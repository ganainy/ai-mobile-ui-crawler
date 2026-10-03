---
author: claude
updated: 2026-10-03
---
# Google account password setting

Run 206 (Whisk, Google-only sign-in): the agent typed the random sign-up password (`AuthenticationSession._signup_password`) into Google's own "Enter your password" screen. It is not the device Google account's password, so Google rejected it; the sign-up rule "wrong email or password error -> find sign-up" then made the Manager press Back (against the Google no-Back rule) and retry the same flow.

## Change
- New secret `google_account_password` (`GOOGLE_PASSWORD_KEY` in `domain/authentication.py`), entered in Settings > Verification Inbox ("Google account password").
- `AuthenticationSession(google_password=...)`; `google_password_rule()` adds to the goal text: type exactly that password on Google screens, or (if unset) never type the sign-up password, use "Try another way", and do not press Back for a wrong-password error.
- The "wrong email or password" sign-up rule is scoped to the app's own screens.
- The sign-up password for apps is still randomly generated (not changed).

`tests/domain/test_authentication.py` green; no new test; not tried on the phone or in the GUI.
