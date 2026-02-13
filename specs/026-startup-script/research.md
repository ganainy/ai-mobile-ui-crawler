# Research: Application Startup Script

**Feature**: 026-startup-script  
**Date**: 2026-01-18

## Research Topics

### 1. PowerShell Background Job Management

**Decision**: Use PowerShell Jobs (`Start-Job`) for background processes with `Start-Process` for visibility.

**Rationale**: 
- `Start-Process` allows launching processes in new windows, giving visibility into each component's output
- PowerShell's `Register-ObjectEvent` can be used for process exit monitoring
- For a simpler approach, use `-NoNewWindow` with background jobs to capture output
- Using `-PassThru` with `Start-Process` returns Process objects for later management

**Alternatives Considered**:
1. **Start-Job**: Good for background work but hides output from user; harder to debug
2. **Start-Process with new windows**: Gives visibility but clutters the desktop
3. **Single-window with multiplexed output**: Complex to implement, poor UX

**Final Approach**: Use `Start-Process -PassThru` to launch Docker and Appium in background, keep the main Python UI in the foreground. Store process objects for cleanup on Ctrl+C.

---

### 2. Dependency Detection Methods

**Decision**: Use `Get-Command` for checking if executables are in PATH.

**Rationale**:
- `Get-Command docker -ErrorAction SilentlyContinue` returns null if not found
- Works reliably across Windows versions
- Fast execution (no external calls)

**Implementation**:
```powershell
function Test-CommandExists {
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}
```

**Docker Daemon Check**: Even if Docker is installed, the daemon may not be running. Use:
```powershell
docker info 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { "Docker daemon not running" }
```

**Alternatives Considered**:
1. **Test-Path on install locations**: Unreliable, varies by installation
2. **Registry checks**: Complex, version-dependent
3. **Try-catch on actual command**: Slower, but more accurate

---

### 3. Port Availability Checking

**Decision**: Use `Test-NetConnection` or direct socket test.

**Rationale**:
- `Test-NetConnection -ComputerName localhost -Port 8000` can check if a port is in use
- Alternative: `[System.Net.Sockets.TcpClient]` for faster checks

**Implementation**:
```powershell
function Test-PortInUse {
    param([int]$Port)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $Port)
        $tcp.Close()
        return $true  # Port is in use
    } catch {
        return $false  # Port is free
    }
}
```

**Alternatives Considered**:
1. **netstat parsing**: Works but slow and string-parsing is fragile
2. **Test-NetConnection**: Cleaner but slower (includes ping timeout)
3. **Direct socket test**: Fast and reliable

---

### 4. Graceful Shutdown Handling (Ctrl+C)

**Decision**: Use `try/finally` block with process tracking.

**Rationale**:
- PowerShell's `try/finally` executes the `finally` block on Ctrl+C
- Store started process objects in a script-scope array
- Iterate and stop each process in `finally`

**Implementation Pattern**:
```powershell
$script:StartedProcesses = @()

try {
    # Start processes, add to $script:StartedProcesses
    # ...
    
    # Wait for main process (UI) to exit
    Wait-Process -Id $mainProcess.Id
} finally {
    Write-Host "Shutting down..." -ForegroundColor Yellow
    foreach ($proc in $script:StartedProcesses) {
        if (-not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
```

**Docker Container Cleanup**: Use `docker stop <container_name>` instead of `Stop-Process` for clean shutdown:
```powershell
docker stop mobile-security-framework-mobsf 2>$null
```

**Alternatives Considered**:
1. **Register-EngineEvent**: More complex, not necessary for this use case
2. **Trap statement**: Less flexible than try/finally

---

### 5. Command-Line Argument Parsing

**Decision**: Use `param()` block with `[switch]` parameters.

**Rationale**:
- PowerShell native approach, no external dependencies
- Clear syntax: `.\start.ps1 --no-mobsf --no-appium`
- Built-in help generation with `[CmdletBinding()]`

**Implementation**:
```powershell
[CmdletBinding()]
param(
    [switch]$NoMobsf,
    [switch]$NoAppium,
    [switch]$UiOnly,
    [switch]$Help
)
```

**Note on PowerShell conventions**: PowerShell uses `-NoMobsf` (with single dash), but we can support both styles.

---

### 6. Colored Console Output

**Decision**: Use `Write-Host -ForegroundColor` for status messages.

**Rationale**:
- Built-in, no dependencies
- Supports standard terminal colors
- Use consistent color scheme: Green=success, Yellow=warning, Red=error, Cyan=info

**Color Scheme**:
| Status | Color |
|--------|-------|
| Starting | Cyan |
| Success | Green |
| Warning | Yellow |
| Error | Red |
| Info | White |

---

### 7. Waiting for Service Readiness

**Decision**: Use health check polling with timeout.

**Rationale**:
- MobSF and Appium need time to start before the UI should connect
- Simple HTTP health check for MobSF: `http://localhost:8000/api/v1/upload` (or home page)
- Appium: Check if port 4723 is accepting connections

**Implementation**:
```powershell
function Wait-ForService {
    param(
        [string]$Name,
        [int]$Port,
        [int]$TimeoutSeconds = 60
    )
    
    $startTime = Get-Date
    while ((Get-Date) - $startTime -lt [TimeSpan]::FromSeconds($TimeoutSeconds)) {
        if (Test-PortInUse -Port $Port) {
            Write-Host "  ✓ $Name is ready on port $Port" -ForegroundColor Green
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    Write-Host "  ⚠ $Name did not become ready within $TimeoutSeconds seconds" -ForegroundColor Yellow
    return $false
}
```

---

## Summary of Decisions

| Topic | Decision |
|-------|----------|
| Background processes | `Start-Process -PassThru` with process tracking |
| Dependency detection | `Get-Command` for PATH check, `docker info` for daemon |
| Port checking | Direct TCP socket connection test |
| Graceful shutdown | `try/finally` with process Stop-Process |
| CLI arguments | PowerShell `param()` with `[switch]` parameters |
| Console output | `Write-Host -ForegroundColor` with consistent color scheme |
| Service readiness | Port polling with configurable timeout |
