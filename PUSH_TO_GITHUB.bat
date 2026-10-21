@echo off
chcp 65001 >nul
title DMC System - Push to GitHub (ស្វ័យប្រវត្តិ)
color 0b

cd /d "%~dp0"

:: 1. Search for Python
set "PY_BIN="
if exist "%~dp0venv\Scripts\python.exe" set "PY_BIN=%~dp0venv\Scripts\python.exe"
if not defined PY_BIN if exist "C:\Program Files\Python311\python.exe" set "PY_BIN=C:\Program Files\Python311\python.exe"
if not defined PY_BIN if exist "C:\Program Files\Python312\python.exe" set "PY_BIN=C:\Program Files\Python312\python.exe"
if not defined PY_BIN if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PY_BIN for /f "delims=" %%i in ('where python 2^>nul') do if not defined PY_BIN set "PY_BIN=%%i"

:: 2. If Python is available, execute push_to_github.py (Unicode & Shell Safe)
if defined PY_BIN (
    "%PY_BIN%" "%~dp0push_to_github.py" %*
    goto :end
)

:: 3. Fallback to direct Git commands if Python is not installed
set "GIT_CMD=git"
if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" set "GIT_CMD=%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
if exist "C:\Program Files\Git\cmd\git.exe" set "GIT_CMD=C:\Program Files\Git\cmd\git.exe"

echo ====================================================================
echo        DMC SYSTEM - បញ្ជូនទម្រង់ថ្មី និងកូដថ្មីទៅ GITHUB (ស្វ័យប្រវត្តិ)
echo ====================================================================
echo.

if exist "dist\DMC_System.exe" copy /Y "dist\DMC_System.exe" "DMC_System.exe" >nul 2>&1

echo [1/3] កំពុងបន្ថែម File ទាំងអស់ (git add)...
"%GIT_CMD%" add -A

echo [2/3] កំពុង Commit ទិន្នន័យថ្មីដោយស្វ័យប្រវត្ត...
"%GIT_CMD%" commit -m "Auto Update DMC System: %DATE% %TIME%"

echo [3/3] កំពុងបញ្ជូនទៅកាន់ GitHub (git push)...
"%GIT_CMD%" push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================================================
    echo  ✅ [ជោគជ័យ ១០០%%] ទម្រង់ថ្មី និងកូដថ្មី ត្រូវបានបញ្ជូនទៅ GitHub រួចរាល់!
    echo ====================================================================
) else (
    echo.
    echo ====================================================================
    echo  ❌ [បរាជ័យ] មានបញ្ហាក្នុងការ Push ទៅកាន់ GitHub!
    echo ====================================================================
)

pause

:end
