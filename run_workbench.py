# -*- coding: utf-8 -*-
"""
JIUMI 提示词工作台 — 启动器（开发 / 测试用）。

职责：
  1. 把 PySide6 的本地依赖目录（.deps，pip --target 安装）挂进 sys.path；
  2. 把项目根目录挂进 sys.path，使 `import core` / `import gui.workbench_app` 可用；
  3. 启动 PySide6 主窗口。

正式分发时由 PyInstaller 打包，无需此脚本（依赖随 EXE 内联）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                       # 项目根 -> core / gui
DEPS = os.path.join(HERE, ".deps")
if os.path.isdir(DEPS):
    sys.path.insert(0, DEPS)                   # 开发期 PySide6

def main():
    from gui.workbench_app import MainWindow
    from PySide6.QtWidgets import QApplication
    import sys as _sys

    app = QApplication(_sys.argv)
    w = MainWindow()
    w.show()
    _sys.exit(app.exec())

if __name__ == "__main__":
    main()
