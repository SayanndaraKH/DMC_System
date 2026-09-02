@echo off
title Document Management System (DMS) [Console / Debug Mode]
color 0b
cd /d "%~dp0"

echo ============================================================
echo   DOCUMENT MANAGEMENT SYSTEM (DMS) - CONSOLE DEBUG MODE
echo ============================================================
echo.

:: 0. Free Port 8000 from conflicting processes
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }" >nul 2>&1

:: 1. Detect Real Python (skip Microsoft Store aliases)
set "PY_BIN="

if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_BIN=%~dp0venv\Scripts\python.exe"
    goto :found_python
)

if exist "C:\Program Files\Python311\python.exe" (
    set "PY_BIN=C:\Program Files\Python311\python.exe"
    goto :found_python
)

for /f "delims=" %%i in ('where python 2^>nul') do (
    if not "%%i"=="%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\python.exe" (
        if not defined PY_BIN (
            set "PY_BIN=%%i"
        )
    )
)

:found_python

if not defined PY_BIN (
    echo [ERROR] Python not found on this system!
    pause
    exit /b 1
)

:: 2. Run Database Migrations
echo [INFO] Checking database migrations...
"%PY_BIN%" manage.py migrate --noinput >nul 2>&1

:: 3. Show Success Banner
echo.
echo ============================================================
echo   DMS SERVER IS RUNNING IN CONSOLE MODE
echo ============================================================
echo   - Local Access:   http://127.0.0.1:8000
echo   - Network Access: http://localhost:8000
echo ============================================================
echo   (Press Ctrl+C to stop the server)
echo.

:: 4. Open browser automatically
start "" "http://127.0.0.1:8000"

:: 5. Start Server with live console
"%PY_BIN%" manage.py runserver 0.0.0.0:8000
pause
