@echo off
title Stop DMS Server
color 0c
cd /d "%~dp0"

echo ============================================================
echo   STOPPING DMS SERVER (Port 8000)...
echo ============================================================
echo.

powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }" >nul 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*manage.py runserver*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo [OK] DMS Server on Port 8000 stopped successfully.
echo.
timeout /t 1 >nul
exit
