; JIUMI 提示词工作台 — InnoSetup 安装包脚本
; 用法：用 InnoSetup (https://jrsoftware.org/isdl.php) 打开本文件，点击 Compile 生成 setup.exe
; 说明：
;  - 本脚本打包已生成的 dist\JIUMI_PromptWorkbench.exe（单文件、离线）
;  - 未签名：分发给他人时 Windows Defender 可能拦截，建议自购代码签名证书后
;    在 [Files] 之前用 signtool 对 exe 签名（见文末注释）
;  - OutputDir 默认 ..\out_installer，编译后在该目录得到 setup.exe

#define MyAppName "JIUMI 提示词工作台"
#define MyAppVersion "1.0"
#define MyAppPublisher "JIUMI"
#define MyAppExeName "JIUMI_PromptWorkbench.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-1234567890EF}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\out_installer
OutputBaseFilename=JIUMI_PromptWorkbench_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
SetupIconFile=
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

; ===== 代码签名（可选，需自购证书） =====
; 安装 InnoSetup 后，在编译前用 signtool 对 exe 签名：
;   signtool sign /fd SHA256 /t http://timestamp.digicert.com /a dist\JIUMI_PromptWorkbench.exe
; 或在 [Setup] 段加：SignTool=my-sign
;   [Setup] 内追加：SignTool=my-sign
;   并在 InnoSetup 的 Tools→Configure Sign Tools 里添加：
;   my-sign=$p\"C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe\" sign /fd SHA256 /t http://timestamp.digicert.com /a $f
