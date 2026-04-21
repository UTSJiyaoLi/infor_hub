@echo off
setlocal

rem One-click local tunnel + open Infor Hub web frontend
rem local browser -> localhost:<auto-port> tunnel -> lijiyao jump -> gpu6000:127.0.0.1:<remote-port>

set "JUMP_HOST=%INFOR_JUMP_HOST%"
if "%JUMP_HOST%"=="" set "JUMP_HOST=lijiyao@172.30.3.166"

set "TARGET_HOST=%INFOR_TARGET_HOST%"
if "%TARGET_HOST%"=="" set "TARGET_HOST=lijiyao@gpu6000"

set "LOCAL_PORT=%~1"
set "REMOTE_HOST=%INFOR_REMOTE_HOST%"
if "%REMOTE_HOST%"=="" set "REMOTE_HOST=127.0.0.1"

set "REMOTE_PORT=%INFOR_REMOTE_PORT%"
if "%REMOTE_PORT%"=="" set "REMOTE_PORT=8000"

set "TUNNEL_TITLE=infor-hub-tunnel"

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "REPO_ROOT=%%~fI"
set "WEB_URL=http://127.0.0.1:3000"

if "%LOCAL_PORT%"=="" (
  for /f %%P in ('powershell -NoProfile -Command "$l = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback,0); $l.Start(); $p=$l.LocalEndpoint.Port; $l.Stop(); Write-Output $p"') do set "LOCAL_PORT=%%P"
)

set "TUNNEL_TITLE=%TUNNEL_TITLE%-%LOCAL_PORT%"
set "BACKEND_URL=http://127.0.0.1:%LOCAL_PORT%"

echo [1/3] Starting SSH tunnel in new window...
start "%TUNNEL_TITLE%" cmd /k "ssh -L %LOCAL_PORT%:%REMOTE_HOST%:%REMOTE_PORT% -J %JUMP_HOST% %TARGET_HOST%"

echo [2/3] Starting Next.js frontend (new window)...
start "infor-hub-web" cmd /k "cd /d %REPO_ROOT%\apps\web && npm run dev"

echo [3/3] Opening browser...
timeout /t 2 /nobreak >nul
start "" "%WEB_URL%"

echo.
echo Done.
echo - Keep the "%TUNNEL_TITLE%" window open while using the web page.
echo - Backend via tunnel: %BACKEND_URL%
echo - Health URL: %BACKEND_URL%/health
echo - In Web UI, set Backend URL = %BACKEND_URL%

endlocal
