@echo off
title Switch DMS to Neon Cloud PostgreSQL Database
color 0a

echo =======================================================================
echo     SWITCHING DMS SYSTEM TO NEON CLOUD DATABASE (PRIMARY MODE)
echo =======================================================================
echo.
echo  - Activating Neon Cloud PostgreSQL...
echo  - All 46 civil servants, 16 contract officers, and geography are live!
echo  - Your local db.sqlite3 remains safe and on standby.
echo.

cd /d "%~dp0"

powershell -NoProfile -Command "$c = Get-Content .env; if ($c -match 'USE_LOCAL_SQLITE=') { $c -replace 'USE_LOCAL_SQLITE=.*', 'USE_LOCAL_SQLITE=False' | Set-Content .env } else { Add-Content .env 'USE_LOCAL_SQLITE=False' }"

echo [1/2] Stopping active server...
call stop.bat >nul 2>&1

echo [2/2] Restarting server connected to Neon Cloud...
wscript.exe start_background.vbs

ping 127.0.0.1 -n 3 >nul 2>&1

echo.
echo =======================================================================
echo  [SUCCESS] DMS System is now connected directly to Neon Cloud Database!
echo  Open browser at: http://127.0.0.1:8000
echo =======================================================================
echo.
pause
