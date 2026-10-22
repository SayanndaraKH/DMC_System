@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title DMC System - Auto Build Android APK into dist/

echo ==============================================================================
echo   📱 ប្រព័ន្ធ DMC SYSTEM - ដំណើរការបង្កើត File APK ចូល dist/ ដោយស្វ័យប្រវត្ត
echo ==============================================================================
echo.

python "%~dp0build_apk.py" --auto
if errorlevel 1 (
    echo.
    echo ❌ [កំហុស] មានបញ្ហាក្នុងដំណើរការបង្កើត APK សូមពិនិត្យមើលសារខាងលើ។
)

echo.
pause
