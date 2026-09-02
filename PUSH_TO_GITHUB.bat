@echo off
title DMC System - Push to GitHub
color 0b

echo ====================================================================
echo        DMC SYSTEM - AUTO PUSH TO GITHUB (RAILWAY AUTO-DEPLOY)
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

echo [1/4] Checking Git Status...
"%GIT_CMD%" status -s
echo.

set commit_msg=
set /p commit_msg=Enter commit message (Press Enter for auto timestamp): 
if "%commit_msg%"=="" (
    set commit_msg=Update DMC System: %date% %time%
)

echo.
echo [2/4] Adding all files to Git (git add .)...
"%GIT_CMD%" add .

echo.
echo [3/4] Committing changes (git commit)...
"%GIT_CMD%" commit -m "%commit_msg%"

echo.
echo [4/4] Pushing to GitHub (git push origin main)...
"%GIT_CMD%" push -u origin main

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
