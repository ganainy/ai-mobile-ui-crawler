# mobile-crawler Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-11

## Active Technologies
- Python 3.11+ + pytest, appium-python-client, selenium (W3C Actions), pytesseract (OCR) (007-test-app-actions-verify)
- N/A (stateless tests) (007-test-app-actions-verify)
- Python 3.11 + PySide6 (Qt bindings), Pillow (PIL for image manipulation) (008-debug-overlay)
- Screenshots saved to filesystem (`screenshots/run_{id}/`) (008-debug-overlay)
- Python 3.11 + PySide6, SQLite (010-fix-run-history-ui)
- `crawler.db` (SQLite), specific folder structure in `output_data/` (010-fix-run-history-ui)
- [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION] + [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION] (010-fix-run-history-ui)
- [if applicable, e.g., PostgreSQL, CoreData, files or N/A] (010-fix-run-history-ui)
- Python 3.11+ + pytest, Appium (via existing `device_verifier` infrastructure), selenium (016-auth-e2e-tests)
- N/A (tests store credentials in memory only) (016-auth-e2e-tests)
- Python 3.11+ (Test Suite) + Dart/Flutter (Optional Test App) + Appium, Android UiAutomator2, Gmail app on device (016-auth-e2e-tests)
- N/A (stateless test execution) (016-auth-e2e-tests)
- Python 3.11+ + PySide6 (Qt for Python), PIL/Pillow (017-ui-monitor-improvements)
- N/A (in-memory UI state, existing SQLite for persistence) (017-ui-monitor-improvements)

- Python 3.9+ + appium-python-client, pytest, requests (007-test-app-actions-verify)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.9+: Follow standard conventions

## Recent Changes
- 017-ui-monitor-improvements: Added Python 3.11+ + PySide6 (Qt for Python), PIL/Pillow
- 016-auth-e2e-tests: Added Python 3.11+ (Test Suite) + Dart/Flutter (Optional Test App) + Appium, Android UiAutomator2, Gmail app on device
- 016-auth-e2e-tests: Added Python 3.11+ + pytest, Appium (via existing `device_verifier` infrastructure), selenium


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
