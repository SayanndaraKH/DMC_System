@echo off
title DMC System - Desktop Control Center
cd /d "%~dp0"
set "PY_BIN="
if exist "%~dp0venv\Scripts\python.exe" set "PY_BIN=%~dp0venv\Scripts\python.exe"
if not defined PY_BIN if exist "C:\Program Files\Python312\python.exe" set "PY_BIN=C:\Program Files\Python312\python.exe"
if not defined PY_BIN if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY_BIN if exist "C:\Program Files\Python311\python.exe" set "PY_BIN=C:\Program Files\Python311\python.exe"
if not defined PY_BIN if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PY_BIN set "PY_BIN=python.exe"

"%PY_BIN%" "%~dp0main_app.py"
