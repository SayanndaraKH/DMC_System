@echo off
chcp 65001 >nul
title Document Management System (DMS)
cd /d "%~dp0"

echo ============================================================
echo   DOCUMENT MANAGEMENT SYSTEM (DMS) - STARTING UP...
echo ============================================================
echo.

:: 0. Free Port 8000 from any stuck or conflicting processes
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)

:: 1. Check Python installation
set "PY_CMD="
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
) else (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_CMD=py"
    )
)

if "%PY_CMD%"=="" (
    echo [ERROR] មិនទាន់មាន Python នៅលើកុំព្យូទ័រនេះទេ!
    echo សូមដំឡើង Python ពី https://www.python.org/downloads/
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 2. Check Virtual Environment or Dependencies
if exist "venv\Scripts\activate.bat" (
    echo [INFO] កំពុងដំណើរការតាមរយៈ Virtual Environment...
    call "venv\Scripts\activate.bat"
    set "PY_CMD=python"
)

:: 3. Run Database Migrations
echo [INFO] កំពុងពិនិត្យ Database...
%PY_CMD% manage.py migrate --noinput >nul 2>&1

:: 4. Show Success Banner
echo.
echo ============================================================
echo   SERVER បានដំណើរការជោគជ័យ!
echo ============================================================
echo   - ចូលប្រើលើកុំព្យូទ័រផ្ទាល់: http://127.0.0.1:8000
echo   - ឬ:                         http://localhost:8000
echo ============================================================
echo   (ដើម្បីបិទ Server សូមចុចបិទផ្ទាំងនេះ ឬចុច Ctrl + C)
echo.

:: 5. Open browser automatically
start "" "http://127.0.0.1:8000"

:: 6. Start Server
%PY_CMD% manage.py runserver 0.0.0.0:8000
pause
