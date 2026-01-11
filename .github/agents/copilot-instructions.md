# mobile-crawler Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-10

## Active Technologies
- Python 3.9+ (compatible with 3.9, 3.10, 3.11, 3.12) + PySide6 >=6.6.0, cryptography >=42.0.0, sqlite3 (stdlib) (001-fix-settings-persistence)
- SQLite (user_config.db in platform-specific app data directory) (001-fix-settings-persistence)
- Python 3.9+ + PySide6 >=6.6.0 (002-ai-io-monitor)
- SQLite via existing `AIInteractionRepository` (crawler.db) (002-ai-io-monitor)

- Python 3.12 + PySide6 6.x, existing mobile_crawler modules (001-wire-gui-widgets)

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
- 002-ai-io-monitor: Added Python 3.9+ + PySide6 >=6.6.0
- 001-fix-settings-persistence: Added Python 3.9+ (compatible with 3.9, 3.10, 3.11, 3.12) + PySide6 >=6.6.0, cryptography >=42.0.0, sqlite3 (stdlib)

- 001-wire-gui-widgets: Added Python 3.12 + PySide6 6.x, existing mobile_crawler modules

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
