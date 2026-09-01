# -*- coding: utf-8 -*-
"""
JIUMI 提示词工作台 · 移动端 PWA 后端

设计要点：
1. 业务逻辑 100% 复用 core/（纯 Python，零 Qt 依赖），本文件只做薄封装。
2. 出图走「PC 中转」：服务端运行在 PC 上，可直接访问本机 127.0.0.1:8188。
3. 出图异步任务化：core 的 push_and_get 是同步阻塞（while + sleep(2)，最长 240s），
   若做成同步接口会占死单线程、且手机链路极易超时。故 POST /api/render 立即返回
   job_id，前端轮询 GET /api/job/{id}。后期加远程控制（跨网络/鉴权/队列管理）
   只需加端点，不必重写交互。
4. 配置外置到 config.json：远程场景改地址的概率很高，避免硬编码。
"""
import base64
import json
import os
import queue
import random
import sqlite3
import sys
import threading
import time
import traceback
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# ---- 让 core / gui 可被 import（项目根目录入路径）----
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import style_packs, krea2_pack                     # noqa: E402
from gui.comfy_push import push_and_get                      # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR = os.path.join(DATA_DIR, "outputs")
DB_PATH = os.path.join(DATA_DIR, "history.db")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
os.makedirs(OUT_DIR, exist_ok=True)

from fastapi import FastAPI, HTTPException                    # noqa: E402
from fastapi.responses import FileResponse, JSONResponse      # noqa: E402
from fastapi.staticfiles import StaticFiles                   # noqa: E402
from pydantic import BaseModel                                # noqa: E402
from typing import Optional, Dict, Any                        # noqa: E402

# ============================ 配置 ============================
DEFAULT_CONFIG = {
    "comfy_url": "http://127.0.0.1:8188",
    "comfy_ckpt": "",
    "comfy_wf": "",
    "krea2": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "api_key": "",
        "model": "GLM-4.7-Flash",
        "temperature": 0.7,
        "timeout": 60,
    },
    "host": "0.0.0.0",
    "port": 8000,
    # 鉴权开关：留空 = 关闭（局域网直连）。后期远程时填 token 即启用，无需改代码。
    "auth_token": "",
}


def load_config() -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                disk = json.load(f)
            for k, v in (disk or {}).items():
                if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
        except Exception:
            pass
    return cfg


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


CONFIG = load_config()

# ============================ 历史库 ============================
_db_lock = threading.Lock()


def db_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _db_lock, db_conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            style TEXT,
            arch TEXT,
            zh TEXT,
            en TEXT
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_hist_ts ON history(ts DESC)")


init_db()

# ============================ 出图异步任务 ============================
# push_and_get 是同步阻塞调用，丢进线程池；并发限制 2，避免显存/队列互抢。
_executor = ThreadPoolExecutor(max_workers=2)
JOBS: Dict[str, dict] = {}
_jobs_lock = threading.Lock()
SEED_MAX = 2 ** 31 - 1


def _run_render(job_id: str, prompt: str, seed: int, negative: Optional[str],
                timeout: int) -> None:
    """后台线程：调 ComfyUI 出图，结果落到 data/outputs/{job_id}.png"""
    try:
        img_bytes, err = push_and_get(
            CONFIG.get("comfy_url") or "http://127.0.0.1:8188",
            prompt,
            negative,
            seed,
            CONFIG.get("comfy_ckpt") or None,
            CONFIG.get("comfy_wf") or None,
            int(timeout or 240),
        )
        with _jobs_lock:
            job = JOBS[job_id]
            if err:
                job.update(status="failed", error=str(err), finished_at=time.time())
                return
            path = os.path.join(OUT_DIR, job_id + ".png")
            with open(path, "wb") as f:
                f.write(img_bytes)
            job.update(status="done", path=path, seed=seed, finished_at=time.time())
    except Exception as e:
        with _jobs_lock:
            JOBS[job_id].update(
                status="failed",
                error="%s: %s" % (type(e).__name__, e),
                detail=traceback.format_exc()[-500:],
                finished_at=time.time(),
            )


# ============================ 请求模型 ============================
class BuildReq(BaseModel):
    style: str
    arch: str = "image"
    params: Dict[str, Any] = {}


class Krea2Req(BaseModel):
    raw_input: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    timeout: Optional[int] = None
    system_prompt: Optional[str] = None


class RenderReq(BaseModel):
    prompt: str
    seed: Optional[int] = None
    negative: Optional[str] = None
    timeout: Optional[int] = 240


class HistAddReq(BaseModel):
    style: str = ""
    arch: str = ""
    zh: str = ""
    en: str = ""


