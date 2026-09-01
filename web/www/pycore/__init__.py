# -*- coding: utf-8 -*-
"""JIUMI 提示词工作台 — 共享引擎 core 包（移动端 Pyodide 子集）。

移动端只做提示词生成，不需要 krea2_pack（仅服务端出图编排用），
故此处只挂载纯 Python 词库：mega_pack / wuxia_pack / y2k_pack + 调度器 style_packs。
零 ComfyUI / torch / numpy 依赖，可在 Pyodide(WASM) 内完整运行。
"""

from .style_packs import build, list_packs, PACKS
from . import y2k_pack, wuxia_pack, mega_pack

__all__ = [
    "build", "list_packs", "PACKS",
    "y2k_pack", "wuxia_pack", "mega_pack",
]
