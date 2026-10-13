@echo off
shutdown.exe /a 2>nul
if %errorlevel% equ 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('បានលុបចោលការកំណត់បិទកុំព្យូទ័ររួចរាល់! ម៉ាស៊ីននឹងមិន Shut Down ឡើយ។', 'DMS Auto-Shutdown', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('មិនមានការកំណត់ពេលបិទម៉ាស៊ីន (Shutdown Timer) ណាមួយឡើយ។', 'DMS Auto-Shutdown', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)"
)
