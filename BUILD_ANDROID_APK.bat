@echo off
if "%~1"=="--in-temp" goto :run_build
copy /y "%~f0" "%TEMP%\dmc_build_apk.bat" >nul 2>&1
"%TEMP%\dmc_build_apk.bat" --in-temp "%~dp0"
exit /b

:run_build
shift
set "APP_DIR=%~1"
if not defined APP_DIR set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"
title DMC System - Auto Build Android APK into dist/

set "PY_BIN="
if exist "%APP_DIR%venv\Scripts\python.exe" set "PY_BIN=%APP_DIR%venv\Scripts\python.exe"
if not defined PY_BIN if exist "C:\Program Files\Python312\python.exe" set "PY_BIN=C:\Program Files\Python312\python.exe"
if not defined PY_BIN if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY_BIN if exist "C:\Program Files\Python311\python.exe" set "PY_BIN=C:\Program Files\Python311\python.exe"
if not defined PY_BIN if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PY_BIN for /f "delims=" %%i in ('where python 2^>nul') do if not defined PY_BIN set "PY_BIN=%%i"
if not defined PY_BIN set "PY_BIN=python.exe"

"%PY_BIN%" "%APP_DIR%build_apk.py" --auto
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] An error occurred during APK build.
    pause
)
