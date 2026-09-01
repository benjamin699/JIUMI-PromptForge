# -*- coding: utf-8 -*-
"""
JIUMI 提示词工作台 — PySide6 桌面主窗口 (v2)

- 架构三选按钮组：图片(image) / 视频 H3(h3) / Krea2(LLM 驱动)
- 风格四选按钮组：巨构 / 武侠 / 普通 / 千禧年（Krea2 模式下隐藏）
- 种子：🎲 随机复选框（默认勾选，每次生成自动换种子；取消则固定）
- 深色/浅色主题切换 + 字号 A-/A+，均持久化
- Krea2 模式：创意描述框 + 本地 LLM 配置（默认 127.0.0.1:8080/v1, deepseek-coder）
- 推送到本地 ComfyUI + 预览图（内置极简文生图 workflow）
- 所有 LLM / 推送走后台线程，不卡界面

依赖：PySide6 + core（纯 Python 提示词引擎）+ gui.comfy_push
"""
import os
import sys
import json
import time
import random

from PySide6.QtCore import Qt, QThread, Signal, QSettings
from PySide6.QtGui import QFont, QClipboard, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QPushButton, QButtonGroup, QSpinBox, QLabel,
    QPlainTextEdit, QScrollArea, QTabWidget, QStackedWidget,
    QLineEdit, QGroupBox, QFileDialog, QComboBox, QSplitter, QDialog,
    QListWidget,
)

from core.style_packs import PACKS, build, resolve_randoms
from core import krea2_pack
from gui.comfy_push import push_and_get

SEED_MAX = 2147483647
SETTINGS = QSettings("JIUMI", "PromptWorkbench")


def _resource_path(rel):
    """解析资源相对路径：开发模式走脚本同目录；EXE 模式走 _MEIPASS 临时目录。"""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)

# 默认 LLM：智谱 GLM（OpenAI 兼容）。
# 密钥优先级：界面填写 > 环境变量 ZHIPU_API_KEY > 内置默认。
# 注：界面填的密钥会明文存本机 QSettings；介意请改用环境变量并清空输入框。
DEFAULT_LLM_URL = "https://open.bigmodel.cn/api/paas/v4/"
DEFAULT_LLM_MODEL = "glm-4-flash"
DEFAULT_LLM_KEY = os.environ.get("ZHIPU_API_KEY", "") or \
    "870f06ea298b014246e9dc443be2bd20.JJ8D2h8iHfz8ijj1"

DARK_STYLE = """
QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
    font-size: FONT_SZpx;
}
QMainWindow { background-color: #1e1e1e; }
#topbar { background-color: #252526; border-bottom: 1px solid #3a3a3a; padding: 6px 8px; }
QComboBox, QSpinBox, QPlainTextEdit, QLineEdit {
    background-color: #2a2a2a;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    padding: 4px 6px;
    color: #e0e0e0;
}
QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled {
    background-color: #232323;
    color: #666666;
}
QComboBox QAbstractItemView {
    background-color: #2a2a2a;
    color: #e0e0e0;
    selection-background-color: #c084fc;
}
QPushButton {
    background-color: #c084fc;
    color: #1a1a1a;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: bold;
}
QPushButton:hover { background-color: #d4a3ff; }
QPushButton:disabled { background-color: #444; color: #888; }
QPushButton#seg {
    background-color: #2a2a2a;
    color: #cfcfcf;
    border: 1px solid #3a3a3a;
    font-weight: normal;
    padding: 5px 12px;
}
QPushButton#seg:checked {
    background-color: #c084fc;
    color: #1a1a1a;
    font-weight: bold;
}
QLabel { color: #e0e0e0; }
QScrollArea { border: none; }
QSplitter::handle { background-color: #3a3a3a; }
QSplitter::handle:vertical { height: 6px; }
QSplitter::handle:hover { background-color: #c084fc; }
QTabWidget::pane { border: 1px solid #3a3a3a; top: -1px; }
QTabBar::tab {
    background: #2a2a2a;
    color: #bbb;
    padding: 6px 14px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected { background: #c084fc; color: #1a1a1a; font-weight: bold; }
QPlainTextEdit { selection-background-color: #c084fc; selection-color: #1a1a1a; }
QGroupBox { border: 1px solid #3a3a3a; border-radius: 4px; margin-top: 8px; padding-top: 6px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; color: #b088d8; }
"""

