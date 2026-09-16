@echo off
title Remove DMS Auto-Start
color 0e
cd /d "%~dp0"

echo ==============================================================================
echo   DOCUMENT MANAGEMENT SYSTEM (DMS) - REMOVE AUTO-START
echo ==============================================================================
echo.
echo [INFO] កំពុងដកចេញមុខងារ Auto-Start ពី Windows Startup...
echo.

powershell -NoProfile -Command ^
    "$startupFolder = [Environment]::GetFolderPath('Startup'); " ^
    "$shortcut1 = $startupFolder + '\DMS_AutoStart.lnk'; " ^
    "if (Test-Path $shortcut1) { Remove-Item $shortcut1 -Force; Write-Host '[OK] បានលុប Shortcut ពី Startup Folder រួចរាល់។' } else { Write-Host '[INFO] គ្មាន Shortcut ក្នុង Startup Folder ឡើយ។' }; " ^
    "$desktopFolder = [Environment]::GetFolderPath('Desktop'); " ^
    "$shortcut2 = $desktopFolder + '\DMS System (Local Server).lnk'; " ^
    "if (Test-Path $shortcut2) { Remove-Item $shortcut2 -Force; Write-Host '[OK] បានលុប Shortcut ពី Desktop រួចរាល់។' }"

echo.
echo ==============================================================================
echo   [ជោគជ័យ] បានបិទមុខងារ AUTO-START រួចរាល់!
echo   ប្រព័ន្ធ DMS នឹងមិនចាប់ផ្តើមដោយស្វ័យប្រវត្តិក្នង Windows ទៀតឡើយ។
echo   (លោកអ្នកអាចបើកប្រព័ន្ធដោយដៃតាមរយៈ start.bat នៅពេលត្រូវការ)
echo ==============================================================================
echo.
pause
