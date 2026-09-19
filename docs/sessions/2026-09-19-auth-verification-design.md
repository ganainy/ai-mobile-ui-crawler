---
author: claude
date: 2026-09-19
---
# Auth, sign-up and verification: design agreed (not implemented)

Grilling session on how the crawler should get past login, email confirmation and phone OTP. Terms added to `CONTEXT.md`: **App Account**, **Verification Challenge**, **Human Fallback**.

## Findings
- Only a global "App Test Credentials" set exists (Settings, `settings_panel.py`); values are pasted into the system prompt (`prompt_builder._get_test_credentials`) and `InputDictionary`. Defaults `testuser` / `Password123` can't log into any real app.
- No sign-up or verification code exists; `specs/013-app-auth-signup` was never finished.

## Decisions
1. Goal: reach screens behind auth for coverage. Sign-up and OTP are a means, not something to analyse.
2. **App Account** is stored per app package, no global fallback. Passwords go in `credential_store`.
3. If no App Account exists, the crawler signs up automatically and saves the created account. If the app logs out later, it logs in again with the saved account. No session snapshots (device not rooted).
4. Email codes and links: a dedicated real Gmail inbox read over IMAP with an app password. Default address is `name+package@gmail.com`, overridable per app.
5. Phone OTP: read SMS over `adb` when the device has a SIM. No SIM: warn the user up front that apps needing a phone number won't work. SIM present but `adb` can't read it: ask the human. Virtual-number APIs rejected (detected as VoIP, unreliable, paid).
6. **Human Fallback** is a checkbox. Configurable timeout (default 5 min), then skip auth and crawl what is reachable, noting it on the run. Off means skip immediately.
7. Authentication is the first Guided Scenario, using new agent tools "get email code" and "get SMS code", with a hard cap on auth attempts.
8. Settings: remove global username and password; keep email, phone and address as "Form Fill Data"; add a "Verification Inbox" group (Gmail address and app password).
9. App Accounts are viewed and edited in the per-app area next to Guided Scenarios.

## Open / next
- No ADR written: nothing here is costly to reverse.
- Implementation not started. Tracked as issues #7 (App Accounts), #8 (Gmail IMAP), #9 (SMS over adb), #10 (Human Fallback), #11 (auth as first Guided Scenario, blocked by the others).
