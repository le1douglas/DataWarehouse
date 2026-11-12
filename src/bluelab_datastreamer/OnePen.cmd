@echo off
rem Starts the OnePen bridge in the background of this window, and the drip and drain readings here,
rem in a datastreamer container, where the pen is chosen. Both end together: on q, and when this window is
rem closed, as closing a window ends every program in it.
title OnePen
rem the repo root, two folders up from this file, wherever the repo is
cd /d "%~dp0..\.."

rem what an earlier run may have left, such as a bridge that still holds the port
call :cleanup

rem prod: the datastreamer image of the git tag in RELEASE (docker\.env.prod), built by docker\03_setup_prod.ps1. a
rem missing image stops here: compose would otherwise build one from whatever is checked out, not from the tag
set "RELEASE="
if exist docker\.env.prod (
    for /f "tokens=1,* delims==" %%a in ('findstr /b /c:"RELEASE=" docker\.env.prod') do set "RELEASE=%%b"
)
if not defined RELEASE (
    echo # error: no RELEASE= line in docker\.env.prod. run: powershell -ExecutionPolicy Bypass -File docker\01_setup_env.ps1
    pause
    exit /b 1
)
docker image inspect datastreamer:%RELEASE% >nul 2>&1
if errorlevel 1 (
    echo # error: no datastreamer:%RELEASE% image. run: powershell -ExecutionPolicy Bypass -File docker\03_setup_prod.ps1
    pause
    exit /b 1
)

rem the bridge writes to a log instead of this window, so it does not draw over the readings
set "BRIDGE_LOG=%TEMP%\onepen_bridge.log"
start "" /b cmd /c "uv run src\bluelab_datastreamer\onepen_bridge.py > "%BRIDGE_LOG%" 2>&1"

rem a container of its own in dw-prod, removed after (--rm), with a fixed name so cleanup finds it. it needs no
rem database. compose mounts the output folder (USER_OUTPUT_DIR in docker\.env.prod) and the work-in-progress volume
rem of prod. it retries every 2 seconds until the bridge listens. dev, from a branch, by hand:
rem   docker compose -f docker/compose.yaml -f docker/compose.dev.yaml run --rm datastreamer
docker compose -f docker/compose.yaml -f docker/compose.prod.yaml --env-file docker/.env.prod run --rm --name onepen-drip-drain datastreamer
set "EXITCODE=%ERRORLEVEL%"

call :cleanup

rem keep the window open on an error, so the message can be read
if not "%EXITCODE%"=="0" (
    echo the log of the bridge is %BRIDGE_LOG%
    pause
)
exit /b %EXITCODE%

rem ends the bridge (uv and its python) and removes the readings container
:cleanup
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -in 'python.exe','uv.exe' -and $_.CommandLine -like '*onepen_bridge.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
docker rm -f onepen-drip-drain >nul 2>&1
exit /b 0
