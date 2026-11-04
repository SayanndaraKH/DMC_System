@echo off
title Document Management System (DMS)
cd /d "%~dp0"

:: 0. Free Port 8000 from old processes
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }" >nul 2>&1

:: 1. Detect Real Python (skip Microsoft Store aliases)
set "PY_BIN="
set "PYW_BIN="

if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_BIN=%~dp0venv\Scripts\python.exe"
    set "PYW_BIN=%~dp0venv\Scripts\pythonw.exe"
    goto :found_python
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    set "PYW_BIN=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
    goto :found_python
)

if exist "C:\Program Files\Python312\python.exe" (
    set "PY_BIN=C:\Program Files\Python312\python.exe"
    set "PYW_BIN=C:\Program Files\Python312\pythonw.exe"
    goto :found_python
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    set "PYW_BIN=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
    goto :found_python
)

if exist "C:\Program Files\Python311\python.exe" (
    set "PY_BIN=C:\Program Files\Python311\python.exe"
    set "PYW_BIN=C:\Program Files\Python311\pythonw.exe"
    goto :found_python
)

for /f "delims=" %%i in ('where python 2^>nul') do (
    if not "%%i"=="%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\python.exe" (
        if not defined PY_BIN (
            set "PY_BIN=%%i"
        )
    )
)

for /f "delims=" %%i in ('where pythonw 2^>nul') do (
    if not "%%i"=="%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\pythonw.exe" (
        if not defined PYW_BIN (
            set "PYW_BIN=%%i"
        )
    )
)

:found_python

if not defined PY_BIN (
    echo [ERROR] Python not found on this system!
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

if not defined PYW_BIN (
    set "PYW_BIN=%PY_BIN%"
)

:: 2. Run database migrations
echo [INFO] Checking database migrations...
"%PY_BIN%" manage.py migrate --noinput >nul 2>&1

:: 3. Detect and Update Active LAN / Wi-Fi IP automatically
"%PY_BIN%" "%~dp0get_lan_ip.py" >nul 2>&1

:: 4. Start Server in Background
start "" "%PYW_BIN%" manage.py runserver 0.0.0.0:8000

:: 5. Wait for server startup safely (up to 45 seconds)
echo [INFO] Waiting for DMS Server to initialize...
powershell -NoProfile -Command "$w=0; while($w -lt 45){ try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/' -UseBasicParsing -TimeoutSec 1; if($r.StatusCode -in 200,302){ break } } catch { if($_.Exception.Response.StatusCode -in 200,302){ break } } Start-Sleep -Milliseconds 600; $w++ }" >nul 2>&1

:: 6. Open browser
start "" "http://127.0.0.1:8000/login/"

:: 7. Close CMD window
exit
