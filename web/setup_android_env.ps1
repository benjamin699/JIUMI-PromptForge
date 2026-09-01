# setup_android_env.ps1  (ASCII-only, no Chinese)
# JIUMI PromptForge APK build env installer (Windows)
# Strategy: local-first (Downloads zips) + self-healing mirror fetch.
# No sdkmanager / no --proxy hacks: SDK files are placed by unzip + license file.
# Run in Admin PowerShell:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   cd <dir of this script>
#   .\setup_android_env.ps1
# Optional: .\setup_android_env.ps1 -Probe   (only print which mirror URLs resolve, no download)

param([switch]$Probe)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$Toolchain = Join-Path $ScriptDir ".toolchain"
$Tmp       = Join-Path $Toolchain "tmp"
$SdkRoot   = Join-Path $env:LOCALAPPDATA "Android\Sdk"
$JdkDir    = Join-Path $Toolchain "jdk-17"
$GradleDir = Join-Path $Toolchain "gradle-8.2.1"
$Downloads = Join-Path $env:USERPROFILE "Downloads"
New-Item -ItemType Directory -Force -Path $Toolchain, $Tmp, $SdkRoot | Out-Null

# Mirror roots that mirror dl.google.com/android/repository/ (flat file layout)
$SdkRoots = @(
  "https://mirrors.tuna.tsinghua.edu.cn/AndroidSDK/",
  "https://mirrors.cloud.tencent.com/AndroidSDK/",
  "https://mirrors.aliyun.com/AndroidSDK/",
  "https://mirrors.huaweicloud.com/android/repository/"
)
$GradleRoots = @(
  "https://mirrors.tuna.tsinghua.edu.cn/gradle/",
  "https://mirrors.cloud.tencent.com/gradle/"
)
$Jdk17Roots = @(
  "https://mirrors.tuna.tsinghua.edu.cn/Adoptium/17/jdk/x64/windows/",
  "https://mirrors.cloud.tencent.com/Adoptium/17/jdk/x64/windows/"
)

function Write-Step($m){ Write-Host ""; Write-Host "=== $m ===" -ForegroundColor Cyan }
function Write-Ok($m){ Write-Host "  $m" -ForegroundColor Green }
function Write-Warn($m){ Write-Host "  $m" -ForegroundColor Yellow }
function Write-Err($m){ Write-Host "  $m" -ForegroundColor Red }

function Fetch($url, $outPath){
  Write-Host "  GET $url"
  $ok = $false
  for ($i = 1; $i -le 3; $i++){
    try {
      Invoke-WebRequest -Uri $url -OutFile $outPath -UseBasicParsing -TimeoutSec 600 -ErrorAction Stop
      $ok = $true; break
    } catch {
      Write-Warn "    attempt $i failed: $_"
      Start-Sleep -Seconds 2
    }
  }
  if (-not $ok){ throw "download failed: $url" }
  Write-Ok ("  OK {0} MB" -f [math]::Round((Get-Item $outPath).Length/1MB, 1))
}

function Expand-Zip($zip, $dest){
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  Expand-Archive -Path $zip -DestinationPath $dest -Force
}

function Find-LocalZip($patterns){
  $files = Get-ChildItem $Downloads -Filter *.zip -ErrorAction SilentlyContinue
  foreach ($p in $patterns){
    $m = $files | Where-Object { $_.Name -match $p } | Select-Object -First 1
    if ($m){ return $m.FullName }
  }
  return $null
}

function Resolve-MirrorUrl($roots, $pattern, $candidates){
  foreach ($root in $roots){
    try {
      $resp = Invoke-WebRequest -Uri $root -UseBasicParsing -TimeoutSec 25 -ErrorAction Stop
      $hrefs = [regex]::Matches($resp.Content, 'href="([^"]+)"') | ForEach-Object { $_.Groups[1].Value }
      $pick = $hrefs | Where-Object { $_ -match $pattern } | Sort-Object -Descending | Select-Object -First 1
      if ($pick){
        if ($pick -match '^https?://'){ return $pick }
        return ($root.TrimEnd('/') + '/' + $pick.TrimStart('/'))
      }
    } catch {}
  }
  foreach ($c in $candidates){
    try {
      $r = Invoke-WebRequest -Uri $c -Method Head -UseBasicParsing -TimeoutSec 25 -ErrorAction Stop
      if ([int]$r.StatusCode -eq 200){ return $c }
    } catch {}
  }
  return $null
}

