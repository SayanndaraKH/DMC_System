Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
currentDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentDir

' Collect any arguments passed to this script
argsStr = ""
For i = 0 To WScript.Arguments.Count - 1
    argsStr = argsStr & " " & WScript.Arguments(i)
Next

' Detect Python executable (runs 100% hidden via WshShell window style 0)
pythonBin = ""
userProfile = WshShell.ExpandEnvironmentStrings("%USERPROFILE%")
localAppData = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%")

candidates = Array(_
    currentDir & "\venv\Scripts\python.exe", _
    localAppData & "\Programs\Python\Python311\python.exe", _
    localAppData & "\Programs\Python\Python312\python.exe", _
    localAppData & "\Programs\Python\Python310\python.exe", _
    localAppData & "\Programs\Python\Python313\python.exe", _
    "C:\Program Files\Python311\python.exe", _
    "C:\Program Files\Python312\python.exe", _
    "C:\Python311\python.exe", _
    "C:\Python312\python.exe" _
)

For Each path In candidates
    If FSO.FileExists(path) Then
        pythonBin = path
        Exit For
    End If
Next

If pythonBin = "" Then
    ' Fallback to where command
    On Error Resume Next
    Set execObj = WshShell.Exec("where python.exe")
    Do While Not execObj.StdOut.AtEndOfStream
        line = Trim(execObj.StdOut.ReadLine())
        If InStr(line, "WindowsApps") = 0 And FSO.FileExists(line) Then
            pythonBin = line
            Exit Do
        End If
    Loop
    On Error GoTo 0
End If

If pythonBin = "" Then
    pythonBin = "python.exe"
End If

' Run run.py silently (0 = hide window, False = do not wait)
runCmd = """" & pythonBin & """ """ & currentDir & "\run.py""" & argsStr
WshShell.Run runCmd, 0, False
