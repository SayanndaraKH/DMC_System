@echo off
chcp 65001 >nul
title Stop DMS Server
cd /d "%~dp0"

echo ============================================================
echo   STOPPING DMS SERVER...
echo ============================================================
echo.

powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

echo ✅ DMS Server ត្រូវបានបិទជោគជ័យ!
echo.
timeout /t 3