function Find-JavaExe($root){
  return Get-ChildItem $root -Recurse -Filter java.exe -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match '\\bin\\java\.exe$' } | Select-Object -First 1
}

function Find-InstalledJdk($major){
  $bases = @("C:\Program Files\Eclipse Adoptium", "C:\Program Files\Java",
             "C:\Program Files\Microsoft", "C:\Program Files\AdoptOpenJDK")
  foreach ($b in $bases){
    if (Test-Path $b){
      $d = Get-ChildItem $b -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match "jdk-$major(\.|$|\+)" } | Select-Object -First 1
      if ($d -and (Test-Path (Join-Path $d.FullName "bin\java.exe"))){ return $d.FullName }
    }
  }
  return $null
}

function Install-SdkZip($zip, $targetRel, $innerName){
  $x = Join-Path $Tmp ("x_" + [guid]::NewGuid().ToString("N"))
  Expand-Zip $zip $x
  $src = Join-Path $x $innerName
  if (-not (Test-Path $src)){ throw "expected folder '$innerName' not found inside zip" }
  $dst = Join-Path $SdkRoot $targetRel
  New-Item -ItemType Directory -Force -Path $dst | Out-Null
  Get-ChildItem $src | Move-Item -Destination $dst -Force
  Remove-Item $x -Recurse -Force
}

function Ensure-SdkComp($targetRel, $innerName, $patterns, $roots, $pattern, $candidates){
  $dst = Join-Path $SdkRoot $targetRel
  if (Test-Path $dst){ Write-Ok "$targetRel exists, skip."; return $true }
  $zip = Find-LocalZip $patterns
  if (-not $zip){
    $url = Resolve-MirrorUrl $roots $pattern $candidates
    if ($url){ $zip = Join-Path $Tmp ($innerName + ".zip"); Fetch $url $zip }
  }
  if (-not $zip){ Write-Err "MISSING $targetRel : drop a matching zip in $Downloads or fix mirrors"; return $false }
  try { Install-SdkZip $zip $targetRel $innerName }
  catch { Write-Err "extract failed: $_"; return $false }
  Write-Ok "installed $targetRel"
  return $true
}

# ---------- Probe mode ----------
if ($Probe){
  Write-Step "PROBE mirror reachability (no download)"
  $probes = @(
    ("JDK17 ", $Jdk17Roots, "OpenJDK17U-jdk_x64_windows_hotspot_17\.0\.\d+_\d+\.zip"),
    ("cmdline", $SdkRoots, "commandlinetools-win-\d+_latest\.zip"),
    ("platform-34", $SdkRoots, "platform-34_r\d+\.zip"),
    ("build-tools", $SdkRoots, "build-tools_r34\.0\.0-windows\.zip"),
    ("gradle", $GradleRoots, "gradle-8\.2\.1-all\.zip")
  )
  foreach ($p in $probes){
    $u = Resolve-MirrorUrl $p[1] $p[2] @()
    if ($u){ Write-Ok ($p[0] + " -> " + $u) } else { Write-Err ($p[0] + " -> NO MIRROR RESOLVED") }
  }
  Write-Host ""
  Write-Host "Local zips in Downloads:" -ForegroundColor Cyan
  Get-ChildItem $Downloads -Filter *.zip -ErrorAction SilentlyContinue | ForEach-Object { Write-Host ("  " + $_.Name) }
  exit 0
}

