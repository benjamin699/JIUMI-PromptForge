# -*- coding: utf-8 -*-
"""JIUMI 提示词工作台 — 共享引擎 core 包。

所有 builder 均为纯 Python（来自插件 vendor 的 mega_pack / wuxia_pack / krea2_pack
以及新增的 y2k_pack），零 ComfyUI 依赖。EXE 与插件共用同一套逻辑，避免分裂。
"""

from .style_packs import build, list_packs, PACKS
from . import y2k_pack, wuxia_pack, mega_pack, krea2_pack

__all__ = [
    "build", "list_packs", "PACKS",
    "y2k_pack", "wuxia_pack", "mega_pack", "krea2_pack",
]
