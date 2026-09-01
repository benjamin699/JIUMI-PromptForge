# -*- coding: utf-8 -*-
"""v6 无头结构/主题/布局/中文纯净/生成测试（offscreen，不弹窗）。"""
import os
import re
import sys
import json

os.environ["QT_QPA_PLATFORM"] = "offscreen"

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DEPS = os.path.join(HERE, ".deps")
if os.path.isdir(DEPS):
    sys.path.insert(0, DEPS)

from PySide6.QtWidgets import QApplication, QLabel, QScrollArea, QSplitter, QStackedWidget, QWidget
from PySide6.QtCore import Qt
from core import mega_pack, y2k_pack
from core.style_packs import (MEGA_FIELDS, WUXIA_FIELDS, Y2K_FIELDS, PACKS,
                              build as build_prompt)
from gui.workbench_app import MainWindow, ARCH_ITEMS

errors = []


def check(cond, msg):
    if not cond:
        errors.append(msg)


app = QApplication(sys.argv)
w = MainWindow()

# 1) 顶部栏存在且开启样式背景
topbar = w.findChild(QWidget, "topbar")
check(topbar is not None, "顶部栏 topbar 未找到")
if topbar is not None:
    check(topbar.testAttribute(Qt.WA_StyledBackground),
          "topbar 未开启 WA_StyledBackground（主题不跟随）")

central = w.centralWidget()
check(central.testAttribute(Qt.WA_StyledBackground),
      "central 未开启 WA_StyledBackground")

# 2) 深/浅主题切换时样式表含对应横栏色
ss_dark = app.styleSheet()
check("#252526" in ss_dark, "深色样式表缺少顶部栏深色 #252526")
w.toggle_theme()
ss_light = app.styleSheet()
check("#e4e4e7" in ss_light, "浅色样式表缺少顶部栏浅色 #e4e4e7")
w.toggle_theme()  # 还原深色

# 3) 架构标签
expected = [("Krea2 图片", "image"), ("MiniMax H3 视频", "h3"), ("Krea2 LLM生成", "krea2")]
check(ARCH_ITEMS == expected, "ARCH_ITEMS 不符: %r" % (ARCH_ITEMS,))

# 4) 主分栏三栏：输入 | 中文+英文竖排 | 预览图竖栏
root = central.layout()
main_split = root.itemAt(1).widget()
check(isinstance(main_split, QSplitter), "主区域不是 QSplitter: %r" % type(main_split))
if isinstance(main_split, QSplitter):
    check(main_split.orientation() == Qt.Horizontal, "主分栏不是横向三栏")
    check(main_split.count() == 3,
          "主分栏应为 3 栏（输入/文本/预览图），实际 %d" % main_split.count())
    if main_split.count() == 3:
        c0, c1, c2 = main_split.widget(0), main_split.widget(1), main_split.widget(2)
        check(isinstance(c0, QStackedWidget), "第1栏不是输入栈: %r" % type(c0))
        check(isinstance(c1, QSplitter) and c1.orientation() == Qt.Vertical,
              "第2栏不是「中文/英文」竖向分割器: %r" % type(c1))
        if isinstance(c1, QSplitter):
            check(c1.count() == 2, "第2栏应含中文/英文 2 个框，实际 %d" % c1.count())
        check(c2 is w.preview_panel, "第3栏不是预览图竖栏: %r" % type(c2))

# 4b) 顶部栏：架构 / 风格包 上下两行，标签同宽左对齐
if topbar is not None:
    tl = topbar.layout()
    check(tl.count() == 2, "顶部栏应为上下两行，实际 %d 项" % tl.count())
    if tl.count() == 2:
        row_arch = tl.itemAt(0).layout()
        row_style = tl.itemAt(1).layout()
        check(row_arch is not None, "顶部第1行不是布局")
        check(row_style is not None, "顶部第2行不是布局")
        if row_arch is not None and row_style is not None:
            la = row_arch.itemAt(0).widget()
            ls = row_style.itemAt(0).widget()
            check(isinstance(la, QLabel) and la.text() == "架构",
                  "第1行首项不是「架构」标签: %r" % (la.text() if hasattr(la, "text") else la))
            check(isinstance(ls, QLabel) and ls.text() == "风格包",
                  "第2行首项不是「风格包」标签: %r" % (ls.text() if hasattr(ls, "text") else ls))
            if isinstance(la, QLabel) and isinstance(ls, QLabel):
                check(la.width() == ls.width(),
                      "两行标签宽度不等，按钮列未对齐: 架构%d vs 风格包%d" % (la.width(), ls.width()))

# 5) 普通生成（mega/image）离线不崩且出内容
w.current_style = "mega"
w.current_arch = "image"
w.rebuild_form()
w.on_generate()
check(w.zh_edit.toPlainText().strip() != "", "中文提示词生成为空")
check(w.en_edit.toPlainText().strip() != "", "英文提示词生成为空")

# 6) 旧悬空属性已清除
check(not hasattr(w, "compare_edit"), "仍存在已删除的 compare_edit 属性")

# 7) 错误分支不崩（此前会因 compare_edit 抛 AttributeError）
try:
    w.current_arch = "krea2"
    w.switch_arch_mode()
    w.krea2_desc.setPlainText("测试描述")
    w.on_krea2_done(None, "模拟错误")
except Exception as e:
    errors.append("on_krea2_done 错误分支崩溃: %r" % e)

try:
    w.on_push_done(None, "模拟推送错误")