LIGHT_STYLE = """
QWidget {
    background-color: #f4f4f5;
    color: #1a1a1a;
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
    font-size: FONT_SZpx;
}
QMainWindow { background-color: #f4f4f5; }
#topbar { background-color: #e4e4e7; border-bottom: 1px solid #c8c8c8; padding: 6px 8px; }
QComboBox, QSpinBox, QPlainTextEdit, QLineEdit {
    background-color: #ffffff;
    border: 1px solid #c8c8c8;
    border-radius: 4px;
    padding: 4px 6px;
    color: #1a1a1a;
}
QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled {
    background-color: #ececec;
    color: #999999;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #1a1a1a;
    selection-background-color: #7c5cff;
}
QPushButton {
    background-color: #7c5cff;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: bold;
}
QPushButton:hover { background-color: #6a4be0; }
QPushButton:disabled { background-color: #c0c0c0; color: #fff; }
QPushButton#seg {
    background-color: #ffffff;
    color: #333333;
    border: 1px solid #c8c8c8;
    font-weight: normal;
    padding: 5px 12px;
}
QPushButton#seg:checked {
    background-color: #7c5cff;
    color: #ffffff;
    font-weight: bold;
}
QLabel { color: #1a1a1a; }
QScrollArea { border: none; }
QSplitter::handle { background-color: #c8c8c8; }
QSplitter::handle:vertical { height: 6px; }
QSplitter::handle:hover { background-color: #7c5cff; }
QTabWidget::pane { border: 1px solid #c8c8c8; top: -1px; }
QTabBar::tab {
    background: #e8e8ea;
    color: #555;
    padding: 6px 14px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected { background: #7c5cff; color: #fff; font-weight: bold; }
QPlainTextEdit { selection-background-color: #7c5cff; selection-color: #fff; }
QGroupBox { border: 1px solid #c8c8c8; border-radius: 4px; margin-top: 8px; padding-top: 6px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; color: #5a3fd0; }
"""

ARCH_ITEMS = [("Krea2 图片", "image"), ("MiniMax H3 视频", "h3"), ("Krea2 LLM生成", "krea2")]
ARCH_ZH = {k: zh for zh, k in ARCH_ITEMS}   # 架构 key → 中文名（历史记录用）
# 顶部两行标签同宽，保证「架构」「风格包」两行的按钮列严格左对齐
LABEL_W = 60
KREA2_ZH = {
    "subject": "主体", "composition": "构图", "micro_density": "微观密度",
    "lens": "镜头", "materials": "材质", "lighting": "光影", "style": "风格",
    "environment": "环境", "quality": "画质", "atmosphere": "氛围",
    "extras": "点缀", "negative_prompt": "负面词",
}


class PreviewLabel(QLabel):
    """预览图标签：支持双击查看原始尺寸图。"""
    doubleClicked = Signal()

    def mouseDoubleClickEvent(self, ev):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(ev)


