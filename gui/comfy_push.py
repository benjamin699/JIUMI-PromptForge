# -*- coding: utf-8 -*-
"""
推送到本地 ComfyUI 并取回预览图

- 内置一个极简文生图 workflow（ComfyUI API 格式），把英文 prompt 注入 positive 节点
- POST /prompt → 轮询 /history → 取 SaveImage 输出 → 下载图片字节
- 全部用标准库 urllib，零额外依赖；超时/错误向上抛出由调用方兜底

注意：内置 workflow 的 CheckpointLoaderSimple.ckpt_name 需与用户本地模型匹配，
GUI 会提供「Checkpoint 名称」输入框覆盖默认值。
"""
import json
import time
import uuid
import urllib.request
import urllib.error
import urllib.parse


# 内置极简文生图 workflow（API 格式）。约定：
#   - 排序后第一个 CLIPTextEncode = positive，第二个 = negative
#   - CheckpointLoaderSimple = 模型加载
#   - KSampler = 采样（seed 可注入）
#   - SaveImage = 出图（被轮询取回）
BUILTIN_WORKFLOW = {
    "3": {"class_type": "KSampler", "inputs": {
        "seed": 0, "steps": 25, "cfg": 7.0, "sampler_name": "dpmpp_2m",
        "scheduler": "karras", "denoise": 1.0,
        "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
        "latent_image": ["5", 0]}},
    "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "__CKPT__"}},
    "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 768, "height": 768, "batch_size": 1}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "__POS__", "clip": ["4", 1]}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "__NEG__", "clip": ["4", 1]}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
    "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0]}},
}


DEFAULT_NEGATIVE = "low quality, blurry, watermark, text, deformed, extra limbs, bad anatomy"


def load_workflow(path):
    """加载用户提供的 workflow JSON；path 为空则使用内置。"""
    if path and path.strip():
        with open(path.strip(), encoding="utf-8") as f:
            return json.load(f)
    return json.loads(json.dumps(BUILTIN_WORKFLOW))


def inject(workflow, positive, negative=None, seed=None, ckpt=None):
    """把 prompt / seed / ckpt 注入到 workflow 副本。"""
    wf = json.loads(json.dumps(workflow))

    clips = sorted(
        (nid for nid, n in wf.items() if n.get("class_type") == "CLIPTextEncode"),
        key=lambda x: int(x) if x.isdigit() else 0,
    )
    if clips:
        wf[clips[0]]["inputs"]["text"] = positive or ""
    if negative and len(clips) >= 2:
        wf[clips[1]]["inputs"]["text"] = negative

    for nid, n in wf.items():
        if n.get("class_type") == "CheckpointLoaderSimple" and ckpt:
            n["inputs"]["ckpt_name"] = ckpt
        if n.get("class_type") == "KSampler" and seed is not None:
            n["inputs"]["seed"] = int(seed)

    return wf


def _post_json(url, payload, timeout=30):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_bytes(url):
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read()


def push_and_get(base_url, positive, negative=None, seed=None, ckpt=None,
                 workflow_path=None, timeout=240):
    """
    返回 (image_bytes, error_str)。
    image_bytes 为 None 表示失败，error_str 含原因。
    """
    base = (base_url or "http://127.0.0.1:8188").rstrip("/")
    try:
        workflow = load_workflow(workflow_path)
        wf = inject(workflow, positive, negative or DEFAULT_NEGATIVE, seed, ckpt)

        client_id = str(uuid.uuid4())
        resp = _post_json(base + "/prompt", {"prompt": wf, "client_id": client_id}, timeout=30)
        prompt_id = resp.get("prompt_id")
        if not prompt_id:
            return None, "ComfyUI 未返回 prompt_id（检查地址是否正确）"

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                hist = _get_json(base + "/history/" + prompt_id, timeout=10)
            except Exception:
                hist = {}
            if prompt_id in hist:
                outputs = hist[prompt_id].get("outputs", {})
                for nid, o in outputs.items():
                    imgs = o.get("images")
                    if imgs:
                        im = imgs[0]
                        view_url = (base + "/view?filename=" +
                                    urllib.parse.quote(im.get("filename", "")) +
                                    "&subfolder=" + urllib.parse.quote(im.get("subfolder", "")) +
                                    "&type=" + urllib.parse.quote(im.get("type", "")))
                        return _fetch_bytes(view_url), None
            time.sleep(2)

        return None, "超时（%d 秒）未拿到出图结果，请检查 ComfyUI 队列/显存" % timeout
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "ignore")[:300]
        except Exception:
            pass
        return None, "ComfyUI HTTP %s: %s" % (e.code, detail)
    except urllib.error.URLError as e:
        return None, "无法连接 ComfyUI（%s）请确认 127.0.0.1:8188 已运行" % e.reason
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)
