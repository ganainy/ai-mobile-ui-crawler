
' VBScript to run the Mobile Crawler UI silently (no terminal window)
' This script automatically detects and activates the virtual environment

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptPath

' Determine Python executable (strict venv312 only)
pythonExe = scriptPath & "\venv312\Scripts\python.exe"

If Not fso.FileExists(pythonExe) Then
    MsgBox "venv312 not found. Create it with: python -m venv venv312", vbCritical, "Mobile Crawler"
    WScript.Quit 1
End If

' Build command to run the UI
runUiScript = scriptPath & "\run_ui.py"
command = """" & pythonExe & """ """ & runUiScript & """"

' Run the command silently (WindowStyle = 0 means hidden)
WshShell.Run command, 0, False



