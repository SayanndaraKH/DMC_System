@echo off
title Setup DMS Auto-Start with Windows
color 0a
cd /d "%~dp0"

echo ==============================================================================
echo   DOCUMENT MANAGEMENT SYSTEM (DMS) - SETUP AUTO-START WITH WINDOWS
echo ==============================================================================
echo.
echo [INFO] កំពុងរៀបចំឱ្យ DMS ចាប់ផ្តើមដំណើរការស្វ័យប្រវត្តិក្នង Background ពេលបើកកុំព្យូទ័រ...
echo.

:: 1. Create Startup Shortcut in Windows Startup folder
powershell -NoProfile -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$startupFolder = [Environment]::GetFolderPath('Startup'); " ^
    "$shortcut = $ws.CreateShortcut($startupFolder + '\DMS_AutoStart.lnk'); " ^
    "$shortcut.TargetPath = '%~dp0start_background.vbs'; " ^
    "$shortcut.Arguments = '--autostart'; " ^
    "$shortcut.WorkingDirectory = '%~dp0'; " ^
    "$shortcut.Description = 'DMS Cambodia Background Local Server'; " ^
    "$shortcut.WindowStyle = 7; " ^
    "$shortcut.Save()"

if %errorlevel% neq 0 (
    echo [កំហុស] មិនអាចបង្កើត Startup Shortcut បានឡើយ!
    pause
    exit /b 1
)

:: 2. Create Desktop Shortcut for easy 1-click browser access
powershell -NoProfile -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$desktopFolder = [Environment]::GetFolderPath('Desktop'); " ^
    "$shortcut = $ws.CreateShortcut($desktopFolder + '\DMS System (Local Server).lnk'); " ^
    "$shortcut.TargetPath = 'http://127.0.0.1:8000/'; " ^
    "$shortcut.Description = 'បើកប្រព័ន្ធគ្រប់គ្រងឯកសារ និងព័ត៌មានមន្ត្រី (DMS)'; " ^
    "$shortcut.Save()"

echo ==============================================================================
echo   [ជោគជ័យ] បានកំណត់ AUTO-START ជាមួយ WINDOWS រួចរាល់ ១០០%!
echo   [SUCCESS] AUTO-START CONFIGURATION COMPLETED SUCCESSFULLY!
echo ==============================================================================
echo.
echo   1. រាល់ពេលបើកកុំព្យូទ័រ (Startup/Boot) ប្រព័ន្ធ DMS នឹងរត់ស្វ័យប្រវត្តិ
echo      នៅក្នុង Background ដោយគ្មានផ្ទាំងខ្មៅ CMD រំខានឡើយ។
echo   2. ទិន្នន័យ (Database) ត្រូវបានការពារដោយ Auto Safety Snapshot រាល់ពេល Boot។
echo   3. ឧបករណ៍ផ្សេងៗក្នុង Wi-Fi / LAN អាចចូលប្រើប្រាស់បានភ្លាមៗដោយរលូន។
echo   4. បានបង្កើត Shortcut លើ Desktop ឈ្មោះ "DMS System (Local Server)"
echo      សម្រាប់លោកអ្នកចុចបើក Browser បានគ្រប់ពេលវេលា។
echo.
echo ==============================================================================
echo   (ប្រសិនបើចង់បិទមុខងារ Auto-Start វិញ សូមរត់ឯកសារ remove_autostart.bat)
echo ==============================================================================
echo.
pause
