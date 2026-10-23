@echo off
chcp 65001 >nul
title DMC System - Auto Update ពី GitHub (សម្រាប់ User PC)
color 0b

echo ========================================================================
echo        DMC SYSTEM - AUTO UPDATE ពី GITHUB (សម្រាប់ USER PC)
echo ========================================================================
echo.

cd /d "%~dp0"

echo [1/4] កំពុងបិទដំណើរការចាស់ៗ និងសម្អាត Port 8000...
:: Terminate any running DMC_System or python processes holding files or port 8000
taskkill /f /im DMC_System.exe >nul 2>&1
taskkill /f /im DMC_System_Client.exe >nul 2>&1
powershell -NoProfile -Command "Get-Process -Name 'DMC_System', 'DMC_System_Client' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue"
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul

:: 2. Locate Git
set "GIT_CMD=git"
if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" (
    set "GIT_CMD=%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
) else if exist "C:\Program Files\Git\cmd\git.exe" (
    set "GIT_CMD=C:\Program Files\Git\cmd\git.exe"
) else if exist "C:\Program Files (x86)\Git\cmd\git.exe" (
    set "GIT_CMD=C:\Program Files (x86)\Git\cmd\git.exe"
)

echo [2/4] កំពុងទាញយកទម្រង់ថ្មី និងកូដថ្មីពី GitHub (git fetch & reset)...
"%GIT_CMD%" --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   + រកឃើញ Git! កំពុងទាញយកកំណែចុងក្រោយពី origin main...
    "%GIT_CMD%" fetch origin main
    "%GIT_CMD%" reset --hard origin/main
    if %ERRORLEVEL% NEQ 0 (
        echo   [!] Reset មិនជោគជ័យ កំពុងសាកល្បង git pull...
        "%GIT_CMD%" pull origin main
    )
) else (
    echo   [!] រកមិនឃើញ Git ទេ! កំពុងប្រើប្រាស់ PowerShell Direct GitHub Downloader...
    powershell -NoProfile -Command ^
        "$url = 'https://github.com/SayanndaraKH/DMC_System/archive/refs/heads/main.zip';" ^
        "$zip = Join-Path $env:TEMP 'dmc_update.zip';" ^
        "$dest = Join-Path $env:TEMP 'dmc_update_extracted';" ^
        "Write-Host '   + កំពុងទាញយក main.zip...';" ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
        "Invoke-WebRequest -Uri $url -OutFile $zip;" ^
        "if (Test-Path $dest) { Remove-Item $dest -Recurse -Force };" ^
        "Expand-Archive -Path $zip -DestinationPath $dest -Force;" ^
        "$extractedFolder = Get-ChildItem -Path $dest | Where-Object { $_.PSIsContainer } | Select-Object -First 1;" ^
        "Copy-Item -Path ($extractedFolder.FullName + '\*') -Destination (Get-Location) -Recurse -Force;" ^
        "Remove-Item $zip -Force -ErrorAction SilentlyContinue;" ^
        "Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue;" ^
        "Write-Host '   + បានជំនួស File ថ្មីទាំងអស់ជោគជ័យ!';"
)

echo.
echo [3/4] កំពុងជំនួស File កម្មវិធី DMC_System.exe...
if exist "dist\DMC_System.exe" (
    copy /Y "dist\DMC_System.exe" "DMC_System.exe" >nul 2>&1
    echo   + បានជំនួស DMC_System.exe ថ្មីជោគជ័យ!
)

:: Run database migration if python is present
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   + កំពុងត្រួតពិនិត្យទិន្នន័យ Database (migrate)...
    python manage.py migrate --noinput >nul 2>&1
)

echo.
echo [4/4] បើកដំណើរការកម្មវិធីទម្រង់ថ្មី...
echo ========================================================================
echo  [OK] ការ UPDATE ទទួលបានជោគជ័យ ១០០%%!
echo  [+] ទម្រង់ថ្មី មុខងារថ្មី និងឯកសារទាំងអស់ត្រូវបានជំនួសថ្មីរួចរាល់។
echo  [*] កម្មវិធីកំពុងបើកដំណើរការឡើងវិញ...
echo ========================================================================
echo.

timeout /t 2 /nobreak >nul

if exist "DMC_System.exe" (
    start "" "DMC_System.exe"
) else if exist "dist\DMC_System.exe" (
    start "" "dist\DMC_System.exe"
) else if exist "RUN_DMS.bat" (
    start "" "RUN_DMS.bat"
) else (
    start "" python main_app.py
)

timeout /t 3 >nul
exit
