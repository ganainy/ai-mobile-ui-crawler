
' VBScript to run the Appium Traverser silently (no terminal window)
' This script automatically detects and activates the virtual environment

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptPath

' Determine Python executable (check virtual environment first)
pythonExe = ""

' Check if Appium is running (port 4723)
' Returns 0 if found (listening), 1 if not found
' We use findstr to look for the port in netstat output
appiumCheck = WshShell.Run("cmd /c netstat -an | findstr "":4723""", 0, True)

If appiumCheck <> 0 Then
    ' Appium is not running, start it silently
    ' We assume npx is available in the system PATH
    WshShell.Run "cmd /c npx appium -p 4723", 0, False
    
    ' Give Appium some time to initialize (8 seconds)
    ' Note: May need more time on slower machines or first run
    WScript.Sleep 8000
End If
if fso.FolderExists(scriptPath & "\.venv\Scripts") then
    pythonExe = scriptPath & "\.venv\Scripts\python.exe"
elseif fso.FolderExists(scriptPath & "\venv\Scripts") then
    pythonExe = scriptPath & "\venv\Scripts\python.exe"
elseif fso.FolderExists(scriptPath & "\env\Scripts") then
    pythonExe = scriptPath & "\env\Scripts\python.exe"
else
    pythonExe = "python"
end if

' Build command to run the UI
runUiScript = scriptPath & "\run_ui.py"
command = """" & pythonExe & """ """ & runUiScript & """"

' Run the command silently (WindowStyle = 0 means hidden)
WshShell.Run command, 0, False



