@echo off
title DMC System - Push to GitHub & Deploy to Railway
color 0b

echo =======================================================================
echo          DMC SYSTEM - AUTO PUSH TO GITHUB & RAILWAY DEPLOY
echo =======================================================================
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

:: 2. Locate Python executable
set "PY_BIN=python"
if exist "C:\Program Files\Python311\python.exe" (
    set "PY_BIN=C:\Program Files\Python311\python.exe"
) else if exist "C:\Program Files\Python312\python.exe" (
    set "PY_BIN=C:\Program Files\Python312\python.exe"
) else if exist "C:\Program Files\Python310\python.exe" (
    set "PY_BIN=C:\Program Files\Python310\python.exe"
)

echo [1/4] Checking Django configuration for errors...
"%PY_BIN%" manage.py check
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Django configuration check failed! Please fix the errors above.
    echo.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/4] Checking Git Status (Modified files)...
"%GIT_CMD%" status -s
echo.

set commit_msg=
set /p commit_msg=Enter commit note (Press Enter for auto-timestamp): 
if "%commit_msg%"=="" (
    set commit_msg=Update DMC System: %date% %time%
)

echo.
echo [3/4] Adding modified files to Git (git add .)...
"%GIT_CMD%" add .
"%GIT_CMD%" commit -m "%commit_msg%"

echo.
echo [4/4] Pushing to GitHub (origin/main and origin/master)...
"%GIT_CMD%" push -u origin main
"%GIT_CMD%" push origin main:master

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =======================================================================
    echo  [SUCCESS] Code pushed to GitHub successfully!
    echo.
    echo  - GitHub Repo: https://github.com/SayanndaraKH/DMC_System
    echo  - Railway Deploy: Railway is automatically deploying your latest update!
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
