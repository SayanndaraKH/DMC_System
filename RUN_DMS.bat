@echo off
title Document Management System (DMS)
color 0b
cd /d "%~dp0"

echo ============================================================
echo   DOCUMENT MANAGEMENT SYSTEM (DMS) - STARTING UP...
echo ============================================================
echo.

:: 0. Free Port 8000 from conflicting processes
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }" >nul 2>&1

:: 1. Check Python installation
set "PY_CMD=python"
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_CMD=py"
    ) else (
        echo [ERROR] Python not found on this system!
        echo Please install Python from https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

:: 2. Activate virtual environment if present
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
    set "PY_CMD=python"
)

:: 3. Run Database Migrations
echo [INFO] Checking database migrations...
%PY_CMD% manage.py migrate --noinput >nul 2>&1

:: 4. Show Success Banner
echo.
echo ============================================================
echo   DMS SERVER IS RUNNING SUCCESSFULLY!
echo ============================================================
echo   - Local Access:  http://127.0.0.1:8000
echo   - Network Access: http://localhost:8000
echo ============================================================
echo   (Press Ctrl+C or close this window to stop the server)
echo.

:: 5. Open browser automatically
start "" "http://127.0.0.1:8000"

:: 6. Start Server
%PY_CMD% manage.py runserver 0.0.0.0:8000
pause
