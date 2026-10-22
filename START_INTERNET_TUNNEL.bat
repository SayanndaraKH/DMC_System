@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title DMC System - Cloudflare Internet Tunnel (Option 2)

python "%~dp0start_tunnel.py"
if errorlevel 1 (
    echo.
    echo ❌ [កំហុស] មានបញ្ហាក្នុងការដំណើរការ Tunnel សូមពិនិត្យមើលសារខាងលើ។
    pause
)
