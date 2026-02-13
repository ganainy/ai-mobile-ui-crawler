# Contracts: Application Startup Script

**Feature**: 026-startup-script  
**Date**: 2026-01-18

## Not Applicable

This feature is a standalone PowerShell script that does not expose any programmatic APIs or contracts.

The script provides a **CLI interface** with the following command-line options:

| Flag | Type | Description |
|------|------|-------------|
| `-NoMobsf` | switch | Skip starting MobSF Docker container |
| `-NoAppium` | switch | Skip starting Appium server |
| `-UiOnly` | switch | Start only the UI (implies -NoMobsf -NoAppium) |
| `-Help` | switch | Display usage information |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - all requested components started and exited cleanly |
| 1 | Python not available - cannot start main UI |
| 2 | User interrupted (Ctrl+C) - cleanup completed |

## Environment Requirements

The script expects to be run from the repository root directory where `run_ui.py` is located.
