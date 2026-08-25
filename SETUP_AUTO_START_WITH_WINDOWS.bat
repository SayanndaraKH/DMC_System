@echo off
chcp 65001 >nul
title Setup Auto-Start DMS with Windows
cd /d "%~dp0"

echo ============================================================
echo   កំណត់ឱ្យ DMS បើកដំណើរការដោយស្វ័យប្រវត្តពេលបើកកុំព្យូទ័រ
echo ============================================================
echo.

powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Startup') + '\DMS_AutoStart.lnk'); $s.TargetPath = '%~dp0RUN_DMS.bat'; $s.WorkingDirectory = '%~dp0'; $s.WindowStyle = 7; $s.Save()"

if %errorlevel% equ 0 (
    echo ✅ បានកំណត់ជោគជ័យ!
    echo លើកក្រោយនៅពេលបើកកុំព្យូទ័រ កម្មវិធី DMS នឹងដំណើរការដោយស្វ័យប្រវត្តិ។
) else (
    echo ❌ មានបញ្ហាក្នុងការកំណត់ សូមសាកល្បងម្ដងទៀត។
)

echo.
pause
