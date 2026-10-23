@echo off
cd /d "%~dp0"
title DMC System - Cloudflare Internet Tunnel

set "PY_BIN="
if exist "%~dp0venv\Scripts\python.exe" set "PY_BIN=%~dp0venv\Scripts\python.exe"
if not defined PY_BIN if exist "C:\Program Files\Python312\python.exe" set "PY_BIN=C:\Program Files\Python312\python.exe"
if not defined PY_BIN if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY_BIN if exist "C:\Program Files\Python311\python.exe" set "PY_BIN=C:\Program Files\Python311\python.exe"
if not defined PY_BIN if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PY_BIN for /f "delims=" %%i in ('where python 2^>nul') do if not defined PY_BIN set "PY_BIN=%%i"
if not defined PY_BIN set "PY_BIN=python.exe"

"%PY_BIN%" "%~dp0start_tunnel.py"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start Internet Tunnel.
    pause
)
