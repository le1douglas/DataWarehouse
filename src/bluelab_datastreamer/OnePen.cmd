@echo off
rem Starts the OnePen bridge in the background of this window, and the drip and drain readings here,
rem in a datastreamer container, where the pen is chosen. Both end together: on q, and when this window is
rem closed, as closing a window ends every program in it.
title OnePen
rem the repo root, two folders up from this file, wherever the repo is
cd /d "%~dp0..\.."

rem what an earlier run may have left, such as a bridge that still holds the port
call :cleanup

rem the bridge writes to a log instead of this window, so it does not draw over the readings
set "BRIDGE_LOG=%TEMP%\onepen_bridge.log"
start "" /b cmd /c "uv run src\bluelab_datastreamer\onepen_bridge.py > "%BRIDGE_LOG%" 2>&1"

rem a container of its own, removed after (--rm), with a fixed name so cleanup finds it. it needs no
rem database, and the daily folder (DAILY_RAW_CSV_DIR in .env) is mounted by compose. it retries every
rem 2 seconds until the bridge listens
docker compose -f compose.yaml -f compose.dev.yaml run --rm --name onepen-drip-drain datastreamer
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
