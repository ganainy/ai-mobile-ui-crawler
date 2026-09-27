---
author: claude
updated: 2026-09-27
---
# Dismiss keyboard after typing to stop a stray trailing character

User report (with a screenshot of Google's "Email or phone" field): typing an email address
via the crawler's `type` tool left an extra `.` at the end, reproduced 3 times in a row against
the same field during a real run (`agent/utils/actions.py:type_text`, run log showed steps 5, 7,
9 and 11 all retyping the same address after the Manager LLM kept seeing the stray period).

## Root cause

`type_text` (`agent/utils/actions.py`) calls `AndroidDriver.input_text` and then immediately
returns; the very next queued action (tapping "Next") fires with no settle delay and no keyboard
dismissal. Gboard's predictive/auto-punctuation state hadn't committed yet when focus moved off
the field, and on losing focus it committed a trailing `.` - a known class of flakiness with
`adb shell input text` racing the IME's composing state, not a bug in the shell-escaping (the
reported email had no space/quote/`$`/backtick to mis-escape).

## Fix

`AndroidDriver` already had `hide_keyboard()` (`tools/driver/android.py`), which sends BACK only
when the IME is actually shown. Both `type_text` and `type_secret` in
`agent/utils/actions.py` now call it right after a successful `input_text`, forcing the IME to
commit/close before any follow-up action can race it.

Existing tests green (`tests/domain/test_action_executor.py`); not tried on a real device.
