<#
.SYNOPSIS
    Mobile Crawler Application Startup Script

.DESCRIPTION
    Starts the complete mobile-crawler application stack:
    - MobSF (Mobile Security Framework) Docker container on port 8000
    - Appium server on port 4723
    - Main UI application (Python)
    
    Checks for dependencies and displays warnings if components are missing.
    Handles graceful shutdown on Ctrl+C.

.PARAMETER NoMobsf
    Skip starting the MobSF Docker container

.PARAMETER NoAppium
    Skip starting the Appium server

.PARAMETER UiOnly
    Start only the main UI (implies -NoMobsf and -NoAppium)

.PARAMETER Help
    Display usage information

.EXAMPLE
    .\start.ps1
    Starts all components (MobSF, Appium, UI)

.EXAMPLE
    .\start.ps1 -NoMobsf
    Starts only Appium and UI

.EXAMPLE
    .\start.ps1 -UiOnly
    Starts only the UI application

.NOTES
    Author: Mobile Crawler Team
    Requires: PowerShell 5.1+, Docker Desktop, Node.js (npm/npx), Python 3.x
#>

[CmdletBinding()]
param(
    [switch]$NoMobsf,
    [switch]$NoAppium,
    [switch]$UiOnly,
    [switch]$Help
)

# ============================================================================
# Configuration
# ============================================================================

$script:MOBSF_PORT = 8000
$script:APPIUM_PORT = 4723
$script:APPIUM_ADDRESS = "127.0.0.1"
$script:MOBSF_IMAGE = "opensecurity/mobile-security-framework-mobsf"
$script:MOBSF_CONTAINER_NAME = "mobile-crawler-mobsf"
$script:STARTUP_TIMEOUT = 60
$script:MOBSF_API_KEY_FILE = ".mobsf_api_key"

# Process tracking for cleanup
$script:StartedProcesses = @()
$script:MobSFContainerStarted = $false
$script:MobSFApiKey = $null

# ============================================================================
# Helper Functions
# ============================================================================

function Write-Status {
    <#
    .SYNOPSIS
        Writes a colored status message to the console
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Message,
        
        [Parameter(Mandatory)]
        [ValidateSet("INFO", "OK", "WARN", "ERROR", "START", "WAIT", "CHECK")]
        [string]$Status
    )
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    $symbol = switch ($Status) {
        "INFO" { "i"; $color = "Cyan" }
        "OK" { "+"; $color = "Green" }
        "WARN" { "!"; $color = "Yellow" }
        "ERROR" { "x"; $color = "Red" }
        "START" { ">"; $color = "Cyan" }
        "WAIT" { "~"; $color = "Gray" }
        "CHECK" { "?"; $color = "White" }
    }
    
    Write-Host "[$timestamp] " -NoNewline -ForegroundColor DarkGray
    Write-Host "[$symbol] " -NoNewline -ForegroundColor $color
    Write-Host $Message -ForegroundColor $color
}

function Test-CommandExists {
    <#
    .SYNOPSIS
        Checks if a command exists in PATH
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Command
    )
    
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

function Test-DockerRunning {
    <#
    .SYNOPSIS
        Checks if Docker daemon is running
    #>
    if (-not (Test-CommandExists "docker")) {
        return $false
    }
    
    $null = docker info 2>&1
    return $LASTEXITCODE -eq 0
}

