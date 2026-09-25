---
author: claude
date: 2026-09-25
---
# Verification code typed with a missing digit

User saw `type "156503"` logged as successful but only `16503` on the phone; twice, missing digit in a different position each time.

## Cause
`AndroidDriver.input_text` sent the whole code as one `adb shell input text "156503"`, i.e. six key events back to back. The app's split code field (one box per digit) moves focus after each digit; an event that arrives before the focus move lands in an already-filled box (max length 1) and is dropped. A race, hence the varying position. The log said "typed successfully" because nothing reads the field back.

## Change
- `tools/driver/android.py`: typing moved into `_send_text` (also removes the duplicated reconnect-retry copy). A short all-digit string (2–8 ASCII digits, `_is_otp_code`) is typed one `input text` call per digit with `OTP_CHAR_DELAY_SECONDS = 0.1` between them; everything else still goes in one command. `StealthDriver` wraps this, so stealth mode gets the same behaviour.
- Tests in `tests/domain/test_android_driver_input.py` (paced per-digit typing, clear-then-digits, non-code strings still one command). Full suite green (1861 passed); not tried on the phone.

## Follow-ups (not done)
- Reading the field back after typing to flag a mismatch.
- The Portal keyboard path (`PortalClient.input_text`) is not used by the driver; not changed.
