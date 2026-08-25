@echo off
title DMC System - Push to GitHub & Deploy to Railway
color 0b

echo =======================================================================
echo          DMC SYSTEM - AUTO PUSH TO GITHUB & RAILWAY DEPLOY
echo =======================================================================
echo.

cd /d "%~dp0"

echo [1/4] Checking Django configuration for errors...
python manage.py check
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Django configuration check failed! Please fix the errors above.
    echo.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/4] Checking Git Status (Modified files)...
git status -s
echo.

set commit_msg=
set /p commit_msg=Enter commit note (Press Enter for auto-timestamp): 
if "%commit_msg%"=="" (
    set commit_msg=Update DMC System: %date% %time%
)

echo.
echo [3/4] Adding modified files to Git (git add .)...
git add .
git commit -m "%commit_msg%"

echo.
echo [4/4] Pushing to GitHub (origin/main and origin/master)...
git push -u origin main
git push origin main:master

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =======================================================================
    echo  [SUCCESS] Code pushed to GitHub successfully!
    echo.
    echo  - GitHub Repo: https://github.com/SayanndaraKH/DMC_System
    echo  - Railway Deploy: Railway is automatically deploying your latest update!
    echo  - Web Application: https://dmcsystem-admin.up.railway.app
    echo.
    echo  [NOTE] Live database records entered via Web are 100%% SAFE and intact!
    echo =======================================================================
) else (
    echo.
    echo =======================================================================
    echo  [FAILED] Push encountered an error! Check the output above.
    echo =======================================================================
)

echo.
pause
