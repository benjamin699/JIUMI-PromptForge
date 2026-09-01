# -*- coding: utf-8 -*-
"""
调用本地 llama-server (DeepSeek-Coder 6.7B Q4) 生成 PySide6 GUI 代码。
本地模型当作者，本脚本负责：等待服务就绪 → 发送精确 spec → 落盘 gui/workbench_app.py。
生成后由人工（W先生）做集成与 QA。
"""
import sys, time, json, urllib.request, urllib.error, re

URL = "http://127.0.0.1:8080/v1/chat/completions"
OUT = "gui/workbench_app.py"

SYSTEM = (
    "You are an expert Python GUI engineer using PySide6 (Qt for Python). "
    "Write clean, runnable, single-file PySide6 desktop applications. "
    "Output ONLY raw Python source code, no markdown fences, no explanation."
)

USER = r"""
Write a single-file PySide6 desktop app: a JIUMI prompt-workbench for AI image/video prompts.

DATA CONTRACT (already implemented, import as-is):
  from core.style_packs import PACKS, build
  PACKS is dict: style_key -> {
      "name": str (Chinese, e.g. "巨构"),
      "desc": str,
      "architectures": list of "image" and/or "h3",
      "fields": list of field dicts,
      "build": callable  # do NOT call directly; use build()
  }
  Each field dict has keys:
      "key": str
      "label": str (Chinese UI label)
      "options": list of [chinese_label, value_key]   # for dropdowns
      "kind": "int"  (only for seed/strength fields)   # absent for dropdowns
      "video": bool  (True => only relevant when architecture == "h3")
  build(style_key, architecture, params) -> (english_prompt_text, json_string)
      params: dict mapping field["key"] -> selected value_key (str) or int (for kind=="int")

REQUIREMENTS:
1. QApplication + QMainWindow titled "JIUMI 提示词工作台". Apply a dark stylesheet (bg #1e1e1e, text #e0e0e0, accent #c084fc).
2. Top controls: a QComboBox "架构" with items 图片(image)/视频H3(h3); a QComboBox "风格包" populated from PACKS (show field["name"]; map back to style_key).
3. When 风格包 changes: rebuild a form (QFormLayout inside a scroll area) from PACKS[style]["fields"]:
   - dropdown fields -> QLabel(label) + QComboBox(options displayed as chinese_label, store value_key in itemData)
   - int fields -> QLabel(label) + QSpinBox (0..4294967294)
   - video-only fields (video==True): disable (setEnabled(False)) when architecture=="image".
   When 架构 changes: re-enable/disable video-only fields.
4. A "生成" QPushButton: collect params dict from the form (key -> currentData() for combos, value() for spins), call build(style, arch, params) -> (text, js). Show:
   - 中英对照 area: for each field show "label : selected_chinese_label"
   - English prompt: QPlainTextEdit (read-only) with text
   - JSON: QPlainTextEdit (read-only) with js
   - Two "复制" buttons: copy english prompt / copy json via QApplication.clipboard().setText(...)
5. Layout: vertical — top controls row, middle split: left form (scroll), right outputs (tabbed or stacked: 中英对照 / 英文 / JSON). Bottom: 生成 + 复制 buttons.
6. Use only PySide6 widgets. Keep it functional and minimal. No external imports beyond PySide6 and core.
7. Guard main with: if __name__ == "__main__": app = QApplication(sys.argv); w = MainWindow(); w.show(); sys.exit(app.exec())

Return ONLY the Python source.
"""

def wait_ready(timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(URL.replace("/chat/completions", "/models"), timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(2)
    return False

def main():
    print("waiting for llama-server ...")
    if not wait_ready():
        print("ERROR: llama-server not ready")
        sys.exit(1)
    payload = {
        "model": "deepseek-coder",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=300) as resp:
        obj = json.loads(resp.read().decode())
    code = obj["choices"][0]["message"]["content"]
    # strip possible markdown fences
    code = re.sub(r"^```(?:python)?\s*", "", code.strip())
    code = re.sub(r"\s*```$", "", code)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(code)
    print("wrote", OUT, "(", len(code), "chars )")

if __name__ == "__main__":
    main()