function Test-PortInUse {
    <#
    .SYNOPSIS
        Checks if a port is already in use
    #>
    param(
        [Parameter(Mandatory)]
        [int]$Port
    )
    
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $Port)
        $tcp.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Test-Dependencies {
    <#
    .SYNOPSIS
        Checks all dependencies and returns status
    #>
    param(
        [switch]$CheckMobsf,
        [switch]$CheckAppium
    )
    
    $status = @{
        Docker        = $false
        DockerRunning = $false
        Npm           = $false
        Python        = $false
    }
    
    Write-Status "Checking dependencies..." -Status CHECK
    
    # Check Docker
    if ($CheckMobsf) {
        if (Test-CommandExists "docker") {
            $status.Docker = $true
            if (Test-DockerRunning) {
                $status.DockerRunning = $true
                Write-Status "Docker: Available and running" -Status OK
            }
            else {
                Write-Status "Docker: Installed but daemon not running" -Status WARN
                Write-Host "           Start Docker Desktop and try again." -ForegroundColor Yellow
            }
        }
        else {
            Write-Status "Docker: Not installed - MobSF will not be started" -Status WARN
            Write-Host "           Install from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
        }
    }
    
    # Check npm/npx for Appium
    if ($CheckAppium) {
        if (Test-CommandExists "npx") {
            $status.Npm = $true
            Write-Status "npm/npx: Available" -Status OK
        }
        else {
            Write-Status "npm/npx: Not installed - Appium will not be started" -Status WARN
            Write-Host "           Install from: https://nodejs.org/" -ForegroundColor Yellow
        }
    }
    
    # Check Python (always required for UI)
    if (Test-CommandExists "python") {
        $status.Python = $true
        Write-Status "Python: Available" -Status OK
    }
    else {
        Write-Status "Python: Not installed - Cannot start main UI" -Status ERROR
        Write-Host "           Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
    }
    
    return $status
}

# ============================================================================
# Component Startup Functions
# ============================================================================

function Start-MobSF {
    <#
    .SYNOPSIS
        Starts the MobSF Docker container
    #>
    
    # Check if port is already in use
    if (Test-PortInUse -Port $script:MOBSF_PORT) {
        Write-Status "Port $($script:MOBSF_PORT) is already in use - MobSF may already be running" -Status WARN
        Write-Host "           Skipping MobSF startup." -ForegroundColor Yellow
        return $true
    }
    
    Write-Status "Starting MobSF Docker container on port $($script:MOBSF_PORT)..." -Status START
    
    # Stop any existing container with the same name
    $null = docker stop $script:MOBSF_CONTAINER_NAME 2>&1
    $null = docker rm $script:MOBSF_CONTAINER_NAME 2>&1
    
    # Start the container
    $process = Start-Process -FilePath "docker" -ArgumentList @(
        "run",
        "--name", $script:MOBSF_CONTAINER_NAME,
        "--rm",
        "-p", "$($script:MOBSF_PORT):8000",
        $script:MOBSF_IMAGE
    ) -PassThru -WindowStyle Hidden
    
    if ($process) {
        $script:StartedProcesses += $process
        $script:MobSFContainerStarted = $true
        return $true
    }
    
    Write-Status "Failed to start MobSF container" -Status ERROR
    return $false
}

function Start-Appium {
    <#
    .SYNOPSIS
        Starts the Appium server
    #>
    
    # Check if port is already in use
    if (Test-PortInUse -Port $script:APPIUM_PORT) {
        Write-Status "Port $($script:APPIUM_PORT) is already in use - Appium may already be running" -Status WARN
        Write-Host "           Skipping Appium startup." -ForegroundColor Yellow
        return $true
    }
    
    Write-Status "Starting Appium server on port $($script:APPIUM_PORT)..." -Status START
    
    # Use cmd.exe to run npx (npx.cmd doesn't work directly with Start-Process on Windows)
    $appiumArgs = "appium --address $($script:APPIUM_ADDRESS) --port $($script:APPIUM_PORT) --relaxed-security"
    $process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npx $appiumArgs" -PassThru -WindowStyle Hidden
    
    if ($process) {
        $script:StartedProcesses += $process
        return $true
    }
    
    Write-Status "Failed to start Appium server" -Status ERROR
    return $false
}

function Start-MainUI {
    <#
    .SYNOPSIS
        Starts the main UI application
    #>
    
    Write-Status "Starting main UI application..." -Status START
    
    # Run in current window (foreground) so user can see output
    $process = Start-Process -FilePath "python" -ArgumentList "run_ui.py" -PassThru -NoNewWindow
    
    if ($process) {
        $script:StartedProcesses += $process
        return $process
    }
    
    Write-Status "Failed to start main UI" -Status ERROR
    return $null
}

