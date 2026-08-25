@echo off
title Remove Auto-Start DMS
color 0e
cd /d "%~dp0"

echo ============================================================
echo   REMOVE AUTO-START DMS
echo ============================================================
echo.

powershell -NoProfile -Command "$shortcut = [Environment]::GetFolderPath('Startup') + '\DMS_AutoStart.lnk'; if (Test-Path $shortcut) { Remove-Item $shortcut -Force; Write-Host '[SUCCESS] Auto-start shortcut removed successfully.' } else { Write-Host '[INFO] No auto-start shortcut was found.' }"

echo.
pause
