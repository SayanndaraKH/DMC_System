@echo off
chcp 65001 >nul
title DMC System - Push to GitHub (សម្រាប់ Admin / Server PC)
color 0b

echo ====================================================================
echo        DMC SYSTEM - បញ្ជូនទម្រង់ថ្មី និងកូដថ្មីទៅ GITHUB
echo ====================================================================
echo.

cd /d "%~dp0"

:: 1. Locate Git executable
set "GIT_CMD=git"
if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" (
    set "GIT_CMD=%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
) else if exist "C:\Program Files\Git\cmd\git.exe" (
    set "GIT_CMD=C:\Program Files\Git\cmd\git.exe"
) else if exist "C:\Program Files (x86)\Git\cmd\git.exe" (
    set "GIT_CMD=C:\Program Files (x86)\Git\cmd\git.exe"
)

echo [1/4] កំពុងពិនិត្យមើលស្ថានភាព File ដែលបានកែប្រែ (Git Status)...
"%GIT_CMD%" status -s
echo.

set commit_msg=
set /p commit_msg=វាយបញ្ចូលកំណត់សម្គាល់ការកែប្រែ (ចុច Enter សម្រាប់ Auto Timestamp): 
if "%commit_msg%"=="" (
    set commit_msg=Update DMC System: %date% %time%
)

echo.
echo [2/4] កំពុងបន្ថែម File ទាំងអស់ទៅ Git (git add -A)...
:: Ensure dist/DMC_System.exe is copied to root if available
if exist "dist\DMC_System.exe" (
    copy /Y "dist\DMC_System.exe" "DMC_System.exe" >nul 2>&1
)
"%GIT_CMD%" add -A

echo.
echo [3/4] កំពុង Commit ទម្រង់ថ្មី (git commit)...
"%GIT_CMD%" commit -m "%commit_msg%"

echo.
echo [4/4] កំពុងបញ្ជូនទៅ GitHub (git push origin main)...
"%GIT_CMD%" push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================================================
    echo  ✅ [ជោគជ័យ] ទម្រង់ថ្មី និងកូដថ្មី ត្រូវបានបញ្ជូនទៅ GitHub រួចរាល់!
    echo.
    echo  📌 នៅលើ User PC:
    echo     គ្រាន់តែចុចលើ "UPDATE_USER_PC.bat" (ឬចុចប៊ូតុង Auto Update)
    echo     នោះទម្រង់ថ្មី និង File ថ្មីនឹងត្រូវបានទាញយក និងជំនួសភ្លាមៗតែម្តង!
    echo ====================================================================
) else (
    echo.
    echo ====================================================================
    echo  ❌ [បរាជ័យ] មានបញ្ហាក្នុងការ Push ទៅកាន់ GitHub! សូមពិនិត្យមើលខាងលើ។
    echo ====================================================================
)

echo.
pause
