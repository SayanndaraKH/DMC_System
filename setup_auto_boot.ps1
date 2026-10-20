# DMS Auto-Boot Setup Script (Run as Administrator)
# UTF-8 Output
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  DOCUMENT MANAGEMENT SYSTEM (DMS) - AUTO-BOOT SETUP" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# Check Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[INFO] កំពុងស្នើសុំសិទ្ធិ Administrator... សូមចុច Yes លើផ្ទាំង Windows UAC" -ForegroundColor Yellow
    try {
        Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
        exit
    } catch {
        Write-Host "[កំហុស] សូម Right-Click លើឯកសារ BAT រួចជ្រើសរើស 'Run as administrator'!" -ForegroundColor Red
        Read-Host "ចុច Enter ដើម្បីចាកចេញ..."
        exit
    }
}

$baseDir = $PSScriptRoot
$pyPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pyPath) {
    $pyPath = "C:\Program Files\Python311\python.exe"
}

Write-Host "[1/5] កំពុងសម្អាត Shortcut ចាស់ក្នុង Startup Folder..." -ForegroundColor Green
$userStartup = [Environment]::GetFolderPath('Startup')
$allStartup = [Environment]::GetFolderPath('CommonStartup')
Remove-Item -Path "$userStartup\DMS_AutoStart.lnk" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$allStartup\DMS_AutoStart.lnk" -Force -ErrorAction SilentlyContinue
Write-Host "  [OK] សម្អាតរួចរាល់។"

Write-Host "[2/5] កំពុងចុះឈ្មោះ Windows Scheduled Task (DMS_Boot_Server)..." -ForegroundColor Green
$runScript = Join-Path $baseDir 'run.py'
$action = New-ScheduledTaskAction -Execute $pyPath -Argument "`"$runScript`" --autostart" -WorkingDirectory $baseDir
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'NT AUTHORITY\SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -Priority 4

Unregister-ScheduledTask -TaskName 'DMS_Boot_Server' -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName 'DMS_Boot_Server' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Host "  [OK] បានបង្កើត Task Scheduler 'DMS_Boot_Server' រួចរាល់។"

Write-Host "[3/5] កំពុងបើក Port 8000 លើ Windows Defender Firewall..." -ForegroundColor Green
& netsh advfirewall firewall delete rule name="Django DMS Port 8000" | Out-Null
& netsh advfirewall firewall add rule name="Django DMS Port 8000" dir=in action=allow protocol=TCP localport=8000 profile=any | Out-Null
Write-Host "  [OK] បើក Port 8000 គ្រប់ Network Profile រួចរាល់។"

Write-Host "[4/5] កំពុងកំណត់ Network ជា Private..." -ForegroundColor Green
Set-NetConnectionProfile -InterfaceAlias 'Ethernet' -NetworkCategory Private -ErrorAction SilentlyContinue
Write-Host "  [OK] កំណត់ Network Category រួចរាល់។"

Write-Host "[5/5] កំពុងបង្កើត Shortcut លើ Desktop..." -ForegroundColor Green
$ws = New-Object -ComObject WScript.Shell
$desktopFolder = [Environment]::GetFolderPath('Desktop')
$shortcut = $ws.CreateShortcut("$desktopFolder\DMS System (Local Server).lnk")
$shortcut.TargetPath = 'http://127.0.0.1:8000/'
$shortcut.Description = 'បើកប្រព័ន្ធគ្រប់គ្រងឯកសារ និងព័ត៌មានមន្ត្រី (DMS)'
$shortcut.Save()
Write-Host "  [OK] បង្កើត Desktop Shortcut រួចរាល់។"

Write-Host ""
Write-Host "[INFO] កំពុង Start DMS Task Scheduler ភ្លាមៗ..." -ForegroundColor Cyan
Start-ScheduledTask -TaskName 'DMS_Boot_Server' -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "  [ជោគជ័យ ១០០%] AUTO-BOOT BEFORE LOGIN ត្រូវបានដំឡើងជោគជ័យ!" -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  1. ពេលនេះ Server ដំណើរការជា System Service តាំងពី System Boot។"
Write-Host "  2. បើក PC មកទោះមិនទាន់ Login ក៏ PC ផ្សេងៗប្រើបានភ្លាមៗ។"
Write-Host ""
Write-Host "សូមចុច Enter ដើម្បីបិទផ្ទាំងនេះ..."
Read-Host
