# JIUMI 提示词工作台（JIUMI-PromptForge）v7.2

基于 Krea2 文生图 / MiniMax H3 视频生成的提示词工程工具链，覆盖「武侠 / 国风 / 巨构 / 千禧年」等风格的提示词生成、剧本分镜与 ComfyUI 出图联调。

> **手机端 APK 请到右侧 [Releases](../../releases) 下载**（debug 包，未签名）。APK 是二进制，不进本仓库源码。

---

## 一、双端结构

### 桌面端（Windows，PySide6）
| 路径 | 说明 |
|---|---|
| `run_workbench.py` | 主入口（双击启动 GUI） |
| `gui/workbench_app.py` | PySide6 主界面 |
| `gui/comfy_push.py` | 推工作流到本地 ComfyUI |
| `core/` | 提示词核心词库（`mega_pack` / `krea2_pack` / `style_packs` / `wuxia_pack` / `y2k_pack`），纯标准库，约 3500 行，零外部依赖 |
| `JIUMI_PromptWorkbench.spec` | PyInstaller 打包配置 |
| `installer.iss` | Inno Setup 安装包脚本 |
| `assets/` | 图标、头像等资源 |

### 手机端（Android，Capacitor + Pyodide 离线）
| 路径 | 说明 |
|---|---|
| `web/index.html` | PWA 主界面（首屏进度条、历史导出/导入） |
| `web/static/pybridge.js` | Pyodide 0.26.4 离线 Python 引擎桥接（无需联网） |
| `web/android/` | Capacitor 安卓工程（包名 `com.jiumi.promptworkbench`） |
| `web/workflow_api.json` | 导出供 ComfyUI 直接导入的文生图工作流（已修 `SaveImage` 缺参） |

> 离线引擎（`web/www/pyodide/`）与安卓构建产物（`web/android/app/build/`、`web/.toolchain/`）已写入 `.gitignore`，不入库。

---

## 二、核心能力

- **结构化提示词生成**：巨构六维公式（Krea2 格式）、武侠/国风分镜模板、千禧年风格包
- **历史管理**：手机端支持历史记录 JSON 导出 / 导入（合并去重）
- **ComfyUI 出图联调**：默认地址 `http://127.0.0.1:8188`，工作流见 `web/workflow_api.json`

---

## 三、手机端连接电脑 ComfyUI 出图（三步）

App 默认 `127.0.0.1:8188` 指**手机自己**，要驱动电脑上的 ComfyUI：

1. 电脑启动 ComfyUI 时加 `--listen 0.0.0.0`
2. App 设置里把地址改成**电脑局域网 IP**：`http://192.168.1.x:8188`
3. 电脑防火墙放行 `8188` 端口

出图结果写到**电脑** ComfyUI 的 `output/` 目录。前提：ComfyUI `models/` 里已放对应 checkpoint / LoRA（App 不打包模型权重）。

---

## 四、本地构建（进阶）

### 桌面端 EXE
```bash
pip install pyinstaller pyside6
pyinstaller JIUMI_PromptWorkbench.spec
```

### 手机端 APK
```bash
cd web
npm install && npm run build        # 构建 PWA 静态资源
npx cap sync android                # 同步到安卓工程
cd android && gradlew assembleDebug # 产物在 app/build/outputs/apk/debug/
```
安卓工具链（JDK17 + SDK）需自行准备，构建脚本见 `web/setup_android_env.ps1`。

---

## 五、许可

个人 / 非商业使用。转载请保留署名。
