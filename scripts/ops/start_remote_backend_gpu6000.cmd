@echo off
setlocal

rem Backward-compatible remote starter for Infor Hub backend.

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

call scripts\ops\infor_services.cmd start
if errorlevel 1 (
  echo [ERROR] failed to start Infor Hub backend service.
  exit /b 1
)

call scripts\ops\infor_services.cmd health
if errorlevel 1 (
  echo [WARN] health check failed; use scripts\ops\infor_services.cmd logs to inspect.
  exit /b 1
)

echo Infor Hub backend is ready.
exit /b 0
