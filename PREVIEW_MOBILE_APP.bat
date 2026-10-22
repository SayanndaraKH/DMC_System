@echo off
chcp 65001 >nul
title 📱 DMC System - ឧបករណ៍មើលសាកល្បងលើទូរស័ព្ទដៃ (Mobile Preview Simulator)

echo ====================================================================
echo   📱 ប្រព័ន្ធគ្រប់គ្រងធនធានមនុស្ស (DMC System)
echo   ឧបករណ៍មើលសាកល្បងទិដ្ឋភាពលើទូរស័ព្ទដៃ (Mobile Simulator)
echo ====================================================================
echo.
echo កំពុងបើកផ្ទាំងទូរស័ព្ទសាកល្បង (Mobile Preview)...
echo អាសយដ្ឋាន៖ http://127.0.0.1:8000/mobile-preview/

start "" "http://127.0.0.1:8000/mobile-preview/"

echo.
echo ✅ បានបើកដោយជោគជ័យ! អ្នកអាចមើលសាកល្បង បង្វិលអេក្រង់ និងស្កេន QR Code បានភ្លាមៗ។
echo.
timeout /t 3 >nul
exit
