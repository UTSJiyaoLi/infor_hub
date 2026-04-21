@echo off
setlocal

rem Infor Hub remote service manager (gpu6000 via jump host)
rem Usage:
rem   .\scripts\ops\infor_services.cmd status
rem   .\scripts\ops\infor_services.cmd start
rem   .\scripts\ops\infor_services.cmd stop
rem   .\scripts\ops\infor_services.cmd restart
rem   .\scripts\ops\infor_services.cmd health
rem   .\scripts\ops\infor_services.cmd logs

set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=status"

set "JUMP_HOST=%INFOR_JUMP_HOST%"
if "%JUMP_HOST%"=="" set "JUMP_HOST=lijiyao@172.30.3.166"

set "TARGET_HOST=%INFOR_TARGET_HOST%"
if "%TARGET_HOST%"=="" set "TARGET_HOST=lijiyao@gpu6000"

set "REMOTE_WORKDIR=%INFOR_REMOTE_WORKDIR%"
if "%REMOTE_WORKDIR%"=="" set "REMOTE_WORKDIR=/share/home/lijiyao/CCCC/Infor_hub"

set "REMOTE_CONDA_ENV=%INFOR_REMOTE_CONDA_ENV%"
if "%REMOTE_CONDA_ENV%"=="" set "REMOTE_CONDA_ENV=rag_task"

set "REMOTE_HOST=%INFOR_REMOTE_HOST%"
if "%REMOTE_HOST%"=="" set "REMOTE_HOST=127.0.0.1"

set "REMOTE_PORT=%INFOR_REMOTE_PORT%"
if "%REMOTE_PORT%"=="" set "REMOTE_PORT=8000"

set "SESSION_NAME=%INFOR_SESSION_NAME%"
if "%SESSION_NAME%"=="" set "SESSION_NAME=infor-hub-api"

set "START_CMD=cd %REMOTE_WORKDIR% && source ~/.bashrc && conda activate %REMOTE_CONDA_ENV% && uvicorn api.app:app --host %REMOTE_HOST% --port %REMOTE_PORT%"

if /I "%ACTION%"=="status" goto status
if /I "%ACTION%"=="start" goto start
if /I "%ACTION%"=="stop" goto stop
if /I "%ACTION%"=="restart" goto restart
if /I "%ACTION%"=="health" goto health
if /I "%ACTION%"=="logs" goto logs

echo [ERROR] Unsupported action: %ACTION%
exit /b 1

:status
echo [INFO] Checking session %SESSION_NAME% on %TARGET_HOST% ...
ssh -J %JUMP_HOST% %TARGET_HOST% "tmux has-session -t %SESSION_NAME% 2>/dev/null && echo running || echo stopped"
exit /b %errorlevel%

:start
echo [INFO] Starting session %SESSION_NAME% on %TARGET_HOST% ...
ssh -J %JUMP_HOST% %TARGET_HOST% "tmux has-session -t %SESSION_NAME% 2>/dev/null || tmux new-session -d -s %SESSION_NAME% '%START_CMD'"
if errorlevel 1 exit /b 1
echo [INFO] Started (or already running).
exit /b 0

:stop
echo [INFO] Stopping session %SESSION_NAME% on %TARGET_HOST% ...
ssh -J %JUMP_HOST% %TARGET_HOST% "tmux kill-session -t %SESSION_NAME% 2>/dev/null || true"
if errorlevel 1 exit /b 1
echo [INFO] Stopped.
exit /b 0

:restart
call "%~f0" stop
if errorlevel 1 exit /b 1
call "%~f0" start
exit /b %errorlevel%

:health
echo [INFO] Checking remote health http://%REMOTE_HOST%:%REMOTE_PORT%/health ...
ssh -J %JUMP_HOST% %TARGET_HOST% "curl -sS http://%REMOTE_HOST%:%REMOTE_PORT%/health"
exit /b %errorlevel%

:logs
echo [INFO] Attaching to tmux session %SESSION_NAME% ...
ssh -t -J %JUMP_HOST% %TARGET_HOST% "tmux attach -t %SESSION_NAME%"
exit /b %errorlevel%
