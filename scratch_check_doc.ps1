
 = 
try {
     = New-Object -ComObject Word.Application
    Write-Host 'Word COM available'
     = Resolve-Path 'Excel/D01.doc'
     = .Documents.Open(.Path)
    Write-Host 'D01 Content:'
    Write-Host .Content.Text
    .Close()
} catch {
    Write-Host 'Error:' 
} finally {
    if () { .Quit() }
}
