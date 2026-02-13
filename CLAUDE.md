# mobile-crawler Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-15

## Active Technologies
- Python 3.11 + PySide6 (Qt), Appium, Pillow, easyocr (025-stats-and-stability)
- SQLite (via DatabaseManager) (025-stats-and-stability)
- PowerShell 5.1+ (Windows built-in) + Docker Desktop, Node.js (npm/npx), Python 3.x (026-startup-script)
- N/A (script only, no persistence) (026-startup-script)

- Python 3.12 + PyQt6, Appium, requests, asyncio (024-crawl-stability-fixes)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.12: Follow standard conventions

## Recent Changes
- 026-startup-script: Added PowerShell 5.1+ (Windows built-in) + Docker Desktop, Node.js (npm/npx), Python 3.x
- 025-stats-and-stability: Added Python 3.11 + PySide6 (Qt), Appium, Pillow, easyocr

- 024-crawl-stability-fixes: Added Python 3.12 + PyQt6, Appium, requests, asyncio

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
