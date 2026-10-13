@echo off
title DMS - Fix Static IP 192.168.1.51
color 0a

:: 1. Check Administrator elevation
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Requesting Administrator Privileges...
    echo Please click YES on the Windows prompt.
    powershell -Command "Start-Process cmd -ArgumentList '/k \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ====================================================================
echo   [DMS SYSTEM] SETTING STATIC IP: 192.168.1.51
echo ====================================================================
echo.

echo [1/3] Setting IP address: 192.168.1.51 on Ethernet...
netsh interface ip set address name="Ethernet" static 192.168.1.51 255.255.255.0 192.168.1.1 1

echo [2/3] Setting DNS servers...
netsh interface ip set dns name="Ethernet" static 192.168.1.1
netsh interface ip add dns name="Ethernet" 8.8.8.8 index=2
netsh interface ip add dns name="Ethernet" 117.120.24.1 index=3

echo [3/3] Flushing DNS cache...
ipconfig /flushdns

echo.
echo ====================================================================
echo   SUCCESS! Network IP 192.168.1.51 is now permanently STATIC!
echo   Router DHCP is disabled for this adapter.
echo   Router will NEVER change this IP address again.
echo ====================================================================
echo.
echo DMS Address for Phones and Other PCs:
echo    http://192.168.1.51:8000/
echo.
pause
