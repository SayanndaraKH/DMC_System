# Interactive Static IP Menu Script for DMS
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 1. Check Administrator Elevation
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[INFO] កំពុងស្នើសុំសិទ្ធិ Administrator... សូមចុច 'Yes' លើផ្ទាំង Windows UAC" -ForegroundColor Yellow
    try {
        Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
        exit
    } catch {
        Write-Host "[កំហុស] សូម Right-Click រួចយក 'Run as administrator'!" -ForegroundColor Red
        Read-Host "ចុច Enter ដើម្បីចាកចេញ..."
        exit
    }
}

# 2. Detect Active Adapter and Current IP
$activeAdapter = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.InterfaceDescription -notlike '*Virtual*' -and $_.InterfaceDescription -notlike '*VPN*' } | Select-Object -First 1
if (-not $activeAdapter) {
    $activeAdapter = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -First 1
}
$interfaceName = if ($activeAdapter) { $activeAdapter.Name } else { "Ethernet" }

$netConfig = Get-NetIPConfiguration -InterfaceAlias $interfaceName -ErrorAction SilentlyContinue
$currentIP = if ($netConfig.IPv4Address) { $netConfig.IPv4Address.IPAddress } else { "192.168.1.97" }
$gateway = if ($netConfig.IPv4DefaultGateway) { $netConfig.IPv4DefaultGateway.NextHop } else { "192.168.1.1" }
$mask = "255.255.255.0"

function Apply-StaticIP($targetIP) {
    Clear-Host
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host "  [DMS SYSTEM] កំពុងកំណត់ IP ថេរ $targetIP លើ Network Adapter '$interfaceName'..." -ForegroundColor Cyan
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host ""

    Write-Host "[+] កំពុងកំណត់ IP: $targetIP, Subnet: $mask, Gateway: $gateway..." -ForegroundColor Green
    & netsh interface ip set address name="$interfaceName" static $targetIP $mask $gateway 1

    Write-Host "[+] កំពុងកំណត់ DNS Server ($gateway, 8.8.8.8, 1.1.1.1)..." -ForegroundColor Green
    & netsh interface ip set dns name="$interfaceName" static $gateway
    & netsh interface ip add dns name="$interfaceName" 8.8.8.8 index=2
    & netsh interface ip add dns name="$interfaceName" 1.1.1.1 index=3

    Write-Host "[+] កំពុង Flush DNS Cache..." -ForegroundColor Green
    & ipconfig /flushdns | Out-Null

    $ipFile = "c:\Users\sydfi\Desktop\DCM_System\IP.txt"
    if (Test-Path $ipFile) {
        $content = Get-Content $ipFile -Raw -Encoding UTF8
        $content = $content -replace "http://192\.168\.\d+\.\d+:8000/", "http://$targetIP`:8000/"
        Set-Content -Path $ipFile -Value $content -Encoding UTF8
    }

    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Green
    Write-Host "  [ជោគជ័យ] កុំព្យូទ័រនេះត្រូវបានកំណត់ IP ថេរ $targetIP រួចរាល់ហើយ!" -ForegroundColor Green
    Write-Host "==============================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  ពេលនេះ Router នឹងមិនអាចផ្លាស់ប្តូរលេខ IP នេះទៀតឡើយ!"
    Write-Host "  អាសយដ្ឋាន DMS សម្រាប់បើកលើទូរស័ព្ទ ឬ PC ដទៃ៖ http://$targetIP`:8000/"
    Write-Host ""
    Read-Host "សូមចុច Enter ដើម្បីបិទ..."
}

function Set-Dhcp {
    Clear-Host
    Write-Host "==============================================================================" -ForegroundColor Yellow
    Write-Host "  [DMS SYSTEM] កំពុងកំណត់ $interfaceName ទៅជា DHCP វិញ..." -ForegroundColor Yellow
    Write-Host "==============================================================================" -ForegroundColor Yellow
    Write-Host ""
    & netsh interface ip set address name="$interfaceName" source=dhcp
    & netsh interface ip set dns name="$interfaceName" source=dhcp
    & ipconfig /renew "$interfaceName" | Out-Null
    Write-Host "[ជោគជ័យ] បានកំណត់ទៅជា DHCP ស្វ័យប្រវត្តវិញរួចរាល់ហើយ!" -ForegroundColor Green
    Write-Host ""
    Read-Host "សូមចុច Enter ដើម្បីបិទ..."
}

function Show-Menu {
    Clear-Host
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host "      ប្រព័ន្ធគ្រប់គ្រងឯកសារ DMS - កំណត់ NETWORK IP ថេរ (STATIC IP)" -ForegroundColor Cyan
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [ព័ត៌មានបច្ចុប្បន្ន]" -ForegroundColor White
    Write-Host "  - Network Card: $interfaceName"
    Write-Host "  - IP បច្ចុប្បន្ន: $currentIP" -ForegroundColor Yellow
    Write-Host "  - Gateway:      $gateway"
    Write-Host ""
    Write-Host "  មូលហេតុដែល IP តែងតែប្តូរ៖" -ForegroundColor Yellow
    Write-Host "  ដោយសារកាតបណ្តាញ ($interfaceName) កំពុងកំណត់ជា DHCP (Router ជាអ្នកចែក IP តាមចិត្ត)។"
    Write-Host "  នៅពេលបិទបើកកុំព្យូទ័រ ឬ Router វានឹងដូរលេខ IP ថ្មីរហូត។"
    Write-Host ""
    Write-Host "------------------------------------------------------------------------------"
    Write-Host "  សូមជ្រើសរើសជម្រើសខាងក្រោម ដើម្បី Fix កុំឱ្យ IP ប្តូរទៀត៖" -ForegroundColor Green
    Write-Host "------------------------------------------------------------------------------"
    Write-Host ""
    Write-Host "  [1] កំណត់ IP បច្ចុប្បន្ន '$currentIP' ជា IP ថេរ (ណែនាំខ្លាំងបំផុត - មិនបាច់ដូរ Link ក្នុងទូរស័ព្ទ)" -ForegroundColor Green
    Write-Host "  [2] កំណត់ IP ខ្ពស់ '192.168.1.200' ជា IP ថេរ (ការពារកុំឱ្យជាន់គ្នាជាមួយទូរស័ព្ទដទៃ)" -ForegroundColor White
    Write-Host "  [3] បញ្ចូលលេខ IP ថេរផ្សេងតាមចិត្ត (Custom IP)" -ForegroundColor White
    Write-Host "  [4] កំណត់ត្រឡប់ទៅជា DHCP វិញ (ឱ្យ Router ចែកតាមស្វ័យប្រវត្តដូចដើម)" -ForegroundColor Gray
    Write-Host "  [5] ចាកចេញ (Exit)" -ForegroundColor Gray
    Write-Host ""
}

Show-Menu
$choice = Read-Host "សូមជ្រើសរើសលេខ (1, 2, 3, 4, ឬ 5)"

switch ($choice) {
    "1" { Apply-StaticIP $currentIP }
    "2" { Apply-StaticIP "192.168.1.200" }
    "3" {
        $custom = Read-Host "សូមវាយបញ្ចូលលេខ IP (ឧ. 192.168.1.97)"
        if ($custom -match '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$') {
            Apply-StaticIP $custom
        } else {
            Write-Host "ទម្រង់ IP មិនត្រឹមត្រូវ!" -ForegroundColor Red
            Read-Host "ចុច Enter ដើម្បីចាកចេញ..."
        }
    }
    "4" { Set-Dhcp }
    default { exit }
}
