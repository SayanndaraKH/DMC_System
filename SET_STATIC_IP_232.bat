@echo off
chcp 65001 >nul
title DMS - កំណត់ IP ថេរ 192.168.1.232 (Static IP)
color 0b

:: Check for Administrator elevation
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ====================================================================
    echo   [INFO] កំពុងស្នើសុំសិទ្ធិ Administrator ដើម្បីកំណត់ IP ថេរ...
    echo ====================================================================
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo.
echo ====================================================================
echo   [DMS SYSTEM] កំពុងកំណត់ Network IP ថេរ 192.168.1.232 លើ Ethernet...
echo ====================================================================
echo.

netsh interface ip set address name="Ethernet" static 192.168.1.232 255.255.255.0 192.168.1.1 1
netsh interface ip set dns name="Ethernet" static 8.8.8.8
netsh interface ip add dns name="Ethernet" 8.8.4.4 index=2

echo [ជោគជ័យ] កុំព្យូទ័រនេះត្រូវបានកំណត់ IP ថេរ 192.168.1.232 រួចរាល់ហើយ!
echo Router នឹងមិនអាចផ្លាស់ប្តូរលេខ IP នេះទៀតឡើយ។
echo.
pause
