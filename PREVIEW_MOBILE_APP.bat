@echo off
title DMC Mobile Preview Simulator
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$r = $false; " ^
    "try { $res = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/' -UseBasicParsing -TimeoutSec 1; if ($res.StatusCode -in 200,302) { $r = $true } } catch { if ($_.Exception.Response.StatusCode -in 200,302) { $r = $true } } " ^
    "if (-not $r) { " ^
    "    Write-Host '[INFO] DMS Server is not running. Starting server in background...' -ForegroundColor Yellow; " ^
    "    Start-Process 'wscript.exe' -ArgumentList '\"%~dp0start_background.vbs\"'; " ^
    "    $w = 0; while ($w -lt 45) { " ^
    "        try { $chk = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/' -UseBasicParsing -TimeoutSec 1; if ($chk.StatusCode -in 200,302) { $r = $true; break } } catch { if ($_.Exception.Response.StatusCode -in 200,302) { $r = $true; break } } " ^
    "        Start-Sleep -Milliseconds 600; $w++; " ^
    "    } " ^
    "} " ^
    "Write-Host '[OK] DMS Server is online! Opening Mobile Preview...' -ForegroundColor Green; " ^
    "Start-Process 'http://127.0.0.1:8000/mobile-preview/'"

exit
