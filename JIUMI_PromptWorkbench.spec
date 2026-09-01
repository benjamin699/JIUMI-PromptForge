# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run_workbench.py'],
    pathex=['C:/Users/jiumi/WorkBuddy/2026-08-30-19-48-49/jiumi_prompt_workbench/.deps', 'C:/Users/jiumi/WorkBuddy/2026-08-30-19-48-49/jiumi_prompt_workbench'],
    binaries=[],
    datas=[('assets/avatar.ico', 'assets'), ('assets/avatar.png', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 代码仅 import PySide6.QtCore / QtGui / QtWidgets，其余子模块全部排除
        'PySide6.QtQuick', 'PySide6.QtQuickControls2', 'PySide6.QtQuickWidgets', 'PySide6.QtQuick3D',
        'PySide6.QtQml', 'PySide6.QtQmlModels',
        'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
        'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput', 'PySide6.Qt3DLogic',
        'PySide6.Qt3DExtras', 'PySide6.Qt3DAnimation',
        'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtGraphs', 'PySide6.QtGraphsWidgets',
        'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'PySide6.QtSpatialAudio',
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick', 'PySide6.QtWebChannel',
        'PySide6.QtLocation', 'PySide6.QtPositioning', 'PySide6.QtBluetooth', 'PySide6.QtNfc',
        'PySide6.QtSerialPort', 'PySide6.QtSerialBus', 'PySide6.QtSensors', 'PySide6.QtScxml', 'PySide6.QtRemoteObjects',
        'PySide6.QtTextToSpeech', 'PySide6.QtNetworkAuth', 'PySide6.QtHelp',
        'PySide6.QtDesigner', 'PySide6.QtUiTools', 'PySide6.QtAxContainer', 'PySide6.QtStateMachine',
        'PySide6.QtPrintSupport', 'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets', 'PySide6.QtShaderTools',
        'PySide6.QtXml', 'PySide6.QtXmlPatterns', 'PySide6.QtSql', 'PySide6.QtDBus', 'PySide6.QtConcurrent', 'PySide6.QtTest',
        'PySide6.QtHttpServer',
        'PyQt5', 'PyQt6', 'PySide2',
    ],
    noarchive=False,
    optimize=2,
)

# —— 体积精简：PySide6 hook 会全量收集 Qt6*.dll，需手动剔除未用项 ——
# 1) 软件 OpenGL 光栅器（纯控件界面用不到，约 19.7MB）
a.binaries = [b for b in a.binaries if not b[0].lower().endswith('opengl32sw.dll')]
# 2) 按模块名剔除其余未使用的 Qt6 动态库
_DROP = (
    'qt6quick', 'qt6qml', 'qt6pdf', 'qt6webengine', 'qt6webchannel', 'qt6location',
    'qt6positioning', 'qt6bluetooth', 'qt6nfc', 'qt6multimedia', 'qt6spatialaudio',
    'qt6charts', 'qt6datavisualization', 'qt6graph', 'qt6graph', 'qt63d', 'qt6scxml',
    'qt6serialbus', 'qt6serialport', 'qt6texttospeech', 'qt6sensors', 'qt6help',
    'qt6designer', 'qt6uitools', 'qt6axcontainer', 'qt6printsupport', 'qt6opengl',
    'qt6openglwidgets', 'qt6shadertools', 'qt6dbus', 'qt6statemachine', 'qt6xml',
    'qt6sql', 'qt6concurrent', 'qt6test', 'qt6httpserver', 'qt6labs', 'qt6remoteobjects',
)
a.binaries = [b for b in a.binaries if not any(b[0].lower().startswith(n) for n in _DROP)]
# 3) 翻译仅保留中文（.qm），剔除其余多语种（约 6MB）
a.datas = [d for d in a.datas if not (d[0].lower().endswith('.qm') and 'zh' not in d[0].lower())]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='JIUMI_PromptWorkbench',
    icon='assets/avatar.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
