@echo off
title DMS Auto-Shutdown Timer
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0shutdown_timer.ps1"
exit /b 0
