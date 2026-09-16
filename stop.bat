@echo off
title Stop DMS Server
color 0c
cd /d "%~dp0"

echo ============================================================
echo   STOPPING DOCUMENT MANAGEMENT SYSTEM (DMS)...
echo ============================================================
echo.

:: 1. Attempt graceful shutdown via run.py --stop
set "PY_BIN="
if exist "%~dp0venv\Scripts\python.exe" set "PY_BIN=%~dp0venv\Scripts\python.exe"
if not defined PY_BIN if exist "C:\Program Files\Python311\python.exe" set "PY_BIN=C:\Program Files\Python311\python.exe"
if not defined PY_BIN set "PY_BIN=python.exe"

"%PY_BIN%" "%~dp0run.py" --stop >nul 2>&1

:: 2. Terminate any remaining process listening on Port 8000
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }" >nul 2>&1

:: 3. Terminate any remaining run.py or manage.py runserver processes
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run.py*' -or $_.CommandLine -like '*manage.py runserver*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

:: 4. Clean up PID file if present
if exist "%~dp0dms.pid" del /f /q "%~dp0dms.pid" >nul 2>&1

echo [OK] DMS Server (Port 8000) has been stopped successfully.
echo.
ping 127.0.0.1 -n 2 >nul 2>&1
exit