# ============================ 工具 ============================
def _norm_options(opts):
    """把 [(label, value)] / [value] 统一成 [{label, value}]，兼容各 pack 的写法。"""
    out = []
    for it in (opts or []):
        if isinstance(it, (list, tuple)):
            if len(it) >= 2:
                out.append({"label": str(it[0]), "value": it[1]})
            elif len(it) == 1:
                out.append({"label": str(it[0]), "value": it[0]})
        else:
            out.append({"label": str(it), "value": it})
    return out


def _serialize_packs():
    """PACKS → 可 JSON 化结构（剔除 build 函数，options 归一化）。"""
    res = {}
    for key, pack in style_packs.PACKS.items():
        fields = []
        for f in pack.get("fields", []):
            fields.append({
                "key": f.get("key"),
                "label": f.get("label"),
                "kind": f.get("kind", "enum"),
                "video": bool(f.get("video")),
                "min": f.get("min"),
                "max": f.get("max"),
                "default": f.get("default"),
                "options": _norm_options(f.get("options")),
            })
        res[key] = {
            "key": key,
            "name": pack.get("name", key),
            "desc": pack.get("desc", ""),
            "architectures": pack.get("architectures", ["image"]),
            "fields": fields,
        }
    return res


# ============================ App ============================
app = FastAPI(title="JIUMI Prompt Workbench · Mobile", version="0.1.0")


@app.middleware("http")
async def auth_middleware(request, call_next):
    """鉴权开关：config.auth_token 为空则跳过。后期远程开放时填值即生效。"""
    token = (CONFIG.get("auth_token") or "").strip()
    if token and not request.url.path.startswith(("/static", "/manifest", "/icon", "/sw")):
        got = request.headers.get("x-jiumi-token", "")
        if got != token:
            return JSONResponse({"error": "未授权：缺少或错误的 token"}, status_code=401)
    return await call_next(request)


# ---------- 配置 ----------
@app.get("/api/config")
def api_get_config():
    cfg = load_config()
    safe = json.loads(json.dumps(cfg))
    k = safe.get("krea2", {})
    if k.get("api_key"):
        k["api_key"] = "***已设置***"
    return safe


@app.post("/api/config")
def api_set_config(patch: Dict[str, Any]):
    global CONFIG
    cfg = load_config()
    for key, val in (patch or {}).items():
        if isinstance(val, dict) and isinstance(cfg.get(key), dict):
            # api_key 传 ***已设置*** 视为不修改
            if key == "krea2" and val.get("api_key") == "***已设置***":
                val = dict(val)
                val.pop("api_key", None)
            cfg[key].update(val)
        else:
            cfg[key] = val
    save_config(cfg)
    CONFIG = cfg
    return {"ok": True}


# ---------- 风格包 ----------
@app.get("/api/packs")
def api_packs():
    return {"packs": _serialize_packs(), "order": list(style_packs.PACKS.keys())}


# ---------- 生成提示词 ----------
def _resolve_randoms(style, params):
    """委托 core.style_packs.resolve_randoms —— 桌面端与移动端共用同一份逻辑，避免两套实现走偏。"""
    return style_packs.resolve_randoms(style, params)


@app.post("/api/build")
def api_build(req: BuildReq):
    try:
        params = dict(req.params or {})
        try:
            params["seed"] = int(params.get("seed", 0) or 0)
        except Exception:
            params["seed"] = 0
        for k, v in list(params.items()):
            if k.endswith("motion_strength") or k == "shots":
                try:
                    params[k] = int(v)
                except Exception:
                    params.pop(k, None)
        params = _resolve_randoms(req.style, params)
        en, js, zh = style_packs.build(req.style, req.arch, params)
        warns = []
        try:
            warns = json.loads(js).get("warnings") or []
        except Exception:
            pass
        return {"ok": True, "en": en, "zh": zh, "json": js, "warnings": warns}
    except Exception as e:
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}


# ---------- Krea2（云端 LLM，手机端不走本机 8080）----------
@app.post("/api/krea2")
def api_krea2(req: Krea2Req):
    try:
        k = CONFIG.get("krea2", {})
        data, text, json_str = krea2_pack.Krea2PromptBuilder().build(
            req.raw_input,
            req.base_url or k.get("base_url", ""),
            req.api_key or k.get("api_key", ""),
            req.model or k.get("model", "GLM-4.7-Flash"),
            float(req.temperature if req.temperature is not None else k.get("temperature", 0.7)),
            int(req.timeout or k.get("timeout", 60)),
            req.system_prompt or krea2_pack.SYSTEM_PROMPT,
        )
        return {"ok": True, "text": text, "json": json_str,
                "error": (data or {}).get("error", "") if isinstance(data, dict) else ""}
    except Exception as e:
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}


