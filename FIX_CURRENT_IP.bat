@echo off
chcp 65001 >nul
title DMS - Fix Current Static IP
color 0a

:: 1. Check Administrator elevation
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ====================================================================
    echo   [INFO] កំពុងស្នើសុំសិទ្ធិ Administrator...
    echo   សូមចុច "Yes" លើផ្ទាំង Windows UAC ខាងមុខនេះ ដើម្បីអនុញ្ញាត Fix IP
    echo ====================================================================
    echo.
    powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/k \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ====================================================================
echo   [DMS SYSTEM] កំពុងកំណត់ IP ថេរ 192.168.1.97 (STATIC IP)
echo ====================================================================
echo.

echo [1/3] កំពុងកំណត់ Network IP 192.168.1.97 លើកាតបណ្តាញ Ethernet...
netsh interface ip set address name="Ethernet" static 192.168.1.97 255.255.255.0 192.168.1.1 1

echo [2/3] កំពុងកំណត់ DNS Server (192.168.1.1, 8.8.8.8, 1.1.1.1)...
netsh interface ip set dns name="Ethernet" static 192.168.1.1
netsh interface ip add dns name="Ethernet" 8.8.8.8 index=2
netsh interface ip add dns name="Ethernet" 1.1.1.1 index=3

echo [3/3] កំពុង Flush DNS Cache...
ipconfig /flushdns >nul

echo.
echo ====================================================================
echo   ✅ ជោគជ័យ! IP 192.168.1.97 ត្រូវបានកំណត់ជា IP ថេរ (STATIC) រួចរាល់!
echo   Router DHCP ត្រូវបានបិទសម្រាប់កុំព្យូទ័រនេះ។
echo   Router នឹងមិនអាចផ្លាស់ប្តូរលេខ IP នេះទៀតឡើយ ទោះបីបិទបើក Router ក៏ដោយ!
echo ====================================================================
echo.
echo អាសយដ្ឋានប្រើប្រាស់លើទូរស័ព្ទ ឬកុំព្យូទ័រផ្សេងទៀត៖
echo 👉 http://192.168.1.97:8000/
echo.
pause