class Worker(QThread):
    """后台跑可能阻塞的调用（LLM / ComfyUI 推送）。done(result, error)。"""
    done = Signal(object, str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn(), "")
        except Exception as e:
            self.done.emit(None, "%s: %s" % (type(e).__name__, e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JIUMI 提示词工作台")
        self.resize(1180, 760)
        # 头像图标（标题栏 + 任务栏）
        QApplication.instance().setApplicationName("JIUMI 提示词工作台")
        self.setWindowIcon(QIcon(_resource_path("assets/avatar.ico")))

        # 状态（默认选中第一个风格包：普通）
        self.current_style = "normal"
        self.current_arch = "image"
        self.field_widgets = {}
        self.seed_spin = None
        self.worker = None

        # 持久化配置
        self.theme = SETTINGS.value("theme", "dark")
        self.font_size = int(SETTINGS.value("font_size", 13))
        self.apply_theme()

        # ---------- 顶部工具栏：架构 / 风格包 上下两行，左对齐 ----------
        topbar = QWidget()
        topbar.setObjectName("topbar")
        # QWidget 容器默认不绘制样式表背景，需显式开启才能跟随主题变色
        topbar.setAttribute(Qt.WA_StyledBackground, True)

        # 第 1 行：架构（左对齐）+ 主题/字号（行尾右侧）
        row_arch = QHBoxLayout()
        lbl_arch = QLabel("架构")
        lbl_arch.setFixedWidth(LABEL_W)
        row_arch.addWidget(lbl_arch)
        self.arch_group = QButtonGroup(self)
        self.arch_group.setExclusive(True)
        for zh, key in ARCH_ITEMS:
            b = QPushButton(zh)
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setProperty("key", key)
            self.arch_group.addButton(b)
            row_arch.addWidget(b)
            if key == self.current_arch:
                b.setChecked(True)
        self.arch_group.buttonClicked.connect(self.on_arch_btn)
        row_arch.addStretch(1)

        self.theme_btn = QPushButton("🌙 深色" if self.theme == "dark" else "☀️ 浅色")
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.font_minus = QPushButton("A-")
        self.font_plus = QPushButton("A+")
        self.font_minus.clicked.connect(lambda: self.change_font(-1))
        self.font_plus.clicked.connect(lambda: self.change_font(1))
        self.font_label = QLabel("%d" % self.font_size)
        row_arch.addWidget(self.theme_btn)
        row_arch.addWidget(self.font_minus)
        row_arch.addWidget(self.font_label)
        row_arch.addWidget(self.font_plus)

        # 第 2 行：风格包（与上一行同起点，按钮列对齐）
        row_style = QHBoxLayout()
        lbl_style = QLabel("风格包")
        lbl_style.setFixedWidth(LABEL_W)
        row_style.addWidget(lbl_style)
        self.style_group = QButtonGroup(self)
        self.style_group.setExclusive(True)
        self.style_btns = []
        for key, pack in PACKS.items():
            b = QPushButton(pack["name"])
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setProperty("key", key)
            self.style_group.addButton(b)
            self.style_btns.append(b)
            row_style.addWidget(b)
            if key == self.current_style:
                b.setChecked(True)
        self.style_group.buttonClicked.connect(self.on_style_btn)
        row_style.addStretch(1)

        top = QVBoxLayout(topbar)
        top.setContentsMargins(8, 6, 8, 6)
        top.setSpacing(4)
        top.addLayout(row_arch)
        top.addLayout(row_style)
        self.apply_theme()

        # ---------- 左侧：表单 / Krea2 描述 ----------
        self.form_layout = QFormLayout()
        self.form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form_widget = QWidget()
        form_widget.setLayout(self.form_layout)
        self.form_scroll = QScrollArea()
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setWidget(form_widget)

        # 种子行（放在左侧输入区底部，远离右侧结果）
        self.seed_row = QHBoxLayout()
        self.random_seed_cb = QPushButton("🎲 随机种子: 开")
        self.random_seed_cb.setObjectName("seg")
        self.random_seed_cb.setCheckable(True)
        self.random_seed_cb.setChecked(True)
        self.random_seed_cb.clicked.connect(self.on_random_toggle)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, SEED_MAX)
        self.seed_spin.setValue(0)
        self.seed_spin.setEnabled(False)
        self.seed_row.addWidget(QLabel("种子"))
        self.seed_row.addWidget(self.random_seed_cb)
        self.seed_row.addWidget(self.seed_spin)
        self.seed_row.addStretch(1)

        # 注意：这是 left_stack 的直接子部件；form_scroll 是它的子部件，
        # 切换页面必须用本对象，不能传 form_scroll（QStackedWidget 只认直接子部件）
        self.left_form_box = QWidget()
        lfb_v = QVBoxLayout(self.left_form_box)
        lfb_v.addWidget(self.form_scroll, 1)
        lfb_v.addLayout(self.seed_row)

        # Krea2 专页
        krea2_page = QWidget()
        kv = QVBoxLayout(krea2_page)
        kv.addWidget(QLabel("创意描述（中文 / 英文均可）："))
        self.krea2_desc = QPlainTextEdit()
        self.krea2_desc.setPlaceholderText("例如：一个巨大的青铜机械巨佛，在雪原中缓缓睁眼，香火与齿轮并存")
        kv.addWidget(self.krea2_desc, 1)
        kcfg = QGroupBox("LLM 配置（默认智谱 GLM · OpenAI 兼容）")
        kl = QFormLayout(kcfg)
        self.krea2_url = QLineEdit(SETTINGS.value("krea2_url", "") or DEFAULT_LLM_URL)
        self.krea2_model = QLineEdit(SETTINGS.value("krea2_model", "") or DEFAULT_LLM_MODEL)
        self.krea2_key = QLineEdit(SETTINGS.value("krea2_key", "") or DEFAULT_LLM_KEY)
        self.krea2_key.setEchoMode(QLineEdit.Password)
        self.krea2_key.setPlaceholderText("留空则读环境变量 ZHIPU_API_KEY")
        self.key_toggle = QPushButton("显示")
        self.key_toggle.setCheckable(True)
        self.key_toggle.setFixedWidth(52)
        self.key_toggle.toggled.connect(
            lambda on: self.krea2_key.setEchoMode(
                QLineEdit.Normal if on else QLineEdit.Password))
        key_row = QHBoxLayout()
        key_row.addWidget(self.krea2_key, 1)
        key_row.addWidget(self.key_toggle)
        key_wrap = QWidget()
        key_wrap.setLayout(key_row)
        kl.addRow("API 地址", self.krea2_url)
        kl.addRow("模型名", self.krea2_model)
        kl.addRow("API Key", key_wrap)
        self.krea2_timeout = QSpinBox()
        self.krea2_timeout.setRange(30, 900)
        self.krea2_timeout.setSuffix(" 秒")
        self.krea2_timeout.setValue(int(SETTINGS.value("krea2_timeout", 120)))
        self.krea2_timeout.setToolTip("云端/本地模型较慢时可调大；超时返回错误但不崩溃")
        kl.addRow("超时", self.krea2_timeout)
        kv.addWidget(kcfg)
        self.krea2_page = krea2_page

        self.left_stack = QStackedWidget()
        self.left_stack.addWidget(self.left_form_box)
        self.left_stack.addWidget(self.krea2_page)

        # ---------- 输出区：第2栏 中文/英文 竖排；第3栏 预览图独立竖栏 ----------
        zh_group = QGroupBox("中文提示词")
        zh_v = QVBoxLayout(zh_group)
        self.zh_edit = QPlainTextEdit(); self.zh_edit.setReadOnly(True)
        zh_v.addWidget(self.zh_edit, 1)
        zh_copy = QPushButton("复制中文")
        zh_copy.clicked.connect(lambda: self.copy_text(self.zh_edit.toPlainText()))
        zh_v.addWidget(zh_copy)

        en_group = QGroupBox("英文提示词（喂模型）")
        en_v = QVBoxLayout(en_group)
        self.en_edit = QPlainTextEdit(); self.en_edit.setReadOnly(True)
        en_v.addWidget(self.en_edit, 1)
        en_copy = QPushButton("复制英文")
        en_copy.clicked.connect(lambda: self.copy_text(self.en_edit.toPlainText()))
        en_v.addWidget(en_copy)

        # 第 2 栏：中文 / 英文 竖向两排，中间分隔条可拖
        self.text_splitter = QSplitter(Qt.Vertical)
        self.text_splitter.addWidget(zh_group)
        self.text_splitter.addWidget(en_group)
        self.text_splitter.setStretchFactor(0, 1)
        self.text_splitter.setStretchFactor(1, 1)

        # 第 3 栏：预览图独立竖栏，按 9:16 显示 —— 竖屏出图不必挤在宽横条里
        prev_group = QGroupBox("预览图（9:16）")
        prev_v = QVBoxLayout(prev_group)
        self.preview_label = PreviewLabel("推送 ComfyUI 后\n预览图显示在此\n（双击看原图）")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(180)
        self.preview_label.doubleClicked.connect(self.open_preview_original)
        self._preview_pix = None
        prev_v.addWidget(self.preview_label, 1)

        self.preview_panel = QWidget()
        self.preview_panel.setObjectName("preview_panel")
        self.preview_panel.setAttribute(Qt.WA_StyledBackground, True)
        self.preview_panel.setMinimumWidth(200)
        pp_v = QVBoxLayout(self.preview_panel)
        pp_v.setContentsMargins(4, 4, 4, 4)
        pp_v.addWidget(prev_group, 1)

        # 主分栏：输入 | 中文+英文 | 预览图，三条边界都能拖
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(self.left_stack)      # 输入表单 / Krea2 描述
        self.main_splitter.addWidget(self.text_splitter)   # 中文 / 英文
        self.main_splitter.addWidget(self.preview_panel)   # 预览图竖栏
        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 3)
        self.main_splitter.setStretchFactor(2, 2)

        # ---------- 底部：生成 + 推送 ----------
        bottom = QHBoxLayout()
        self.gen_btn = QPushButton("生成")
        self.gen_btn.clicked.connect(self.on_generate)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setToolTip("终止正在进行的 LLM 生成 / ComfyUI 推送")
        self.cancel_btn.clicked.connect(self.cancel_worker)
        bottom.addWidget(self.gen_btn)
        bottom.addWidget(self.cancel_btn)
        bottom.addStretch(1)
        self.history_btn = QPushButton("历史 / 导出")
        self.history_btn.clicked.connect(self.open_history)
        bottom.addWidget(self.history_btn)

        # 推送设置行
        push_row = QHBoxLayout()
        self.comfy_url = QLineEdit(SETTINGS.value("comfy_url", "http://127.0.0.1:8188"))
        self.comfy_ckpt = QLineEdit(SETTINGS.value("comfy_ckpt", ""))
        self.comfy_ckpt.setPlaceholderText("Checkpoint 名称(留空用内置默认)")
        self.comfy_wf = QLineEdit(SETTINGS.value("comfy_wf", ""))
        self.comfy_wf.setPlaceholderText("自定义 workflow JSON(可选)")
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.clicked.connect(self.browse_workflow)
        self.push_btn = QPushButton("推送到 ComfyUI 并预览")
        self.push_btn.clicked.connect(self.on_push)
        push_row.addWidget(QLabel("ComfyUI"))
        push_row.addWidget(self.comfy_url, 2)
        push_row.addWidget(QLabel("模型"))
        push_row.addWidget(self.comfy_ckpt, 1)
        push_row.addWidget(QLabel("WF"))
        push_row.addWidget(self.comfy_wf, 1)
        push_row.addWidget(self.browse_btn)
        push_row.addWidget(self.push_btn)

        # 状态栏
        self.status_bar = QLabel("就绪")
        self.status_bar.setStyleSheet("color:#9aa0a6;")

        # ---------- 根布局 ----------
        root = QVBoxLayout()
        root.addWidget(topbar)
        root.addWidget(self.main_splitter, 1)
        root.addLayout(bottom)
        root.addLayout(push_row)
        root.addWidget(self.status_bar)
        central = QWidget()
        central.setAttribute(Qt.WA_StyledBackground, True)
        central.setLayout(root)
        self.setCentralWidget(central)

        self.rebuild_form()
        self.switch_arch_mode()

    # ---------------- 主题 / 字号 ----------------
    def apply_theme(self):
        src = DARK_STYLE if self.theme == "dark" else LIGHT_STYLE
        QApplication.instance().setStyleSheet(src.replace("FONT_SZ", str(self.font_size)))
        if hasattr(self, "theme_btn"):
            self.theme_btn.setText("🌙 深色" if self.theme == "dark" else "☀️ 浅色")

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        SETTINGS.setValue("theme", self.theme)
        self.apply_theme()

    def change_font(self, delta):
        self.font_size = max(11, min(20, self.font_size + delta))
        SETTINGS.setValue("font_size", self.font_size)
        self.font_label.setText("%d" % self.font_size)
        self.apply_theme()

    # ---------------- 架构 / 风格切换 ----------------
    def on_arch_btn(self, btn):
        self.current_arch = btn.property("key")
        self.switch_arch_mode()

    def on_style_btn(self, btn):
        self.current_style = btn.property("key")
        self.rebuild_form()

    def switch_arch_mode(self):
        is_krea2 = self.current_arch == "krea2"
        # 必须用 left_stack 的直接子部件，传 form_scroll 会静默失效导致切不回表单页
        self.left_stack.setCurrentWidget(self.krea2_page if is_krea2 else self.left_form_box)
        for b in self.style_btns:
            b.setVisible(not is_krea2)
        self.gen_btn.setText("生成 (LLM)" if is_krea2 else "生成")
        if not is_krea2:
            self.rebuild_form()
        self.update_seed_visibility()

    def update_seed_visibility(self):
        show = (self.current_arch != "krea2") and (self.current_style in ("mega", "normal"))
        self.seed_spin.setVisible(show)
        self.random_seed_cb.setVisible(show)

    def on_random_toggle(self):
        on = self.random_seed_cb.isChecked()
        self.random_seed_cb.setText("🎲 随机种子: %s" % ("开" if on else "关"))
        self.seed_spin.setEnabled(not on)

    # ---------------- 表单渲染 ----------------
    def rebuild_form(self):
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)
        self.field_widgets.clear()

        pack = PACKS[self.current_style]
        for field in pack["fields"]:
            key = field["key"]
            if key == "seed":
                continue  # 种子由底部固定控件统一管理
            label = QLabel(field["label"])
            if field.get("kind") == "int":
                # 通用整数字段：范围与默认值由字段声明的 min/max/default 决定
                w = QSpinBox()
                w.setRange(int(field.get("min", 0)), int(field.get("max", SEED_MAX)))
                w.setValue(int(field.get("default", field.get("min", 0))))
            else:
                w = QComboBox()
                for zh, val in field.get("options", []):
                    w.addItem(zh, val)
            is_video = field.get("video", False)
            if is_video and self.current_arch == "image":
                w.setEnabled(False)
            self.form_layout.addRow(label, w)
            self.field_widgets[key] = (w, field)
        self.update_seed_visibility()

    # ---------------- 生成 ----------------
    def on_generate(self):
        if self.current_arch == "krea2":
            self.run_krea2()
        else:
            self.run_normal_generate()

    def run_normal_generate(self):
        if self.random_seed_cb.isChecked():
            seed = random.randint(0, SEED_MAX)
            if self.seed_spin is not None:
                self.seed_spin.setValue(seed)
        else:
            seed = self.seed_spin.value() if self.seed_spin else 0
        params = {"seed": seed}

        for key, (w, field) in self.field_widgets.items():
            if key == "seed":
                continue
            if isinstance(w, QSpinBox):
                params[key] = w.value()
            else:
                params[key] = w.currentData()

        try:
            # 随机哨兵先解析成具体值，否则中文段落只剩风格尾巴（详见 core.resolve_randoms）
            params = resolve_randoms(self.current_style, params)
            text, js, zh = build(self.current_style, self.current_arch, params)
        except Exception as e:
            self.zh_edit.setPlainText("生成失败：%s" % e)
            self.en_edit.clear()
            return

        self.zh_edit.setPlainText(zh)
        self.en_edit.setPlainText(text)
        self.record_history(self.current_style, self.current_arch, zh, text)

        # 6c：把风格 × 题材联动的警告显示到状态栏（如"题材[科幻废土]与[水墨]冲突，已隔离"）
        warns = []
        try:
            warns = json.loads(js).get("warnings") or []
        except Exception:
            warns = []
        if warns:
            self.status_bar.setText("⚠ " + "；".join(warns))
        else:
            self.status_bar.setText("生成完成")

    def run_krea2(self):
        raw = self.krea2_desc.toPlainText().strip()
        if not raw:
            self.status_bar.setText("请先填写创意描述")
            return
        base = self.krea2_url.text().strip() or DEFAULT_LLM_URL
        model = self.krea2_model.text().strip() or DEFAULT_LLM_MODEL
        api_key = self.krea2_key.text().strip()
        SETTINGS.setValue("krea2_url", base)
        SETTINGS.setValue("krea2_model", model)
        SETTINGS.setValue("krea2_key", api_key)
        timeout = int(self.krea2_timeout.value())
        SETTINGS.setValue("krea2_timeout", timeout)
        self.busy("LLM 生成中…（最长 %d 秒，可点取消）" % timeout)
        self.worker = Worker(lambda: krea2_pack.Krea2PromptBuilder().build(
            raw, base, api_key, model, 0.7, timeout, krea2_pack.SYSTEM_PROMPT))
        self.worker.done.connect(self.on_krea2_done)
        self.worker.start()

    def on_krea2_done(self, result, err):
        self.busy(None)
        if err:
            self.zh_edit.setPlainText("Krea2 调用失败：%s" % err)
            self.status_bar.setText("Krea2 失败")
            return
        data, text, js = result
        zh_lines = ["%s：%s" % (KREA2_ZH.get(k, k), (data.get(k) or "")) for k in krea2_pack.KREA2_DIMS]
        self.zh_edit.setPlainText("\n".join(zh_lines))
        self.en_edit.setPlainText(text)
        self.record_history("krea2", "krea2", self.zh_edit.toPlainText(), text)
        self.status_bar.setText("Krea2 生成完成")

    # ---------------- 推送到 ComfyUI ----------------
    def browse_workflow(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 workflow JSON", "", "JSON (*.json)")
        if path:
            self.comfy_wf.setText(path)
            SETTINGS.setValue("comfy_wf", path)

    def on_push(self):
        en = self.en_edit.toPlainText().strip()
        if not en:
            self.status_bar.setText("请先生成英文提示词再推送")
            return
        base = self.comfy_url.text().strip() or "http://127.0.0.1:8188"
        ckpt = self.comfy_ckpt.text().strip() or None
        wf = self.comfy_wf.text().strip() or None
        seed = (self.seed_spin.value() if (self.seed_spin and not self.random_seed_cb.isChecked())
                else random.randint(0, SEED_MAX))
        SETTINGS.setValue("comfy_url", base)
        SETTINGS.setValue("comfy_ckpt", self.comfy_ckpt.text())
        self.busy("推送到 ComfyUI 并等待出图…")
        self.worker = Worker(lambda: push_and_get(base, en, None, seed, ckpt, wf, 240))
        self.worker.done.connect(self.on_push_done)
        self.worker.start()

    def on_push_done(self, img_bytes, err):
        self.busy(None)
        if err:
            self.status_bar.setText("推送失败：%s" % err)
            return
        pix = QPixmap()
        if not pix.loadFromData(img_bytes):
            self.status_bar.setText("预览图解码失败")
            return
        self._preview_pix = pix
        self.render_preview(pix)
        self.status_bar.setText("出图完成，已显示预览（双击看原图）")

    def render_preview(self, pix):
        """按 9:16 竖版比例把图放进预览栏，竖屏出图能完整看到。"""
        avail = self.preview_label.size()
        if avail.width() <= 0 or avail.height() <= 0:
            self.preview_label.setPixmap(pix)
            return
        # 在可用区域内取 9:16 的最大内接矩形
        w = min(avail.width(), int(avail.height() * 9 / 16))
        h = int(w * 16 / 9)
        if h > avail.height():
            h = avail.height()
            w = int(h * 9 / 16)
        self.preview_label.setPixmap(
            pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def open_preview_original(self):
        """双击预览图：弹窗看原图（超出屏幕则等比缩小）。"""
        pix = self._preview_pix
        if pix is None or pix.isNull():
            return
        pm = pix
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            max_w, max_h = int(geo.width() * 0.9), int(geo.height() * 0.9)
            if pm.width() > max_w or pm.height() > max_h:
                pm = pm.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        dlg = QDialog(self)
        dlg.setWindowTitle("预览原图（%d × %d）" % (pix.width(), pix.height()))
        v = QVBoxLayout(dlg)
        lab = QLabel()
        lab.setPixmap(pm)
        lab.setAlignment(Qt.AlignCenter)
        v.addWidget(lab)
        btn = QPushButton("关闭")
        btn.clicked.connect(dlg.accept)
        v.addWidget(btn)
        dlg.exec()

    def resizeEvent(self, ev):
        """拖动分栏/缩放窗口时，预览图按 9:16 重新适配。"""
        super().resizeEvent(ev)
        pix = getattr(self, "_preview_pix", None)
        if pix is not None and not pix.isNull():
            self.render_preview(pix)

    # ---------------- 工具 ----------------
    def busy(self, msg):
        if msg is None:
            self.gen_btn.setEnabled(True)
            self.push_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            return
        self.status_bar.setText(msg)
        self.gen_btn.setEnabled(False)
        self.push_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

    def cancel_worker(self):
        """终止后台线程。阻塞的 HTTP 请求无法优雅中断，只能强杀线程后恢复 UI。"""
        if self.worker is not None and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(3000)
        self.worker = None
        self.busy(None)
        self.status_bar.setText("已取消")

    def copy_text(self, text):
        if not text:
            return
        QApplication.clipboard().setText(text, QClipboard.Clipboard)

    # ---------------- 历史记录 / 导出 ----------------
    def history_path(self):
        """历史文件放用户目录，开发模式与 EXE 模式共用同一份。"""
        return os.path.join(os.path.expanduser("~"), ".jiumi_workbench_history.json")

    def load_history(self):
        p = self.history_path()
        if not os.path.isfile(p):
            return []
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def save_history(self, items):
        try:
            with open(self.history_path(), "w", encoding="utf-8") as f:
                json.dump(items[-300:], f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def record_history(self, style_key, arch_key, zh, en):
        """每次成功生成后留存一条，供回看 / 复制 / 批量导出。"""
        if not (zh or en):
            return
        items = self.load_history()
        items.append({
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "style": PACKS.get(style_key, {}).get("name", style_key),
            "arch": ARCH_ZH.get(arch_key, arch_key),
            "zh": zh or "",
            "en": en or "",
        })
        self.save_history(items)

    @staticmethod
    def _hist_title(it):
        head = (it.get("zh") or it.get("en") or "").replace("\n", " ")
        return "%s  [%s · %s]  %s" % (it.get("time", "?"), it.get("style", "?"),
                                      it.get("arch", "?"), head[:46])

    def open_history(self):
        """历史记录面板：查看 / 复制 / 删除 / 导出全部（txt 或 json）。"""
        items = self.load_history()
        dlg = QDialog(self)
        dlg.setWindowTitle("历史记录（最近 %d 条）" % len(items))
        dlg.resize(840, 580)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("每次生成自动留存（最多 300 条）。点条目看全文，可复制 / 删除 / 导出："))

        lst = QListWidget()
        detail = QPlainTextEdit()
        detail.setReadOnly(True)

        def refresh():
            lst.clear()
            for it in reversed(items):
                lst.addItem(self._hist_title(it))
            detail.clear()

        def show_detail(_r=None):
            r = lst.currentRow()
            if r < 0:
                return
            it = list(reversed(items))[r]
            detail.setPlainText(
                "时间：%s\n风格包：%s\n架构：%s\n\n【中文提示词】\n%s\n\n【英文提示词】\n%s"
                % (it.get("time", ""), it.get("style", ""), it.get("arch", ""),
                   it.get("zh", ""), it.get("en", "")))

        def current_item():
            r, n = lst.currentRow(), len(items)
            idx = n - 1 - r
            return items[idx] if 0 <= idx < n else None

        refresh()
        v.addWidget(lst, 1)
        v.addWidget(detail, 1)
        lst.currentRowChanged.connect(show_detail)

        b_en = QPushButton("复制英文")
        b_zh = QPushButton("复制中文")
        b_del = QPushButton("删除本条")
        b_exp = QPushButton("导出全部…")
        b_close = QPushButton("关闭")

        def copy_en():
            it = current_item()
            if it:
                self.copy_text(it.get("en", ""))
                self.status_bar.setText("已复制该条英文提示词")

        def copy_zh():
            it = current_item()
            if it:
                self.copy_text(it.get("zh", ""))
                self.status_bar.setText("已复制该条中文提示词")

        def delete_one():
            r, n = lst.currentRow(), len(items)
            idx = n - 1 - r
            if not (0 <= idx < n):
                return
            items.pop(idx)
            self.save_history(items)
            refresh()
            self.status_bar.setText("已删除 1 条，剩余 %d 条" % len(items))

        def export_all():
            if not items:
                self.status_bar.setText("暂无历史可导出")
                return
            path, _ = QFileDialog.getSaveFileName(
                dlg, "导出历史提示词", "jiumi_prompts.txt", "文本 (*.txt);;JSON (*.json)")
            if not path:
                return
            try:
                if path.lower().endswith(".json"):
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(items, f, ensure_ascii=False, indent=2)
                else:
                    with open(path, "w", encoding="utf-8") as f:
                        for i, it in enumerate(items, 1):
                            f.write("#%d  %s  [%s · %s]\n中文：%s\n英文：%s\n\n"
                                    % (i, it.get("time", ""), it.get("style", ""),
                                       it.get("arch", ""), it.get("zh", ""), it.get("en", "")))
                self.status_bar.setText("已导出 %d 条 → %s" % (len(items), path))
            except Exception as e:
                self.status_bar.setText("导出失败：%s" % e)

        b_en.clicked.connect(copy_en)
        b_zh.clicked.connect(copy_zh)
        b_del.clicked.connect(delete_one)
        b_exp.clicked.connect(export_all)
        b_close.clicked.connect(dlg.accept)

        row_btn = QHBoxLayout()
        for b in (b_en, b_zh, b_del, b_exp):
            row_btn.addWidget(b)
        row_btn.addStretch(1)
        row_btn.addWidget(b_close)
        v.addLayout(row_btn)

        if items:
            lst.setCurrentRow(0)
        dlg.exec()


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
