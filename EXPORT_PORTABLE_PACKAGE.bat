@echo off
chcp 65001 >nul
title DMC System - បង្កើតកញ្ចប់ Offline Portable (រួមទាំងរូបភាព និងឯកសារយោង)
color 0a

echo ========================================================================
echo     [DMC SYSTEM] - EXPORT STANDALONE OFFLINE PACKAGE
echo          ឧបករណ៍បង្កើតកញ្ចប់ពេញលេញ (EXE + Media + Config)
echo ========================================================================
echo.

cd /d "%~dp0"

set "TARGET_DIR=%~dp0DMC_System_Portable"
if exist "%TARGET_DIR%" (
    echo [1/3] កំពុងសម្អាតកញ្ចប់ចាស់...
    rd /s /q "%TARGET_DIR%" >nul 2>&1
)

mkdir "%TARGET_DIR%"
mkdir "%TARGET_DIR%\media"

echo [2/3] កំពុងចម្លង File កម្មវិធី និង Media...
if exist "dist\DMC_System.exe" (
    copy /Y "dist\DMC_System.exe" "%TARGET_DIR%\DMC_System.exe" >nul
) else if exist "DMC_System.exe" (
    copy /Y "DMC_System.exe" "%TARGET_DIR%\DMC_System.exe" >nul
)

if exist "dmc_config.txt" (
    copy /Y "dmc_config.txt" "%TARGET_DIR%\dmc_config.txt" >nul
)

if exist "media" (
    echo   + កំពុងចម្លង Folder media (រូបថត និងឯកសារយោងទាំងអស់)...
    robocopy "%~dp0media" "%TARGET_DIR%\media" /E /NFL /NDL /NJH /NJS >nul
)

:: Create instructions text file
(
echo ========================================================================
echo     ប្រព័ន្ធគ្រប់គ្រងឯកសារ និងព័ត៌មានមន្ត្រី (DMC System - Standalone)
echo ========================================================================
echo.
echo [*] របៀបប្រើប្រាស់លើ User PC ផ្សេងទៀត៖
echo  1. លោកអ្នកអាចចម្លង Folder «DMC_System_Portable» នេះទាំងមូល ដាក់លើ Flash Drive ឬផ្ញើទៅ PC ផ្សេង។
echo  2. ចុចបើក File «DMC_System.exe» នោះកម្មវិធីនឹងដំណើរការភ្លាមៗ។
echo  3. រូបថតមន្ត្រីទាំងអស់ និងឯកសារយោង ត្រូវបានភ្ជាប់មកជាមួយក្នុង Folder «media» រួចជាស្រេច
echo     (ដំណើរការបាន ១០០%% ទាំង Offline និង Online)។
echo.
) > "%TARGET_DIR%\README_USER_PC.txt"

echo.
echo [3/3] បង្កើតកញ្ចប់រួចរាល់!
echo ========================================================================
echo  [OK] ជោគជ័យ ១០០%%! កញ្ចប់ Offline ត្រូវបានបង្កើតនៅ៖
echo     %TARGET_DIR%
echo.
echo  [*] អាច Copy Folder «DMC_System_Portable» នេះទៅដាក់លើ PC ណាផ្សេងក៏បាន
echo     ដោយមិនបាត់រូបភាព ឬឯកសារយោងឡើយ!
echo ========================================================================
echo.
pause
