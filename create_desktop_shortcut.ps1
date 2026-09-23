# PowerShell script to create a desktop shortcut for Mobile Crawler
# This script automatically creates a shortcut with icon and proper name

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Get desktop path
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Mobile Crawler.lnk"

# Paths
$IconPathIco = Join-Path $ScriptDir "crawler_logo.ico"

# Find a Python interpreter to launch the GUI. Prefer a project virtualenv's
# windowed interpreter (pythonw.exe) so no console window is shown.
$venvDirs = @(".venv312", "venv312", ".venv", "venv")
$pythonExe = $null
foreach ($venvDir in $venvDirs) {
    $pythonw = Join-Path $ScriptDir (Join-Path $venvDir "Scripts\pythonw.exe")
    if (Test-Path $pythonw) { $pythonExe = $pythonw; break }
    $python = Join-Path $ScriptDir (Join-Path $venvDir "Scripts\python.exe")
    if (Test-Path $python) { $pythonExe = $python; break }
}
if (-not $pythonExe) {
    $pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
}

# Check if the Python interpreter was found
if (-not $pythonExe) {
    Write-Host "Error: Python not found. Install Python, create a virtualenv, and run 'pip install -e .' first." -ForegroundColor Red
    exit 1
}

# Check if ICO file exists (user should provide it)
if (-not (Test-Path $IconPathIco)) {
    Write-Host "Warning: crawler_logo.ico not found at: $IconPathIco" -ForegroundColor Yellow
    Write-Host "Please ensure the ICO file exists, or the shortcut will be created without a custom icon." -ForegroundColor Yellow
}

# Create WScript.Shell COM object
$WshShell = New-Object -ComObject WScript.Shell

# Create shortcut
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $pythonExe
$Shortcut.Arguments = "-m mobile_crawler.ui.main_window"
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Description = "Launch Mobile Crawler"

# Set icon (Windows shortcuts require ICO format and absolute paths)
$IconSet = $false
if (Test-Path $IconPathIco) {
    try {
        # Verify ICO file is not empty
        $icoFile = Get-Item $IconPathIco
        if ($icoFile.Length -lt 100) {
            Write-Host "Warning: ICO file appears to be too small ($($icoFile.Length) bytes). It may be corrupted." -ForegroundColor Yellow
        }

        # Use absolute path for icon (required by Windows shortcuts)
        $IconPathIcoAbsolute = (Resolve-Path $IconPathIco).Path
        $Shortcut.IconLocation = "$IconPathIcoAbsolute,0"
        Write-Host "Icon set to: $IconPathIcoAbsolute" -ForegroundColor Green
        Write-Host "Icon file size: $($icoFile.Length) bytes" -ForegroundColor Gray
        $IconSet = $true
    } catch {
        Write-Host "Warning: Could not set icon from ICO file: $IconPathIco" -ForegroundColor Yellow
        Write-Host "Error: $_" -ForegroundColor Red
    }
} else {
    Write-Host "Warning: No ICO icon file found (crawler_logo.ico), shortcut will use default icon" -ForegroundColor Yellow
    Write-Host "Please ensure crawler_logo.ico exists in the project directory." -ForegroundColor Yellow
}

# Save shortcut
$Shortcut.Save()

# Note: If icon doesn't appear immediately, you may need to refresh the desktop
# Right-click desktop > Refresh, or press F5

Write-Host "`nDesktop shortcut created successfully!" -ForegroundColor Green
Write-Host "Location: $ShortcutPath" -ForegroundColor Cyan

# Verify icon was set
if ($IconSet) {
    Write-Host "Icon has been set on the shortcut." -ForegroundColor Green
} else {
    Write-Host "`nNote: The shortcut was created but without a custom icon." -ForegroundColor Yellow
    Write-Host "To add the icon, ensure crawler_logo.ico exists and run this script again." -ForegroundColor Yellow
    Write-Host "Or manually set the icon by right-clicking the shortcut > Properties > Change Icon" -ForegroundColor Cyan
}

Write-Host "`nYou can now double-click 'Mobile Crawler' on your desktop to launch the application." -ForegroundColor Green

# Clean up COM object
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($WshShell) | Out-Null
