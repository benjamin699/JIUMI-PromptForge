# -*- coding: utf-8 -*-
"""JIUMI 移动端后端 · 冒烟测试（只读 + 自造数据，不触碰用户书籍/配置）"""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"


def req(path, data=None, method=None):
    url = BASE + path
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        r = urllib.request.Request(url, data=body, method=method or "POST",
                                   headers={"Content-Type": "application/json"})
    else:
        r = urllib.request.Request(url, method=method or "GET")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "detail": e.read().decode("utf-8", "ignore")[:200]}
    except Exception as e:
        return {"_error": "%s: %s" % (type(e).__name__, e)}


print("=" * 60)
print("[1] /api/packs 风格包与字段")
pk = req("/api/packs")
if "packs" not in pk:
    print("  失败:", pk)
    raise SystemExit(1)
for k, p in pk["packs"].items():
    vis = len([f for f in p["fields"] if not f["video"]])
    hid = len([f for f in p["fields"] if f["video"]])
    print("  %s(%s)  架构=%s  图片字段=%d  视频字段=%d"
          % (p["name"], k, "/".join(p["architectures"]), vis, hid))

print()
print("[2] /api/build 四风格 × 图片/H3 全量生成")
ok = fail = 0
for style in pk["packs"]:
    for arch in pk["packs"][style]["architectures"]:
        params = {}
        for f in pk["packs"][style]["fields"]:
            if f["video"] and arch != "h3":
                continue
            if f["kind"] == "int":
                params[f["key"]] = f["default"] if f["default"] is not None else 0
            else:
                opts = f["options"]
                params[f["key"]] = opts[0]["value"] if opts else ""
        r = req("/api/build", {"style": style, "arch": arch, "params": params})
        if r.get("ok"):
            ok += 1
            zh = (r.get("zh") or "").replace("\n", " ")
            warn = len(r.get("warnings") or [])
            print("  [OK] %-7s %-5s  中文 %4d 字 / 英文 %4d 字符 / 警告 %d"
                  % (style, arch, len(r.get("zh") or ""), len(r.get("en") or ""), warn))
            print("       %s" % zh[:76])
        else:
            fail += 1
            print("  [FAIL] %-7s %-5s  %s" % (style, arch, r.get("error")))
print("  小计：成功 %d / 失败 %d" % (ok, fail))

print()
print("[3] /api/comfy/status")
st = req("/api/comfy/status")
print("  ", json.dumps(st, ensure_ascii=False)[:180])

print()
print("[4] 历史记录 增/查/删")
r = req("/api/history", {"style": "wuxia", "arch": "image",
                         "zh": "冒烟测试中文", "en": "smoke test en"})
hid = r.get("id")
print("  新增 id =", hid)
lst = req("/api/history?limit=5")
print("  列表总数 =", lst.get("total"), " 首条 =", (lst["items"][0]["zh"][:20] if lst.get("items") else "无"))
if hid:
    print("  删除 =", req("/api/history/%d" % hid, method="DELETE"))
print("  删除后总数 =", req("/api/history?limit=5").get("total"))

print()
print("[5] /api/render 异步任务（仅当 ComfyUI 在线才真出图）")
if st.get("online"):
    r = req("/api/render", {"prompt": "a colossal bronze tower above the sea of clouds, cinematic",
                            "timeout": 60})
    print("  提交:", r)
    if r.get("ok"):
        import time
        for i in range(12):
            time.sleep(5)
            j = req("/api/job/%s" % r["job_id"])
            print("  轮询 %2d: %s %s" % (i, j.get("status"), j.get("error", "")))
            if j.get("status") in ("done", "failed"):
                break
else:
    print("  ComfyUI 离线，跳过真实出图。改为验证任务接口的错误处理：")
    r = req("/api/render", {"prompt": "test prompt for offline render", "timeout": 10})
    print("  提交:", r)
    if r.get("ok"):
        import time
        time.sleep(14)
        print("  轮询:", req("/api/job/%s" % r["job_id"]))

print()
print("=" * 60)
print("冒烟测试结束")
