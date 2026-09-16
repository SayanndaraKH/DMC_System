@echo off
title DMS - Fix Windows Firewall (Port 8000 & mDNS)
color 0a
cd /d "%~dp0"

echo ==============================================================================
echo   DOCUMENT MANAGEMENT SYSTEM (DMS) - WINDOWS FIREWALL CONFIGURATION
echo ==============================================================================
echo.

:: 1. Check Administrator Privileges and auto-elevate if needed
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] កំពុងស្នើសុំសិទ្ធិ Administrator ដើម្បីកែសម្រួល Windows Firewall...
    echo [INFO] Requesting Administrator privileges...
    powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo [1/3] កំពុងបើក Port 8000 (TCP) លើ Windows Defender Firewall...
netsh advfirewall firewall delete rule name="DMS_HTTP_Port_8000" >nul 2>&1
netsh advfirewall firewall add rule name="DMS_HTTP_Port_8000" dir=in action=allow protocol=TCP localport=8000 profile=any description="Allow LAN/Wi-Fi devices to connect to DMS" >nul 2>&1

echo [2/3] កំពុងបើក mDNS Port 5353 (UDP) សម្រាប់ស្វែងរក Hostname ក្នុង Wi-Fi...
netsh advfirewall firewall delete rule name="DMS_mDNS_Port_5353" >nul 2>&1
netsh advfirewall firewall add rule name="DMS_mDNS_Port_5353" dir=in action=allow protocol=UDP localport=5353 profile=any description="Allow mDNS local service discovery for DMS" >nul 2>&1

echo [3/3] កំពុងអនុញ្ញាតចរាចរណ៍សម្រាប់ Python...
if exist "%~dp0venv\Scripts\python.exe" (
    netsh advfirewall firewall delete rule name="DMS_Python_Service" >nul 2>&1
    netsh advfirewall firewall add rule name="DMS_Python_Service" dir=in action=allow program="%~dp0venv\Scripts\python.exe" enable=yes profile=any >nul 2>&1
)

echo.
echo ==============================================================================
echo   [ជោគជ័យ] PORT 8000 (TCP) និង MDNS 5353 (UDP) ត្រូវបានបើកដំណើរការរួចរាល់!
echo   [SUCCESS] FIREWALL RULES APPLIED SUCCESSFULLY!
echo ==============================================================================
echo.
echo   - ឧបករណ៍ទាំងអស់ក្នុង Wi-Fi / LAN អាចចូលទៅកាន់: http://192.168.1.xxx:8000
echo   - បណ្តាញ mDNS គាំទ្រការស្វែងរក local network discovery ដោយស្វ័យប្រវត្តិ
echo.
echo ==============================================================================
pause