function Wait-ForService {
    <#
    .SYNOPSIS
        Waits for a service to become available on a port
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Name,
        
        [Parameter(Mandatory)]
        [int]$Port,
        
        [int]$TimeoutSeconds = 60
    )
    
    Write-Status "Waiting for $Name to be ready on port $Port..." -Status WAIT
    
    $startTime = Get-Date
    $timeout = [TimeSpan]::FromSeconds($TimeoutSeconds)
    
    while ((Get-Date) - $startTime -lt $timeout) {
        if (Test-PortInUse -Port $Port) {
            Write-Status "$Name is ready on port $Port" -Status OK
            
            # If this is MobSF, try to extract the API key from logs
            if ($Name -eq "MobSF") {
                $apiKey = Get-MobSFApiKey
                if ($apiKey) {
                    $script:MobSFApiKey = $apiKey
                    Save-MobSFApiKey -ApiKey $apiKey
                }
            }
            
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    
    Write-Status "$Name did not become ready within $TimeoutSeconds seconds" -Status WARN
    return $false
}

function Get-MobSFApiKey {
    <#
    .SYNOPSIS
        Extracts the REST API key from MobSF Docker container logs
    .PARAMETER RetryCount
        Number of times to retry if key not found
    .PARAMETER RetryDelaySeconds
        Seconds to wait between retries
    #>
    param(
        [int]$RetryCount = 20,  # 60 seconds total - MobSF first start needs time for DB migrations
        [int]$RetryDelaySeconds = 3
    )
    
    Write-Status "Waiting for MobSF API key (this may take up to $($RetryCount * $RetryDelaySeconds) seconds)..." -Status WAIT
    
    for ($i = 0; $i -lt $RetryCount; $i++) {
        try {
            # Get container logs
            $logs = docker logs $script:MOBSF_CONTAINER_NAME 2>&1
            
            # Look for the REST API Key line
            # MobSF outputs with ANSI color codes, so we need to strip them first
            # Format: "REST API Key: [1mXXXXXXXXXXXXXX..." with escape codes
            foreach ($line in $logs) {
                # Strip ANSI escape codes: ESC[...m patterns
                $cleanLine = $line -replace '\x1b\[[0-9;]*m', ''
                
                if ($cleanLine -match "REST API Key:\s*([a-fA-F0-9]+)") {
                    $apiKey = $matches[1]
                    Write-Status "Extracted MobSF API Key: $($apiKey.Substring(0,8))..." -Status OK
                    return $apiKey
                }
            }
        }
        catch {
            Write-Status "Failed to read MobSF logs: $_" -Status WARN
        }
        
        # Wait before next attempt (except on last iteration)
        if ($i -lt $RetryCount - 1) {
            Write-Host "           Attempt $($i + 1)/$RetryCount - API key not found yet, waiting..." -ForegroundColor Gray
            Start-Sleep -Seconds $RetryDelaySeconds
        }
    }
    
    Write-Status "MobSF API Key not found after $RetryCount attempts" -Status WARN
    Write-Host "           You may need to manually copy the API key from MobSF logs." -ForegroundColor Yellow
    Write-Host "           Run: docker logs $($script:MOBSF_CONTAINER_NAME) | Select-String 'REST API Key'" -ForegroundColor Yellow
    return $null
}

function Save-MobSFApiKey {
    <#
    .SYNOPSIS
        Saves the MobSF API key to a file for the Python app to read
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ApiKey
    )
    
    try {
        # Save to file in project root
        $ApiKey | Out-File -FilePath $script:MOBSF_API_KEY_FILE -Encoding UTF8 -NoNewline
        Write-Status "MobSF API Key saved to $($script:MOBSF_API_KEY_FILE)" -Status OK
        Write-Host "           The app will automatically use this key for MobSF authentication." -ForegroundColor Gray
        return $true
    }
    catch {
        Write-Status "Failed to save MobSF API Key: $_" -Status WARN
        return $false
    }
}

# ============================================================================
# Cleanup Functions
# ============================================================================

function Stop-MobSFContainer {
    <#
    .SYNOPSIS
        Stops the MobSF Docker container gracefully
    #>
    if ($script:MobSFContainerStarted) {
        Write-Status "Stopping MobSF container..." -Status INFO
        $null = docker stop $script:MOBSF_CONTAINER_NAME 2>&1
    }
}

