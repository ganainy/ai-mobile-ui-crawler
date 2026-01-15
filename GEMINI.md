# mobile-crawler Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-16

## Active Technologies
- Python 3.11+ (Project Standard) + mailosaur (019-force-mailosaur-email)
- Python 3.11+ (Project Standard) + Appium, ADB (Project Standard)
- Python 3.11+ (Project Standard) (009-ocr-som-grounding)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

# Verification Tests (Mailosaur)
pytest tests/unit/domain/test_action_executor_mailosaur.py -v
pytest tests/integration/test_mailosaur_e2e.py -v

## Code Style

Python 3.11+ (Project Standard): Follow standard conventions

## Recent Changes
- 019-force-mailosaur-email: Removed Gmail automation, forced Mailosaur for email verification.
- 018-integrate-mailosaur: Added MailosaurService for OTP/link retrieval via API.
- 017-ui-monitor-improvements: UI feedback improvements for crawler actions.
- 010-fix-run-history-ui: Fixed session history display and folder resolution.

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
