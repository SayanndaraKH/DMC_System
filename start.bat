@echo off
title Document Management System (DMS)
color 0b
cd /d "%~dp0"

:: Check if user requested console/debug mode
if /i "%1"=="console" goto :console_mode
if /i "%1"=="debug" goto :console_mode

:: ============================================================
:: 1. BACKGROUND MODE (Runs silently & opens browser)
:: ============================================================
echo ============================================================
echo   DOCUMENT MANAGEMENT SYSTEM (DMS) - STARTING...
echo ============================================================
echo.
echo [INFO] Starting DMS Server in Windows Background...

:: 0. Free Port 8000 from old processes
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }" >nul 2>&1

:: Launch via VBScript silently
wscript.exe "%~dp0start_background.vbs"

:: Wait for server startup safely (up to 45 seconds)
echo [INFO] Waiting for DMS Server to initialize...
powershell -NoProfile -Command "$w=0; while($w -lt 45){ try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/' -UseBasicParsing -TimeoutSec 1; if($r.StatusCode -in 200,302){ break } } catch { if($_.Exception.Response.StatusCode -in 200,302){ break } } Start-Sleep -Milliseconds 600; $w++ }" >nul 2>&1

echo [OK] DMS is running in the background.
echo [OK] Opening your web browser to http://127.0.0.1:8000/login/ ...
start "" "http://127.0.0.1:8000/login/"

echo.
echo ============================================================
echo   To stop the server at any time, double-click STOP.BAT
echo ============================================================
ping 127.0.0.1 -n 2 >nul 2>&1
exit

:: ============================================================
:: 2. CONSOLE / DEBUG MODE (Keep CMD window open with live logs)
:: ============================================================
:console_mode
echo ============================================================
echo   DOCUMENT MANAGEMENT SYSTEM (DMS) - CONSOLE DEBUG MODE
echo ============================================================
echo.

set "PY_BIN="
if exist "%~dp0venv\Scripts\python.exe" set "PY_BIN=%~dp0venv\Scripts\python.exe"
if not defined PY_BIN for /f "delims=" %%i in ('where python 2^>nul') do if not defined PY_BIN set "PY_BIN=%%i"
if not defined PY_BIN set "PY_BIN=python.exe"

"%PY_BIN%" "%~dp0run.py" --open-browser
pause
