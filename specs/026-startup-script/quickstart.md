# Quickstart: Application Startup Script

**Feature**: 026-startup-script  
**Date**: 2026-01-18

## Prerequisites

Before using the startup script, ensure you have the following installed:

| Component | Required For | Installation |
|-----------|--------------|--------------|
| Docker Desktop | MobSF | [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/) |
| Node.js (npm/npx) | Appium | [https://nodejs.org/](https://nodejs.org/) |
| Python 3.x | Main UI | [https://www.python.org/downloads/](https://www.python.org/downloads/) |

## Quick Start

### Start Everything (Default)

```powershell
.\scripts\start.ps1
```

This will:
1. Check if Docker, npm, and Python are installed
2. Start MobSF Docker container on port 8000
3. Start Appium server on port 4723
4. Wait for services to be ready
5. Launch the main UI application

### Stop All Components

Press `Ctrl+C` in the PowerShell window to gracefully stop all components.

## Usage Options

### Skip MobSF

If you don't need MobSF for your current work:

```powershell
.\scripts\start.ps1 -NoMobsf
```

### Skip Appium

If you don't need Appium for your current work:

```powershell
.\scripts\start.ps1 -NoAppium
```

### UI Only

Start only the main UI without any dependencies:

```powershell
.\scripts\start.ps1 -UiOnly
```

### Show Help

```powershell
.\scripts\start.ps1 -Help
```

## What If Dependencies Are Missing?

The script will warn you if any dependency is missing but continue with the components that are available.

### Example: Docker Not Installed

```text
[19:08:00] [WARN] Docker is not installed. MobSF will not be started.
           Install from: https://www.docker.com/products/docker-desktop/
[19:08:00] [OK] npm/npx: Available
[19:08:00] [OK] Python: Available
[19:08:00] [START] Starting Appium server...
```

### Example: Docker Daemon Not Running

```text
[19:08:00] [WARN] Docker daemon is not running. Start Docker Desktop first.
           MobSF will not be started.
```

## Troubleshooting

### Port Already in Use

If you see a warning about a port being in use, another instance may already be running:

```text
[19:08:00] [WARN] Port 8000 is already in use. MobSF may already be running.
           Skipping MobSF startup.
```

**Solution**: Either use the existing instance or stop the conflicting process.

### First-Time Docker Image Pull

On first run, Docker needs to download the MobSF image (~1-2 GB). This may take several minutes:

```text
[19:08:00] [INFO] Pulling MobSF Docker image (first time only)...
           This may take a few minutes...
```

### Script Execution Policy

If you get an error about script execution being disabled:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Integration with Development Workflow

For daily development, you can add a shortcut or alias:

### PowerShell Profile Alias

Add to your PowerShell profile (`$PROFILE`):

```powershell
function Start-MobileCrawler {
    Set-Location "E:\VS-projects\mobile-crawler"
    .\scripts\start.ps1 @args
}
Set-Alias mc Start-MobileCrawler
```

Then start with just:

```powershell
mc              # Full stack
mc -UiOnly      # UI only
```
