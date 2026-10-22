@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title DMC System - Android APK Builder
python "%~dp0build_apk.py"
if errorlevel 1 (
    echo.
    echo [ERROR] An error occurred while running build_apk.py.
    pause
)
