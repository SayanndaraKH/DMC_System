@echo off
chcp 65001 >nul
title Stop DMS Server
cd /d "%~dp0"

echo ============================================================
echo   STOPPING DMS SERVER (Port 8000)...
echo ============================================================
echo.

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)

powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo.
echo [OK] DMS Server (Port 8000) ត្រូវបានបិទជោគជ័យ!
echo.
timeout /t 2 >nul
