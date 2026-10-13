@echo off
chcp 65001 >nul
title DMS - Setup Auto-Boot at Windows Startup (Before Login)
color 0b
cd /d "%~dp0"

:: 1. Check if running as Administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ==============================================================================
    echo   DOCUMENT MANAGEMENT SYSTEM (DMS) - SETUP AUTO-BOOT BEFORE LOGIN
    echo ==============================================================================
    echo.
    echo   [INFO] កំពុងស្នើសុំដំណើរការជា Administrator...
    echo   👉 សូមចុច "Yes" លើផ្ទាំង Windows UAC ប្រសិនបើវាបង្ហាញឡើង។
    echo.
    echo   (ចំណាំ៖ ប្រសិនបើចុច Double-Click មិនចេញផ្ទាំង Yes ទេ
    echo    សូម Right-Click [ចុចកណ្ដុរស្ដាំ] លើឯកសារនេះ រួចយក "Run as administrator")
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"\"%~dp0setup_auto_boot.ps1\"\"' -Verb RunAs"
    exit /b
)

:: If already Administrator, run setup script directly
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_auto_boot.ps1"
