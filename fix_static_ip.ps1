# DMS Static IP Setup Script (Run as Administrator)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  DMS SYSTEM - កំណត់ NETWORK IP ថេរ 192.168.1.51 (STATIC IP)" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[INFO] កំពុងស្នើសុំសិទ្ធិ Administrator... សូមចុច 'Yes' លើផ្ទាំង Windows UAC" -ForegroundColor Yellow
    try {
        Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
        exit
    } catch {
        Write-Host "[កំហុស] សូម Right-Click លើឯកសារ រួចជ្រើសរើស 'Run as administrator'!" -ForegroundColor Red
        Read-Host "ចុច Enter ដើម្បីចាកចេញ..."
        exit
    }
}

$interfaceName = "Ethernet"
$ip = "192.168.1.51"
$mask = "255.255.255.0"
$gateway = "192.168.1.1"

Write-Host "[1/4] កំពុងកំណត់ IP ថេរ $ip លើកាតបណ្តាញ $interfaceName..." -ForegroundColor Green
& netsh interface ip set address name="$interfaceName" static $ip $mask $gateway 1

Write-Host "[2/4] កំពុងកំណត់ DNS Server ($gateway, 8.8.8.8, 117.120.24.1)..." -ForegroundColor Green
& netsh interface ip set dns name="$interfaceName" static $gateway
& netsh interface ip add dns name="$interfaceName" 8.8.8.8 index=2
& netsh interface ip add dns name="$interfaceName" 117.120.24.1 index=3

Write-Host "[3/4] កំពុង Flush DNS Cache..." -ForegroundColor Green
& ipconfig /flushdns | Out-Null

Write-Host "[4/4] កំពុងធ្វើបច្ចុប្បន្នភាពឯកសារ IP.txt..." -ForegroundColor Green
$ipFile = Join-Path $PSScriptRoot "IP.txt"
if (Test-Path $ipFile) {
    $content = Get-Content $ipFile -Raw -Encoding UTF8
    $content = $content -replace "http://192\.168\.\d+\.\d+:8000/", "http://$ip`:8000/"
    Set-Content -Path $ipFile -Value $content -Encoding UTF8
}

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "  [ជោគជ័យ ១០០%] IP $ip ត្រូវបានកំណត់ជា IP ថេរ (Static IP) រួចរាល់!" -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  * DHCP ត្រូវបានបិទ (Disabled) - Router នឹងលែងអាចប្តូរលេខ IP នេះទៀតឡើយ!"
Write-Host "  * អាសយដ្ឋាន DMS សម្រាប់ទូរស័ព្ទ និង PC ដទៃ៖ http://$ip`:8000/"
Write-Host "  * ឬប្រើឈ្មោះកុំព្យូទ័រ៖ http://desktop-cil0etl.local:8000/"
Write-Host ""
Read-Host "សូមចុច Enter ដើម្បីបិទផ្ទាំងនេះ..."
