@echo off
title DMS - Setup Windows Firewall for LAN / Wi-Fi Access
color 0a
cd /d "%~dp0"

echo ==============================================================================
echo   DOCUMENT MANAGEMENT SYSTEM (DMS) - FIREWALL SETUP FOR LAN / WI-FI
echo ==============================================================================
echo.
echo [INFO] កំពុងបើក Port 8000 លើ Windows Defender Firewall...
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ព្រមាន] សូម Right-Click លើឯកសារនេះ រួចជ្រើសរើស "Run as administrator"!
    echo [WARNING] Please run this file as Administrator to configure Windows Firewall.
    echo.
    pause
    exit /b 1
)

:: Remove any duplicate old rule if exists
netsh advfirewall firewall delete rule name="DMS_System_Port_8000" >nul 2>&1

:: Add Inbound TCP rule on Port 8000
netsh advfirewall firewall add rule name="DMS_System_Port_8000" dir=in action=allow protocol=TCP localport=8000 profile=any >nul 2>&1

if %errorlevel% equ 0 (
    echo ==============================================================================
    echo   [ជោគជ័យ] PORT 8000 ត្រូវបានបើកដំណើរការដោយជោគជ័យលើ WINDOWS FIREWALL!
    echo ==============================================================================
    echo.
    echo   ឥឡូវនេះ ទូរស័ព្ទដៃ, iPad និងកុំព្យូទ័រដទៃទៀតក្នុងបណ្តាញ Wi-Fi / LAN តែមួយ
    echo   អាចចូលប្រើប្រាស់ប្រព័ន្ធ DMS បានយ៉ាងរលូន ដោយគ្មានការរារាំងឡើយ។
    echo.
) else (
    echo [បរាជ័យ] មិនអាចកែប្រែ Firewall បានឡើយ។ សូមប្រាកដថាបាន Run as administrator។
)

echo ==============================================================================
pause
