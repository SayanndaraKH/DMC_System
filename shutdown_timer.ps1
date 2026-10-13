# DMS Auto-Shutdown Timer with Modern Khmer UI
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

[System.Windows.Forms.Application]::EnableVisualStyles()

$form = New-Object System.Windows.Forms.Form
$form.Text = "DMS - កំណត់ពេលបិទកុំព្យូទ័រ (Auto-Shutdown Timer)"
$form.Size = New-Object System.Drawing.Size(480, 480)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(248, 250, 252)

# Khmer Font fallback
$khmerFont = New-Object System.Drawing.Font("Khmer OS Battambang", 9.5, [System.Drawing.FontStyle]::Regular)
$titleFont = New-Object System.Drawing.Font("Khmer OS Battambang", 11, [System.Drawing.FontStyle]::Bold)
$boldFont = New-Object System.Drawing.Font("Khmer OS Battambang", 9.5, [System.Drawing.FontStyle]::Bold)
$smallFont = New-Object System.Drawing.Font("Khmer OS Battambang", 8.5, [System.Drawing.FontStyle]::Regular)

# Header Banner
$header = New-Object System.Windows.Forms.Panel
$header.Size = New-Object System.Drawing.Size(480, 75)
$header.Location = New-Object System.Drawing.Point(0, 0)
$header.BackColor = [System.Drawing.Color]::FromArgb(30, 58, 138)
$form.Controls.Add($header)

$headerTitle = New-Object System.Windows.Forms.Label
$headerTitle.Text = "⏱️ កំណត់ពេលបិទកុំព្យូទ័រដោយស្វ័យប្រវត្តិ"
$headerTitle.Font = $titleFont
$headerTitle.ForeColor = [System.Drawing.Color]::White
$headerTitle.Location = New-Object System.Drawing.Point(20, 12)
$headerTitle.Size = New-Object System.Drawing.Size(440, 28)
$header.Controls.Add($headerTitle)

$headerDesc = New-Object System.Windows.Forms.Label
$headerDesc.Text = "User ផ្សេងទៀតនៅតែអាចប្រើ DMS បាន រហូតដល់ម៉ោងកំណត់"
$headerDesc.Font = $smallFont
$headerDesc.ForeColor = [System.Drawing.Color]::FromArgb(191, 219, 254)
$headerDesc.Location = New-Object System.Drawing.Point(22, 42)
$headerDesc.Size = New-Object System.Drawing.Size(440, 22)
$header.Controls.Add($headerDesc)

# Status Label
$statusLbl = New-Object System.Windows.Forms.Label
$statusLbl.Text = "សូមជ្រើសរើសរយៈពេលដែលចង់ឱ្យកុំព្យូទ័រដំណើរការមុនពេល Shut Down៖"
$statusLbl.Font = $khmerFont
$statusLbl.ForeColor = [System.Drawing.Color]::FromArgb(51, 65, 85)
$statusLbl.Location = New-Object System.Drawing.Point(24, 88)
$statusLbl.Size = New-Object System.Drawing.Size(430, 24)
$form.Controls.Add($statusLbl)

