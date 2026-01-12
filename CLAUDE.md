# mobile-crawler Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-11

## Active Technologies
- Python 3.11+ + pytest, appium-python-client, selenium (W3C Actions), pytesseract (OCR) (007-test-app-actions-verify)
- N/A (stateless tests) (007-test-app-actions-verify)
- Python 3.11 + PySide6 (Qt bindings), Pillow (PIL for image manipulation) (008-debug-overlay)
- Screenshots saved to filesystem (`screenshots/run_{id}/`) (008-debug-overlay)

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
- 008-debug-overlay: Added Python 3.11 + PySide6 (Qt bindings), Pillow (PIL for image manipulation)
- 007-test-app-actions-verify: Added Python 3.11+ + pytest, appium-python-client, selenium (W3C Actions), pytesseract (OCR)

- 007-test-app-actions-verify: Added Python 3.9+ + appium-python-client, pytest, requests

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
