@echo off
chcp 65001 >nul
title Remove Auto-Start DMS
cd /d "%~dp0"

echo ============================================================
echo   លុបការកំណត់ Auto-Start DMS ពេលបើកកុំព្យូទ័រ
echo ============================================================
echo.

powershell -NoProfile -Command "$shortcut = [Environment]::GetFolderPath('Startup') + '\DMS_AutoStart.lnk'; if (Test-Path $shortcut) { Remove-Item $shortcut -Force; Write-Host '✅ បានលុបការកំណត់ Auto-Start រួចរាល់!' } else { Write-Host 'ℹ️ មិនមានការកំណត់ Auto-Start ពីមុនមកទេ។' }"

echo.
pause
