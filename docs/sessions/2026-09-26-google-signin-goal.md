---
author: claude
updated: 2026-09-26
---
# Google-only sign-in (run 198, Flow)

Run 198 (`com.google.android.apps.labs.whisk`, Google Sign-In only): the agent called `skip_authentication` on the account picker, pressed Back on Google Play services screens (cancelling sign-in and leaving the app), tapped "Continue as Amri" but then backed out of the consent screen, and finally tapped "Sign out". Only 13 steps in 600 s (Manager calls 13-55 s each).

Fix (prompt text only): `_GOOGLE_SIGN_IN_RULE` in `domain/authentication.py` is added to both the sign-up and log-in goal sections (use the device Google account, accept consent screens, never Back on them, never `skip_authentication` while a picker is showing, never Sign out); the PERMISSION DIALOGS text in `crawler_agent_service.py` no longer says to dismiss the account picker during sign-in; `skip_authentication` tool description warns the same. Test added in `tests/domain/test_authentication.py`.

Not done: a code guard in `skip_authentication` (needs the foreground package), the gms recovery logic, and step speed. Not tried on the phone.