# ---------- 1/5 JDK 17 ----------
Write-Step "1/5 JDK 17 (required by Gradle 8.2.1)"
$JAVA_HOME = Find-InstalledJdk 17
if ($JAVA_HOME){ Write-Ok "found installed JDK17: $JAVA_HOME" }
else {
  $zip = Find-LocalZip @('jdk-17', 'openjdk17', 'adoptium17', '17\.0\.\d+')
  if (-not $zip){
    $url = Resolve-MirrorUrl $Jdk17Roots "OpenJDK17U-jdk_x64_windows_hotspot_17\.0\.\d+_\d+\.zip" @()
    if ($url){ $zip = Join-Path $Tmp "jdk17.zip"; Fetch $url $zip }
  }
  if (-not $zip){ throw "JDK17 not found. Drop a JDK17 zip in Downloads or install Adoptium 17." }
  Expand-Zip $zip $JdkDir
  $je = Find-JavaExe $JdkDir
  if (-not $je){
    # WAPT-style package: real JDK ships as an embedded .msi -> admin-install it
    $msi = Get-ChildItem $JdkDir -Recurse -Filter *.msi -ErrorAction SilentlyContinue |
           Where-Object { $_.Name -match 'x64' } | Select-Object -First 1
    if (-not $msi){ $msi = Get-ChildItem $JdkDir -Recurse -Filter *.msi -ErrorAction SilentlyContinue | Select-Object -First 1 }
    if ($msi){
      Write-Warn "JDK zip is a WAPT package; admin-installing embedded $($msi.Name)"
      $inst = Join-Path $JdkDir "installed"
      $pr = Start-Process msiexec.exe -ArgumentList "/a `"$($msi.FullName)`" TARGETDIR=`"$inst`" /qn" -Wait -PassThru
      if ($pr.ExitCode -ne 0){ throw "msiexec admin-install failed (exit $($pr.ExitCode))" }
      $je = Find-JavaExe $inst
    }
  }
  if (-not $je){ throw "java.exe not found after JDK extract" }
  $JAVA_HOME = $je.DirectoryName.Replace("\bin", "")
}
Write-Ok "JAVA_HOME = $JAVA_HOME"
& (Join-Path $JAVA_HOME "bin\java.exe") -version
$Env:JAVA_HOME = $JAVA_HOME

# ---------- 2/5 platform-tools (local, optional for build, needed for adb install) ----------
Write-Step "2/5 platform-tools"
$ptZip = Find-LocalZip @('platform-tools')
if ($ptZip -and -not (Test-Path (Join-Path $SdkRoot "platform-tools\adb.exe"))){
  Write-Ok "use local platform-tools: $ptZip"
  Expand-Zip $ptZip (Join-Path $SdkRoot "platform-tools")
} elseif (Test-Path (Join-Path $SdkRoot "platform-tools\adb.exe")){
  Write-Ok "platform-tools exists, skip."
} else {
  Write-Warn "platform-tools missing (optional). Drop platform-tools-latest-windows.zip in Downloads to enable adb install."
}

# ---------- 3/5 platform-34 ----------
Write-Step "3/5 Android platform-34"
$ok34 = Ensure-SdkComp "platforms\android-34" "android-34" @('platform-34') $SdkRoots 'platform-34_r\d+\.zip' @()

# ---------- 4/5 build-tools 34.0.0 ----------
Write-Step "4/5 Android build-tools 34.0.0"
$okbt = Ensure-SdkComp "build-tools\34.0.0" "android-34.0.0" @('build-tools') $SdkRoots 'build-tools_r34\.0\.0-windows\.zip' @()

# ---------- license file (Gradle requires accepted SDK license) ----------
$licDir = Join-Path $SdkRoot "licenses"
New-Item -ItemType Directory -Force -Path $licDir | Out-Null
Set-Content (Join-Path $licDir "android-sdk-license") -Value "24333f8a63b6825ea9c5514f83c2829b004d1fee" -Encoding ASCII -NoNewline
Write-Ok "wrote $licDir\android-sdk-license"

