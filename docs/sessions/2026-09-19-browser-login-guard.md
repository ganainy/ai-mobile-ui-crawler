---
author: claude
updated: 2026-09-19
---
# Browser login flow killed by target-app guard

**Problem (run 172):** tapping "Log in or create an account" opened Headspace's web login in Brave. `AndroidStateProvider._ensure_target_package_active` saw `current != target` before the next capture and relaunched the app, abandoning the login page (and resetting the terms checkbox). The run also had `max_steps=5`.

**Fix:** `tools/ui/provider.py` now tolerates a known browser (`BROWSER_PACKAGES`) in the foreground for up to `external_grace_captures` (default 8, roughly 2-3 steps) consecutive captures before relaunching. The counter resets when the target is back or after a relaunch. Non-browser foreground packages (launcher etc.) still recover immediately.

**Tests:** two new cases in `tests/domain/test_droidrun_target_package_guards.py` (browser allowed, relaunch after grace exhausted).

**Decisions:** prompt left unchanged on purpose (user: prompt hints would be app-specific). Not verified on a real device. Checkbox-vs-terms-link confusion is untouched. `max_steps=5` is a run setting to raise.

## Follow-up (run 173)
- Grace of 8 captures ran out mid-flow (~3 steps): after typing the email and pressing Go the guard relaunched the app, so the password step was lost and the agent then opened Brave's home page via `open_app`. Default raised to 40 captures.
- Screenshot/overlay mismatch: `ManagerAgent` took its own `driver.screenshot()` *before* `get_state()`. When the guard relaunched the app in between, the report showed the browser image with the welcome screen's elements. Fix: `get_state()` runs first and `UIState.screenshot_bytes` carries the exact image OmniParser parsed; the manager reuses it (falls back to a driver screenshot). This also saves one screenshot per step.
- `open_app` slowness fixed: `AndroidDriver.get_apps` ran `dumpsys package` serially for every installed package (hundreds) on each AppOpener call. Labels are now fetched 16 at a time and cached while the package list is unchanged (`tests/domain/test_android_driver_get_apps.py`). Not timed on a device.

## Run 174: login attempt without saved account
On Headspace's email-first web form the manager saw "Password / Log in" after entering the email and reasoned "maybe the account exists", typed the generated sign-up password and got "Wrong email or password". Fix: the no-App-Account branch of `AuthenticationScenario.goal_section` now says the credentials are for a NEW account only, never to log in with them, and to look for the sign-up option instead. Generic text (no app names). Test: `test_goal_section_signup_when_no_account`. Unrelated pre-existing failure: `test_get_crawler_agent_config` expects manager max_tokens 2048 but HEAD (5907fe9) raised it to 8192.

## Committed
All of the above is in 49c09c1 (plus a `TYPE_CHECKING` import of `PIL.Image` in `driver/android.py` to satisfy ruff F821, and the stale `max_tokens` test fix). The keyboard-hiding edits that appeared in the working tree were another agent's work, committed as 88d4fcf (see [session](2026-09-19-hide-keyboard.md)).
