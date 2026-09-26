---
author: claude
updated: 2026-09-26
---
# API key Test buttons

Request: a button next to each API key in Settings that checks the key works.

- `domain/api_key_check.py`: `check_api_key(provider, key) -> (ok, message)`. Gemini: GET `v1beta/models?pageSize=1` with `x-goog-api-key`. OpenRouter: GET `/api/v1/auth/key` (the `/models` endpoint is public, so it can't validate a key). 400/401/403 = rejected.
- `ui/widgets/settings_panel.py`: Test button + status label per key; worker thread emits `_api_key_test_done`.
- Tests: `tests/domain/test_api_key_check.py` (mocked `requests`).
- Not tried in the GUI or with real keys.
