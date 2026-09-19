---
author: claude
date: 2026-09-19
---
# Issue #8: Verification Inbox (Gmail IMAP)

- `infrastructure/verification_inbox.py`: `VerificationInboxReader.wait_for_verification(recipient, since, timeout)` polls Gmail IMAP, returns the newest code and/or link (`VerificationResult`); `InboxAuthError` (bad app password / IMAP disabled), `InboxConnectionError`, `InboxTimeoutError`. `default_signup_address()` builds `name+<package>@gmail.com`; the per-app override is `AppAccount.address_override` (#7). `VerificationInboxStore` keeps address (settings) and app password (secrets).
- Settings > General: new "Verification Inbox" group (`settings_panel.py`); UI change and its tests were left uncommitted because that file also holds uncommitted #6 edits.
- Not yet run against real Gmail; unit tests use a fake IMAP client. Not wired into the agent (that is #11).

## Follow-up
- Committed the reader (9a000f0) and Settings group (a09e36b, built from HEAD plus only the #8 hunks) and pushed to origin/main.
- A failed pre-commit run had stashed the #6 edits; restored with `git apply --3way` from the pre-commit patch.
- Wrote uncommitted fixes for pre-existing failures (finalize helper, None-config guard in `_wire_observers_to_agent`, stale stopping-state test); not re-run. #6 is not committed because the #10 session has staged work in the same tree.
