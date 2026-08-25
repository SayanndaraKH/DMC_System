@echo off
title DMC System - Push to GitHub
color 0b

echo ====================================================================
echo        DMC SYSTEM - AUTO PUSH TO GITHUB (RAILWAY AUTO-DEPLOY)
echo ====================================================================
echo.

cd /d "%~dp0"

echo [1/4] Checking Git Status...
git status -s
echo.

set commit_msg=
set /p commit_msg=Enter commit message (Press Enter for auto timestamp): 
if "%commit_msg%"=="" (
    set commit_msg=Update DMC System: %date% %time%
)

echo.
echo [2/4] Adding all files to Git (git add .)...
git add .

echo.
echo [3/4] Committing changes (git commit)...
git commit -m "%commit_msg%"

echo.
echo [4/4] Pushing to GitHub (git push origin main)...
git push -u origin main --force

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================================================
    echo  [SUCCESS] Code pushed to GitHub successfully!
    echo  Railway.com will auto-deploy the full project now.
    echo ====================================================================
) else (
    echo.
    echo ====================================================================
    echo  [FAILED] Push encountered an error! Check the output above.
    echo ====================================================================
)

echo.
pause
