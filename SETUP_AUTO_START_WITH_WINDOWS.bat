@echo off
title Setup Auto-Start DMS with Windows
color 0a
cd /d "%~dp0"

echo ============================================================
echo   SETUP AUTO-START DMS WITH WINDOWS
echo ============================================================
echo.

powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Startup') + '\DMS_AutoStart.lnk'); $s.TargetPath = '%~dp0RUN_DMS_SILENT.vbs'; $s.WorkingDirectory = '%~dp0'; $s.WindowStyle = 7; $s.Save()"

if %errorlevel% equ 0 (
    echo [SUCCESS] Auto-start configured successfully!
    echo DMS will start silently when Windows starts up.
) else (
    echo [ERROR] Failed to configure auto-start.
)

echo.
pause