# ---------- 5/5 Gradle 8.2.1 local dist ----------
Write-Step "5/5 Gradle 8.2.1 (local distribution)"
$grZip = Find-LocalZip @('gradle-8\.2\.1')
if (-not $grZip){
  $url = Resolve-MirrorUrl $GradleRoots 'gradle-8\.2\.1-all\.zip' @(
    "https://mirrors.cloud.tencent.com/gradle/gradle-8.2.1-all.zip",
    "https://mirrors.tuna.tsinghua.edu.cn/gradle/gradle-8.2.1-all.zip"
  )
  if ($url){ $grZip = Join-Path $Tmp "gradle.zip"; Fetch $url $grZip }
}
if (-not $grZip){
  Write-Err "Gradle 8.2.1 zip missing. Drop gradle-8.2.1-all.zip in Downloads or fix mirrors."
} else {
  $distLocal = Join-Path $ScriptDir "android\gradle-8.2.1-all.zip"
  Copy-Item $grZip $distLocal -Force
  Write-Ok "copied dist -> $distLocal"
}

# point gradlew to Tencent mirror dist (verified 200)
$wrap = Join-Path $ScriptDir "android\gradle\wrapper\gradle-wrapper.properties"
if (Test-Path $wrap){
  (Get-Content $wrap) -replace "distributionUrl=.*", "distributionUrl=https\://mirrors.cloud.tencent.com/gradle/gradle-8.2.1-all.zip" | Set-Content $wrap -Encoding ASCII
  Write-Ok "gradlew switched to Tencent mirror dist."
}

# local.properties so Gradle finds the SDK without ANDROID_HOME in this session
$lp = Join-Path $ScriptDir "android\local.properties"
$esc = $SdkRoot.Replace("\", "\\")
Set-Content $lp -Value ("sdk.dir=" + $esc) -Encoding ASCII
Write-Ok "wrote android\local.properties (sdk.dir)"

# init.gradle: force Aliyun maven (so offline-from-Google build works in CN)
$init = Join-Path $ScriptDir "android\init.gradle"
$initContent = @"
allprojects {
  buildscript {
    repositories {
      clear()
      maven { url 'https://maven.aliyun.com/repository/gradle-plugin' }
      maven { url 'https://maven.aliyun.com/repository/google' }
      maven { url 'https://maven.aliyun.com/repository/central' }
    }
  }
  repositories {
    clear()
    maven { url 'https://maven.aliyun.com/repository/google' }
    maven { url 'https://maven.aliyun.com/repository/gradle-plugin' }
    maven { url 'https://maven.aliyun.com/repository/central' }
    maven { url 'https://maven.aliyun.com/repository/public' }
  }
}
settingsEvaluated { settings ->
  settings.pluginManagement {
    repositories {
      maven { url 'https://maven.aliyun.com/repository/gradle-plugin' }
      maven { url 'https://maven.aliyun.com/repository/google' }
      maven { url 'https://maven.aliyun.com/repository/central' }
    }
  }
}
"@
Set-Content $init -Value $initContent -Encoding ASCII
Write-Ok "wrote android\init.gradle (Aliyun maven mirror)"

# ---------- env vars ----------
Write-Step "Write user env ANDROID_HOME / JAVA_HOME / Path"
[Environment]::SetEnvironmentVariable("ANDROID_HOME", $SdkRoot, "User")
[Environment]::SetEnvironmentVariable("JAVA_HOME", $JAVA_HOME, "User")
$path = [Environment]::GetEnvironmentVariable("Path", "User")
foreach ($p in @((Join-Path $SdkRoot "platform-tools"), (Join-Path $JAVA_HOME "bin"))){
  if ($path -notlike "*$p*"){ $path = "$p;$path" }
}
[Environment]::SetEnvironmentVariable("Path", $path, "User")

Write-Host ""
if (-not ($ok34 -and $okbt)){ Write-Err "Some SDK components missing - fix mirrors or drop zips in Downloads, then re-run." }
Write-Host "===== SETUP DONE =====" -ForegroundColor Green
Write-Host "JAVA_HOME    = $JAVA_HOME"
Write-Host "ANDROID_HOME = $SdkRoot"
Write-Host ""
Write-Host "Next (new terminal):" -ForegroundColor Cyan
Write-Host "  cd $ScriptDir\android"
Write-Host "  .\gradlew --init-script init.gradle assembleDebug"
Write-Host "APK: android\app\build\outputs\apk\debug\app-debug.apk"
