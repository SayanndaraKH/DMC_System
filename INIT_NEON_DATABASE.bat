@echo off
title DMC System - Initialize Neon PostgreSQL Database
color 0b

echo =======================================================================
echo         DMC SYSTEM - INITIALIZE NEON CLOUD DATABASE
echo =======================================================================
echo.
echo  This tool runs database migrations, initializes departments, and
echo  loads Cambodia administrative geography directly into your Neon DB.
echo.

cd /d "%~dp0"

:: Check if DATABASE_URL is already defined in environment or .env
set "NEON_URL=%DATABASE_URL%"
if "%NEON_URL%"=="" (
    echo Please copy the Connection String from your Neon Console.
    echo Example: postgresql://neondb_owner:npg_xxx@ep-xyz-pooler.region.aws.neon.tech/neondb?sslmode=require
    echo.
    set /p NEON_URL="Enter your Neon DATABASE_URL: "
)

if "%NEON_URL%"=="" (
    echo.
    echo [ERROR] No DATABASE_URL entered. Operation cancelled.
    pause
    exit /b 1
)

set "DATABASE_URL=%NEON_URL%"

:: Locate Python
set "PY_BIN=python"
if exist "C:\Program Files\Python311\python.exe" (
    set "PY_BIN=C:\Program Files\Python311\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
)

echo.
echo [1/3] Running migrations on Neon Database...
"%PY_BIN%" manage.py migrate --noinput
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Migration failed. Please check your Neon DATABASE_URL.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Loading Cambodia administrative geography into Neon...
"%PY_BIN%" manage.py load_geo

echo.
echo [3/3] Initializing default Admin account and core departments...
"%PY_BIN%" manage.py init_admin

echo.
echo =======================================================================
echo  [SUCCESS] Neon Cloud Database is 100%% initialized and ready!
echo.
echo  Default Superuser:
echo    Username: ADMIN
echo    Password: syd@168
echo.
echo  Next step: In Netlify Dashboard (https://app.netlify.com):
echo    Site configuration -> Environment variables -> Add DATABASE_URL
echo =======================================================================
echo.
pause
