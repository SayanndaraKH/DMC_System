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
"%PY_BIN%" -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)) if True else None; ip = s.getsockname()[0]; s.close(); open('IP.txt', 'w', encoding='utf-8').write(f'✅ អាសយដ្ឋាន IP សម្រាប់ដំណើរការកម្មវិធី DMS៖\n\n🔹 សម្រាប់ប្រើប្រាស់លើកុំព្យូទ័រផ្ទាល់ (Localhost):\n👉 http://127.0.0.1:8000/\n👉 http://localhost:8000/\n\n🔹 សម្រាប់ទូរស័ព្ទ ឬកុំព្យូទ័រផ្សេងទៀតក្នុងបណ្តាញ Wi-Fi / LAN តែមួយ (Network IP):\n👉 http://{ip}:8000/\n\n---\n(បានធ្វើបច្ចុប្បន្នភាពស្វ័យប្រវត្តិតាម IP បណ្តាញ Wi-Fi/LAN ជាក់ស្តែង)\n')" >nul 2>&1

:: 4. Start Server in Background
start "" "%PYW_BIN%" manage.py runserver 0.0.0.0:8000

:: 5. Wait for server startup
timeout /t 2 >nul

:: 6. Open browser
start "" "http://127.0.0.1:8000"

:: 7. Close CMD window
exit
