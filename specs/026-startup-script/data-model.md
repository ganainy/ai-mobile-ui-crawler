# Data Model: Application Startup Script

**Feature**: 026-startup-script  
**Date**: 2026-01-18

## Overview

This document describes the internal structure and state management of the startup script. Since this is a PowerShell script (not a data-driven application), the "data model" describes the script's internal variables, configuration, and process tracking.

## Script State

### Process Registry

The script tracks all started processes for cleanup purposes.

| Variable | Type | Description |
|----------|------|-------------|
| `$script:StartedProcesses` | `Process[]` | Array of Process objects started by the script |
| `$script:DockerContainerId` | `string` | ID of the MobSF Docker container (for `docker stop`) |
| `$script:AppiumProcess` | `Process` | Appium server process object |
| `$script:UIProcess` | `Process` | Main UI Python process object |

### Configuration Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `$MOBSF_PORT` | `8000` | Port for MobSF API |
| `$APPIUM_PORT` | `4723` | Port for Appium server |
| `$APPIUM_ADDRESS` | `127.0.0.1` | Appium bind address |
| `$MOBSF_IMAGE` | `opensecurity/mobile-security-framework-mobsf` | Docker image name |
| `$STARTUP_TIMEOUT` | `60` | Seconds to wait for service readiness |

### Command Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `-NoMobsf` | switch | false | Skip starting MobSF Docker container |
| `-NoAppium` | switch | false | Skip starting Appium server |
| `-UiOnly` | switch | false | Start only the UI (implies -NoMobsf -NoAppium) |
| `-Help` | switch | false | Display usage information |

## Dependency Status

The script evaluates these dependencies at startup:

| Dependency | Check Method | Required For |
|------------|--------------|--------------|
| Docker | `Get-Command docker` + `docker info` | MobSF |
| npm/npx | `Get-Command npx` | Appium |
| Python | `Get-Command python` | Main UI |

### Dependency Status Enum

```text
Available    - Command exists and is functional
NotInstalled - Command not found in PATH
NotRunning   - Command exists but service not running (Docker daemon)
```

## Process Lifecycle

```text
                    ┌─────────────────────────────────────────────────┐
                    │              Script Entry                        │
                    └─────────────────────────────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────────┐
                    │         Parse Command-Line Arguments             │
                    └─────────────────────────────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────────┐
                    │         Check Dependencies (Docker, npm, Python) │
                    │         Display warnings for missing ones        │
                    └─────────────────────────────────────────────────┘
                                         │
                                         ▼
           ┌─────────────────────────────┴─────────────────────────────┐
           │                                                           │
           ▼                                                           ▼
┌─────────────────────┐                                    ┌─────────────────────┐
│ Start MobSF Docker  │ (if Docker available & !NoMobsf)   │ Skip MobSF          │
│ Register process    │                                    │ (warn if missing)   │
└─────────────────────┘                                    └─────────────────────┘
           │                                                           │
           └─────────────────────────────┬─────────────────────────────┘
                                         ▼
           ┌─────────────────────────────┴─────────────────────────────┐
           │                                                           │
           ▼                                                           ▼
┌─────────────────────┐                                    ┌─────────────────────┐
│ Start Appium        │ (if npx available & !NoAppium)     │ Skip Appium         │
│ Register process    │                                    │ (warn if missing)   │
└─────────────────────┘                                    └─────────────────────┘
           │                                                           │
           └─────────────────────────────┬─────────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────────┐
                    │         Wait for Services to be Ready            │
                    │         (port check with timeout)                │
                    └─────────────────────────────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────────┐
                    │         Start Main UI (python run_ui.py)         │
                    │         Wait for UI process to exit              │
                    └─────────────────────────────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────────┐
                    │         Cleanup: Stop all registered processes   │
                    │         (Triggered by UI exit or Ctrl+C)         │
                    └─────────────────────────────────────────────────┘
```

## Console Output Format

### Status Message Format

```text
[TIMESTAMP] [STATUS] Message text
```

Example output:
```text
[19:08:00] [INFO] Starting Mobile Crawler Application Stack...
[19:08:00] [CHECK] Checking dependencies...
[19:08:00] [OK] Docker: Available
[19:08:00] [OK] npm/npx: Available
[19:08:00] [OK] Python: Available
[19:08:01] [START] Starting MobSF Docker container...
[19:08:03] [WAIT] Waiting for MobSF to be ready on port 8000...
[19:08:15] [OK] MobSF is ready
[19:08:15] [START] Starting Appium server...
[19:08:17] [OK] Appium is ready on port 4723
[19:08:17] [START] Starting main UI...
[19:08:17] [OK] All components started successfully!
```

### Color Scheme

| Status | Color | Symbol |
|--------|-------|--------|
| INFO | Cyan | ℹ |
| CHECK | White | ? |
| OK | Green | ✓ |
| WARN | Yellow | ⚠ |
| ERROR | Red | ✗ |
| START | Cyan | → |
| WAIT | Gray | ⏳ |
