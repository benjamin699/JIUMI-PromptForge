@echo off
chcp 936 >nul
setlocal

REM 清代理变量：否则手机访问可能被系统代理拦截，导致打不开页面
set http_proxy=
set https_proxy=
set HTTP_PROXY=
set HTTPS_PROXY=
set all_proxy=
set ALL_PROXY=
set no_proxy=*
set NO_PROXY=*

set "PY=C:\Users\jiumi\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if not exist "%PY%" (
  echo [错误] 未找到 Python：%PY%
  pause
  exit /b 1
)

cd /d "%~dp0"
echo JIUMI 移动端服务（崩溃自动重启，关闭本窗口即停止）
echo 本机: http://127.0.0.1:8000   手机(同WiFi): 查服务启动后输出的局域网地址
echo.

:loop
echo [%date% %time%] 启动 backend.py...
"%PY%" backend.py >> server_run.log 2>&1
echo [%date% %time%] backend.py 已退出（代码 %errorlevel%），2 秒后重启...
timeout /t 2 /nobreak >nul
goto loop