function Stop-AllProcesses {
    <#
    .SYNOPSIS
        Stops all tracked processes
    #>
    Write-Status "Cleaning up processes..." -Status INFO
    
    # Stop MobSF container first (graceful Docker stop)
    Stop-MobSFContainer
    
    # Stop other processes
    foreach ($proc in $script:StartedProcesses) {
        if ($proc -and -not $proc.HasExited) {
            try {
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
            catch {
                # Process may have already exited
            }
        }
    }
    
    Write-Status "Cleanup complete" -Status OK
}

# ============================================================================
# Help Display
# ============================================================================

function Show-Help {
    Write-Host ""
    Write-Host "Mobile Crawler Startup Script" -ForegroundColor Cyan
    Write-Host "=============================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\start.ps1 [options]" -ForegroundColor White
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -NoMobsf    Skip starting MobSF Docker container"
    Write-Host "  -NoAppium   Skip starting Appium server"
    Write-Host "  -UiOnly     Start only the UI (same as -NoMobsf -NoAppium)"
    Write-Host "  -Help       Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\start.ps1              # Start everything"
    Write-Host "  .\start.ps1 -NoMobsf     # Start Appium + UI only"
    Write-Host "  .\start.ps1 -UiOnly      # Start UI only"
    Write-Host ""
    Write-Host "Requirements:" -ForegroundColor Yellow
    Write-Host "  - Docker Desktop (for MobSF)"
    Write-Host "  - Node.js with npm/npx (for Appium)"
    Write-Host "  - Python 3.x (for main UI)"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop all components." -ForegroundColor Gray
    Write-Host ""
}

# ============================================================================
# Main Execution
# ============================================================================

# Handle -UiOnly flag (implies both -NoMobsf and -NoAppium)
if ($UiOnly) {
    $NoMobsf = $true
    $NoAppium = $true
}

# Show help if requested
if ($Help) {
    Show-Help
    exit 0
}

# Main execution with cleanup on exit
try {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Mobile Crawler Application Startup   " -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Check dependencies
    $deps = Test-Dependencies -CheckMobsf:(-not $NoMobsf) -CheckAppium:(-not $NoAppium)
    
    # Verify Python is available (required)
    if (-not $deps.Python) {
        Write-Status "Cannot continue without Python" -Status ERROR
        exit 1
    }
    
    Write-Host ""
    
    # Start MobSF if requested and Docker is available
    if (-not $NoMobsf) {
        if ($deps.Docker -and $deps.DockerRunning) {
            Start-MobSF | Out-Null
        }
    }
    else {
        Write-Status "Skipping MobSF (--NoMobsf flag)" -Status INFO
    }
    
    # Start Appium if requested and npm is available
    if (-not $NoAppium) {
        if ($deps.Npm) {
            Start-Appium | Out-Null
        }
    }
    else {
        Write-Status "Skipping Appium (--NoAppium flag)" -Status INFO
    }
    
    # Wait for services to be ready
    Write-Host ""
    
    if (-not $NoMobsf -and $deps.Docker -and $deps.DockerRunning) {
        Wait-ForService -Name "MobSF" -Port $script:MOBSF_PORT -TimeoutSeconds $script:STARTUP_TIMEOUT | Out-Null
    }
    
    if (-not $NoAppium -and $deps.Npm) {
        Wait-ForService -Name "Appium" -Port $script:APPIUM_PORT -TimeoutSeconds 30 | Out-Null
    }
    
    Write-Host ""
    
    # Start the main UI (runs in foreground)
    $uiProcess = Start-MainUI
    
    if ($uiProcess) {
        Write-Host ""
        Write-Status "All components started successfully!" -Status OK
        Write-Host ""
        Write-Host "Press Ctrl+C to stop all components." -ForegroundColor Gray
        Write-Host ""
        
        # Wait for UI to exit
        Wait-Process -Id $uiProcess.Id -ErrorAction SilentlyContinue
    }
    
}
finally {
    # Cleanup on exit (Ctrl+C or normal exit)
    Write-Host ""
    Stop-AllProcesses
}