# Function to schedule shutdown
function Set-ShutdownTimer([int]$minutes, [string]$label) {
    $seconds = $minutes * 60
    # Abort any prior timer first
    & shutdown.exe /a 2>$null
    
    $targetTime = (Get-Date).AddMinutes($minutes).ToString("hh:mm tt (dd/MM/yyyy)")
    & shutdown.exe /s /t $seconds /c "DMS Server Auto-Shutdown Timer: ម៉ាស៊ីននឹងបិទនៅវេលាម៉ោង $targetTime"
    
    $msg = "✅ បានកំណត់ដោយជោគជ័យ!`n`n" +
           "• រយៈពេលដំណើរការ៖ $label ($minutes នាទី)`n" +
           "• កុំព្យូទ័រនឹង Shut Down នៅម៉ោង៖ $targetTime`n`n" +
           "💡 ឥឡូវនេះលោកអ្នកអាចចុច [Windows + L] ដើម្បីចាក់សោអេក្រង់ដើរចេញបានដោយសុវត្ថិភាព។"
           
    [System.Windows.Forms.MessageBox]::Show($msg, "DMS Auto-Shutdown", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
    $form.Close()
}

# Function to cancel shutdown
function Cancel-ShutdownTimer {
    $res = & shutdown.exe /a 2>&1
    if ($LASTEXITCODE -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("✅ បានលុបចោលការកំណត់បិទកុំព្យូទ័ររួចរាល់! ម៉ាស៊ីននឹងមិនបិទឡើយ។", "DMS Auto-Shutdown", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
    } else {
        [System.Windows.Forms.MessageBox]::Show("ℹ️ មិនមានការកំណត់ពេលបិទម៉ាស៊ីន (Shutdown Timer) ណាមួយកំពុងដំណើរការឡើយ។", "DMS Auto-Shutdown", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
    }
}

# Helper to create styled buttons
function Create-PresetButton([string]$text, [int]$minutes, [int]$x, [int]$y, [int]$w, [int]$h, [bool]$isRecommended=$false) {
    $btn = New-Object System.Windows.Forms.Button
    $btn.Text = $text
    $btn.Font = if ($isRecommended) { $boldFont } else { $khmerFont }
    $btn.Size = New-Object System.Drawing.Size($w, $h)
    $btn.Location = New-Object System.Drawing.Point($x, $y)
    $btn.FlatStyle = "Flat"
    $btn.FlatAppearance.BorderSize = 1
    if ($isRecommended) {
        $btn.BackColor = [System.Drawing.Color]::FromArgb(219, 234, 254)
        $btn.ForeColor = [System.Drawing.Color]::FromArgb(30, 64, 175)
        $btn.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(59, 130, 246)
    } else {
        $btn.BackColor = [System.Drawing.Color]::White
        $btn.ForeColor = [System.Drawing.Color]::FromArgb(30, 41, 59)
        $btn.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(203, 213, 225)
    }
    $btn.Cursor = [System.Windows.Forms.Cursors]::Hand
    $btn.Add_Click({ Set-ShutdownTimer -minutes $minutes -label $text })
    $form.Controls.Add($btn)
    return $btn
}

# 2 Columns of Presets
Create-PresetButton -text "⏱️ ៣០ នាទី (30 Mins)" -minutes 30 -x 25 -y 120 -w 200 -h 42
Create-PresetButton -text "⏱️ ១ ម៉ោង (1 Hour)" -minutes 60 -x 240 -y 120 -w 200 -h 42

Create-PresetButton -text "⏱️ ២ ម៉ោង (ណែនាំ ⭐)" -minutes 120 -x 25 -y 172 -w 200 -h 42 -isRecommended $true
Create-PresetButton -text "⏱️ ៣ ម៉ោង (3 Hours)" -minutes 180 -x 240 -y 172 -w 200 -h 42

Create-PresetButton -text "⏱️ ៤ ម៉ោង (4 Hours)" -minutes 240 -x 25 -y 224 -w 200 -h 42
Create-PresetButton -text "⏱️ ៦ ម៉ោង (6 Hours)" -minutes 360 -x 240 -y 224 -w 200 -h 42

# Custom Minutes Section
$customGroup = New-Object System.Windows.Forms.GroupBox
$customGroup.Text = " កំណត់ចំនួននាទីដោយខ្លួនឯង (Custom) "
$customGroup.Font = $khmerFont
$customGroup.Location = New-Object System.Drawing.Point(25, 280)
$customGroup.Size = New-Object System.Drawing.Size(415, 68)
$form.Controls.Add($customGroup)

$customInput = New-Object System.Windows.Forms.NumericUpDown
$customInput.Minimum = 1
$customInput.Maximum = 1440
$customInput.Value = 90
$customInput.Font = New-Object System.Drawing.Font("Segoe UI", 10.5)
$customInput.Location = New-Object System.Drawing.Point(15, 26)
$customInput.Size = New-Object System.Drawing.Size(90, 30)
$customGroup.Controls.Add($customInput)

$customUnitLbl = New-Object System.Windows.Forms.Label
$customUnitLbl.Text = "នាទី"
$customUnitLbl.Font = $khmerFont
$customUnitLbl.Location = New-Object System.Drawing.Point(110, 28)
$customUnitLbl.Size = New-Object System.Drawing.Size(40, 24)
$customGroup.Controls.Add($customUnitLbl)

$customBtn = New-Object System.Windows.Forms.Button
$customBtn.Text = "កំណត់បិទ"
$customBtn.Font = $boldFont
$customBtn.Size = New-Object System.Drawing.Size(120, 32)
$customBtn.Location = New-Object System.Drawing.Point(280, 24)
$customBtn.BackColor = [System.Drawing.Color]::FromArgb(15, 118, 110)
$customBtn.ForeColor = [System.Drawing.Color]::White
$customBtn.FlatStyle = "Flat"
$customBtn.FlatAppearance.BorderSize = 0
$customBtn.Cursor = [System.Windows.Forms.Cursors]::Hand
$customBtn.Add_Click({
    $val = [int]$customInput.Value
    Set-ShutdownTimer -minutes $val -label "$val នាទី"
})
$customGroup.Controls.Add($customBtn)

# Bottom Action Buttons
$cancelBtn = New-Object System.Windows.Forms.Button
$cancelBtn.Text = "❌ លុបចោលការកំណត់បិទ (Cancel)"
$cancelBtn.Font = $khmerFont
$cancelBtn.Size = New-Object System.Drawing.Size(260, 40)
$cancelBtn.Location = New-Object System.Drawing.Point(25, 368)
$cancelBtn.BackColor = [System.Drawing.Color]::FromArgb(254, 226, 226)
$cancelBtn.ForeColor = [System.Drawing.Color]::FromArgb(185, 28, 28)
$cancelBtn.FlatStyle = "Flat"
$cancelBtn.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(248, 113, 113)
$cancelBtn.Cursor = [System.Windows.Forms.Cursors]::Hand
$cancelBtn.Add_Click({ Cancel-ShutdownTimer })
$form.Controls.Add($cancelBtn)

$closeBtn = New-Object System.Windows.Forms.Button
$closeBtn.Text = "បិទផ្ទាំង"
$closeBtn.Font = $khmerFont
$closeBtn.Size = New-Object System.Drawing.Size(145, 40)
$closeBtn.Location = New-Object System.Drawing.Point(295, 368)
$closeBtn.BackColor = [System.Drawing.Color]::FromArgb(241, 245, 249)
$closeBtn.ForeColor = [System.Drawing.Color]::FromArgb(71, 85, 105)
$closeBtn.FlatStyle = "Flat"
$closeBtn.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(203, 213, 225)
$closeBtn.Cursor = [System.Windows.Forms.Cursors]::Hand
$closeBtn.Add_Click({ $form.Close() })
$form.Controls.Add($closeBtn)

[void]$form.ShowDialog()
