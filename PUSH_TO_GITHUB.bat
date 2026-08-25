@echo off
chcp 65001 >nul
title DMC System - Push to GitHub
color 0b

echo ====================================================================
echo        DMC SYSTEM - AUTO PUSH TO GITHUB (RAILWAY AUTO-DEPLOY)
echo ====================================================================
echo.

cd /d "%~dp0"

echo [1/4] ពិនិត្យមើលស្ថានភាព File ដែលបានកែប្រែ (Checking Git Status)...
git status -s
echo.

set /p commit_msg=">> បញ្ចូលចំណាំនៃការកែប្រែ (Commit message) [ចុច Enter យក Default]: "
if "%commit_msg%"=="" (
    set commit_msg=Update DMC System: %date% %time%
)

echo.
echo [2/4] កំពុងរៀបចំឯកសារ (Git Add)...
git add .

echo.
echo [3/4] កំពុងរក្សាទុកការកែប្រែ (Git Commit: "%commit_msg%")...
git commit -m "%commit_msg%"

echo.
echo [4/4] កំពុង Push ឡើងទៅកាន់ GitHub (Git Push origin main)...
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================================================
    echo  [ជោគជ័យ] បាន Push ឡើង GitHub រួចរាល់ដោយជោគជ័យ!
    echo  Railway.com នឹងចាប់ផ្តើម Auto-Deploy កំណែថ្មីនេះដោយស្វ័យប្រវត្តិ។
    echo ====================================================================
) else (
    echo.
    echo ====================================================================
    echo  [បរាជ័យ] មានបញ្ហាក្នុងការ Push! សូមពិនិត្យមើល Error ខាងលើ។
    echo ====================================================================
)

echo.
pause
