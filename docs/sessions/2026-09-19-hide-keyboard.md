---
author: claude
updated: 2026-09-19
---
# Hide keyboard before state capture

**Problem:** `type_text` left the keyboard open, so screenshots showed it, OmniParser parsed its keys as elements, and it covered UI.

**Decisions (grilling):** dismiss via BACK only if the IME is shown (`dumpsys input_method` `mInputShown=true`; BACK otherwise navigates); dismiss once before each state capture, not after each `type`; Enter stays agent-controlled; drop the prompt's "keyboard is visible / long press backspace" guidance in favour of `type` with `clear=true`.

**Done:** `DeviceDriver.hide_keyboard` (no-op default), `AndroidDriver.hide_keyboard`, `AndroidStateProvider._dismiss_keyboard` called first in `get_state`, executor prompt text, `tests/domain/test_android_driver_hide_keyboard.py`. Wrappers (Stealth/Recording) pass through via `__getattr__`.

**Not done:** Q5 safety net (drop OmniParser detections inside IME window bounds); no device run; CloudDriver keeps the no-op.
