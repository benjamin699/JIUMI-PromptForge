# -*- coding: utf-8 -*-
"""全风格包生成测试（纯逻辑，无需 Qt）。

覆盖用户「全部风格包测试」诉求：
  - 4 风格包 × 2 架构(image/h3) × 40 种子，离线生成不崩、非空
  - 中文提示词 100% 中文（仅放行 8K/Y2K/135mm 等跟数字的规格词）
  - ① refPct ∈ [0.03, 0.08]%（参照物占比新规）
  - ③ occ ∈ [75, 92]%、negPct ∈ [12, 25]%（画幅占比/负空间新规）
  - ② 跨区域环境反馈（zh 含「环境影响」）+ ④ 边缘溢出画框（zh 含「画框溢出」）
"""
import os
import re
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from core import mega_pack
from core.style_packs import PACKS, build as build_prompt

ERRORS = []
N_SEEDS = 40
PACKS_ALL = ["normal", "mega", "wuxia", "y2k"]
ARCH_ALL = ["image", "h3"]

# 仅放行紧跟数字的规格词（8K / 135mm / Y2K 等）；连续 2+ 英文字母视为残留
ZH_EN = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{2,}")


def _has_cjk(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def _check(cond, msg):
    if not cond:
        ERRORS.append(msg)


# ---------- 1) 全风格包 × 全架构 × 多种子：生成 / 非空 / 中文纯净 ----------
for st in PACKS_ALL:
    for ar in ARCH_ALL:
        if ar not in PACKS[st]["architectures"]:
            continue
        for sd in range(1, N_SEEDS + 1):
            try:
                en, js, zh = build_prompt(st, ar, {"seed": sd})
            except Exception as e:
                ERRORS.append("%s/%s seed=%d 生成抛异常: %r" % (st, ar, sd, e))
                continue
            _check(en.strip() != "", "%s/%s seed=%d 英文为空" % (st, ar, sd))
            _check(zh.strip() != "", "%s/%s seed=%d 中文为空" % (st, ar, sd))
            hits = ZH_EN.findall(zh)
            if hits:
                ERRORS.append("%s/%s seed=%d 中文残留英文: %r"
                              % (st, ar, sd, sorted(set(hits))[:6]))

# ---------- 2) ① refPct ∈ [0.03, 0.08] ----------
m_ref = re.compile(r"occupying only ([0-9.]+)% of the frame")
ref_bad = 0
for sd in range(1, N_SEEDS + 1):
    en, js, zh = build_prompt("mega", "image", {"seed": sd})
    mm = m_ref.search(en)
    if not mm:
        ref_bad += 1
        continue
    v = float(mm.group(1))
    if not (0.03 - 1e-9 <= v <= 0.08 + 1e-9):
        ref_bad += 1
_check(ref_bad == 0, "① refPct 不在 0.03–0.08%% 的有 %d 次" % ref_bad)

# ---------- 3) ③ occ ∈ [75,92]%、negPct ∈ [12,25]% ----------
m_occ = re.compile(r"occupying (\d+)% of the canvas")
m_neg = re.compile(r"reserving the top (\d+)% of the frame")
occ_bad = neg_bad = 0
for sd in range(1, N_SEEDS + 1):
    en, js, zh = build_prompt("mega", "image", {"seed": sd})
    mo = m_occ.search(en)
    if not mo or not (75 <= int(mo.group(1)) <= 92):
        occ_bad += 1
    mn = m_neg.search(en)
    if not mn or not (12 <= int(mn.group(1)) <= 25):
        neg_bad += 1
_check(occ_bad == 0, "③ occ 不在 75–92%% 的有 %d 次" % occ_bad)
_check(neg_bad == 0, "③ negPct 不在 12–25%% 的有 %d 次" % neg_bad)

# ---------- 4) ② 跨区域环境反馈 + ④ 边缘溢出画框（mega 中文必含） ----------
overflow_miss = impact_miss = 0
for sd in range(1, N_SEEDS + 1):
    en, js, zh = build_prompt("mega", "image", {"seed": sd})
    if "边缘溢出" not in zh:
        overflow_miss += 1
    if "环境影响" not in zh:
        impact_miss += 1
_check(overflow_miss == 0, "④ 边缘溢出缺失 %d 次" % overflow_miss)
_check(impact_miss == 0, "② 跨区域环境反馈(环境影响)缺失 %d 次" % impact_miss)

# ---------- 5) H3 架构同样应带 ②④（串进视频 prompt） ----------
h3_overflow = h3_impact = 0
for sd in range(1, N_SEEDS + 1):
    en, js, zh = build_prompt("mega", "h3", {"seed": sd})
    if "边缘溢出" not in zh:
        h3_overflow += 1
    if "环境影响" not in zh:
        h3_impact += 1
_check(h3_overflow == 0, "④ H3 架构边缘溢出缺失 %d 次" % h3_overflow)
_check(h3_impact == 0, "② H3 架构环境影响缺失 %d 次" % h3_impact)

# ---------- 6) 风格包顺序：普通 > 巨构 > 武侠 > 千禧年 ----------
names = [p["name"] for p in PACKS.values()]
_check(names == ["普通", "巨构", "武侠", "千禧年"], "风格包顺序不符: %r" % (names,))

# ---------- 收尾 ----------
total = len(PACKS_ALL) * len(ARCH_ALL) * N_SEEDS
if ERRORS:
    print("FAIL (%d):" % len(ERRORS))
    for e in ERRORS[:40]:
        print("  -", e)
    sys.exit(1)
else:
    print("PASS: 全风格包测试通过 | 4包×2架构×%d种子=%d 组 | ①refPct ②环境影响 ③occ/negPct ④画框溢出 全部生效 | 中文100%%纯净"
          % (N_SEEDS, total))
    sys.exit(0)
