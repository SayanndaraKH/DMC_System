@echo off
title Switch DMS to Local SQLite Database (Standby Re-activation)
color 0e

echo =======================================================================
echo    SWITCHING DMS SYSTEM TO LOCAL SQLITE DATABASE (STANDBY MODE)
echo =======================================================================
echo.
echo  - Activating local db.sqlite3...
echo  - Offline mode active (no internet connection required).
echo.

cd /d "%~dp0"

powershell -NoProfile -Command "$c = Get-Content .env; if ($c -match 'USE_LOCAL_SQLITE=') { $c -replace 'USE_LOCAL_SQLITE=.*', 'USE_LOCAL_SQLITE=True' | Set-Content .env } else { Add-Content .env 'USE_LOCAL_SQLITE=True' }"

echo [1/2] Stopping active server...
call stop.bat >nul 2>&1

echo [2/2] Restarting server connected to local db.sqlite3...
wscript.exe start_background.vbs

ping 127.0.0.1 -n 3 >nul 2>&1

echo.
echo =======================================================================
echo  [SUCCESS] DMS System is now connected to local db.sqlite3!
echo  Open browser at: http://127.0.0.1:8000
echo =======================================================================
echo.
pause