# ---------- 出图（异步任务）----------
@app.post("/api/render")
def api_render(req: RenderReq):
    prompt = (req.prompt or "").strip()
    if not prompt:
        raise HTTPException(400, "prompt 为空")
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + str(random.randint(1000, 9999))
    seed = req.seed if req.seed else random.randint(0, SEED_MAX)
    with _jobs_lock:
        JOBS[job_id] = {"status": "running", "created_at": time.time(), "seed": seed}
    _executor.submit(_run_render, job_id, prompt, seed, req.negative, int(req.timeout or 240))
    return {"ok": True, "job_id": job_id, "seed": seed}


@app.get("/api/job/{job_id}")
def api_job(job_id: str):
    with _jobs_lock:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    return {
        "status": job.get("status"),
        "error": job.get("error", ""),
        "seed": job.get("seed"),
        "image_url": ("/api/image/%s" % job_id) if job.get("status") == "done" else None,
        "elapsed": round(time.time() - job.get("created_at", time.time()), 1),
    }


@app.get("/api/image/{job_id}")
def api_image(job_id: str):
    with _jobs_lock:
        job = JOBS.get(job_id)
    if not job or job.get("status") != "done" or not job.get("path"):
        raise HTTPException(404, "图片不存在")
    return FileResponse(job["path"], media_type="image/png")


# ---------- ComfyUI 状态（后期远程控制的基础端点）----------
@app.get("/api/comfy/status")
def api_comfy_status():
    base = (CONFIG.get("comfy_url") or "http://127.0.0.1:8188").rstrip("/")
    try:
        with urllib.request.urlopen(base + "/system_stats", timeout=3) as r:
            data = json.loads(r.read().decode("utf-8"))
        try:
            with urllib.request.urlopen(base + "/queue", timeout=3) as r2:
                q = json.loads(r2.read().decode("utf-8"))
            running = len(q.get("queue_running") or [])
            pending = len(q.get("queue_pending") or [])
        except Exception:
            running = pending = -1
        dev = (data.get("devices") or [{}])[0]
        return {"online": True, "running": running, "pending": pending,
                "device": dev.get("name", ""),
                "vram_free": dev.get("vram_free", 0), "vram_total": dev.get("vram_total", 0)}
    except Exception as e:
        return {"online": False, "error": "%s" % e}


# ---------- 历史 ----------
@app.get("/api/history")
def api_history(limit: int = 50, offset: int = 0):
    with _db_lock, db_conn() as c:
        rows = c.execute(
            "SELECT id, ts, style, arch, zh, en FROM history "
            "ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        total = c.execute("SELECT COUNT(*) FROM history").fetchone()[0]
    return {"total": total, "items": [dict(r) for r in rows]}


@app.post("/api/history")
def api_history_add(req: HistAddReq):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock, db_conn() as c:
        cur = c.execute(
            "INSERT INTO history (ts, style, arch, zh, en) VALUES (?,?,?,?,?)",
            (ts, req.style, req.arch, req.zh, req.en))
        new_id = cur.lastrowid
    return {"ok": True, "id": new_id, "ts": ts}


@app.delete("/api/history/{hid}")
def api_history_del(hid: int):
    with _db_lock, db_conn() as c:
        c.execute("DELETE FROM history WHERE id=?", (hid,))
    return {"ok": True}


@app.delete("/api/history")
def api_history_clear():
    with _db_lock, db_conn() as c:
        c.execute("DELETE FROM history")
        c.execute("DELETE FROM sqlite_sequence WHERE name='history'")
    return {"ok": True}


# ---------- 静态与 PWA ----------
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(os.path.join(STATIC_DIR, "manifest.webmanifest"),
                        media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    return FileResponse(os.path.join(STATIC_DIR, "sw.js"), media_type="application/javascript")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": datetime.now().isoformat()}


def lan_addresses(port):
    """列出本机局域网 IP，方便手机扫码/手输地址。"""
    import socket
    addrs = []
    try:
        host = socket.gethostname()
        for info in socket.getaddrinfo(host, None, socket.AF_INET):
            ip = info[4][0]
            if ip.startswith("127.") or ip in addrs:
                continue
            addrs.append(ip)
    except Exception:
        pass
    if not addrs:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("223.5.5.5", 80))
            addrs.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass
    return ["http://%s:%d" % (ip, port) for ip in addrs]


if __name__ == "__main__":
    import uvicorn
    port = int(CONFIG.get("port", 8000))
    print("=" * 52)
    print("  JIUMI 提示词工作台 · 移动端服务")
    print("=" * 52)
    print("  本机访问:   http://127.0.0.1:%d" % port)
    for a in lan_addresses(port):
        print("  手机访问:   %s" % a)
    print("  说明: 手机需与电脑连同一个网络")
    print("=" * 52)
    uvicorn.run(app, host=CONFIG.get("host", "0.0.0.0"), port=port, log_level="info")