except Exception as e:
    errors.append("on_push_done 错误分支崩溃: %r" % e)

# 8) 架构切换往返：Krea2 LLM <-> 图片/H3，左栈必须跟着换页
#    （回归：曾因 setCurrentWidget 传了非直接子部件，切到 LLM 后永远切不回来）
arch_btns = {b.property("key"): b for b in w.arch_group.buttons()}
w.on_arch_btn(arch_btns["krea2"])
check(w.current_arch == "krea2", "点 Krea2 LLM 后 current_arch 未更新")
check(w.left_stack.currentWidget() is w.krea2_page,
      "切到 Krea2 LLM 后左栈未显示 LLM 页")
w.on_arch_btn(arch_btns["image"])
check(w.current_arch == "image", "点 Krea2 图片后 current_arch 未更新")
check(w.left_stack.currentWidget() is w.left_form_box,
      "切回「Krea2 图片」后左栈仍卡在 LLM 页（setCurrentWidget 失效）")
w.on_arch_btn(arch_btns["h3"])
check(w.left_stack.currentWidget() is w.left_form_box,
      "切到 MiniMax H3 视频后左栈应显示表单页")
w.on_arch_btn(arch_btns["image"])

# 9) 风格包切换：4 个风格包逐个点一遍，表单都要重建出字段
for _b in w.style_btns:
    w.on_style_btn(_b)
    check(len(w.field_widgets) > 0,
          "风格包 %s 切换后表单字段为空" % (_b.property("key"),))

# 10) 巨构主体下拉必须全中文（MEGA 条目无 label 键，曾 fallback 成英文 key）
def _has_cjk(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


pk_field = [f for f in MEGA_FIELDS if f["key"] == "pk"][0]
bad_pk = [zh for zh, _v in pk_field["options"] if zh and not _has_cjk(zh)]
check(not bad_pk, "巨构主体下拉存在非中文选项: %r" % (bad_pk[:6],))

# 11) A 方案：中文提示词必须 100% 中文（4 包 × 2 架构 × 15 种子）
#     仅允许 Y2K / 8K / 135mm 这类紧跟数字的规格词（lookbehind 已排除）
_zh_en = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{2,}")
for _st in ("mega", "normal", "wuxia", "y2k"):
    for _ar in ("image", "h3"):
        for _sd in range(1, 16):
            _t, _j, _zh = build_prompt(_st, _ar, {"seed": _sd})
            _hits = _zh_en.findall(_zh)
            if _hits:
                errors.append("%s/%s seed=%d 中文提示词残留英文: %r"
                              % (_st, _ar, _sd, sorted(set(_hits))[:5]))
                break

# 12) 千禧年主体：场景型为主 + 总量足够
_scene = [zh for zh, _v in y2k_pack.SUBJECTS if zh.startswith("【场景】")]
check(len(_scene) >= 15, "千禧年场景型主体不足 15 个，实际 %d" % len(_scene))
check(len(y2k_pack.SUBJECTS) >= 30,
      "千禧年主体总数不足 30，实际 %d" % len(y2k_pack.SUBJECTS))

# 13) 6a 联动：环境=广西 + 主体=随机，必须全部落在广西地域巨构池
_hits = 0
for _s in range(30):
    _t, _j, _zh = build_prompt("mega", "image", {"seed": _s, "envKey": "guangxi", "pk": "rand"})
    if any(n in _zh.split("，")[0] for n in ("铜鼓寨", "喀斯特", "龙脊")):
        _hits += 1
check(_hits == 30, "6a 地域联动失效：30 次中仅 %d 次落在广西池" % _hits)

# 14) 6b 联动：水墨(国风) + 科幻废土 → 隔离模式须剔除题材并给警告；碰撞模式须保留
_t1, _j1, _z1 = build_prompt("mega", "image",
                             {"seed": 7, "styleKey": "ink", "theme": "scifi_waste", "mix_mode": "隔离"})
_w1 = json.loads(_j1).get("warnings") or []
check("题材：" not in _z1, "6b 隔离模式未剔除冲突题材")
check(any("已隔离" in x for x in _w1), "6b 隔离模式未给出冲突警告: %r" % (_w1,))
_t2, _j2, _z2 = build_prompt("mega", "image",
                             {"seed": 7, "styleKey": "ink", "theme": "scifi_waste", "mix_mode": "碰撞"})
check("题材：" in _z2, "6b 碰撞模式未保留题材")

# 15) 风格包顺序：普通 > 巨构 > 武侠 > 千禧年
_names = [p["name"] for p in PACKS.values()]
check(_names == ["普通", "巨构", "武侠", "千禧年"], "风格包顺序不符: %r" % (_names,))

# 16) 下拉首项必须是「随机」（武侠 / 千禧年）
for _pname, _fields in (("武侠", WUXIA_FIELDS), ("千禧年", Y2K_FIELDS)):
    for _f in _fields:
        _opts = _f.get("options") or []
        if _opts:
            check("随机" in str(_opts[0][0]),
                  "%s 的「%s」下拉首项不是随机: %r" % (_pname, _f["label"], _opts[0][0]))

# 收尾
if errors:
    print("FAIL (%d):" % len(errors))
    for e in errors:
        print("  -", e)
    sys.exit(1)
else:
    print("PASS: 顶部两行左对齐 / 顶部栏主题跟随 / 输出区右侧竖排可拖 / 架构标签 / 生成 / 错误分支 / 架构往返切换 / 风格包切换 全部通过")
    sys.exit(0)
