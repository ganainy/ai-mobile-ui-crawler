---
author: claude
updated: 2026-09-25
---
# Permission dialogs killed by target-app guard

**Problem:** crawling Strava, the log showed `Target app mismatch before state capture (current=com.google.android.permissioncontroller, target=com.strava)`. `AndroidStateProvider._ensure_target_package_active` only tolerated browsers (see [browser login guard](2026-09-19-browser-login-guard.md)); any other foreground package was relaunched over at once. Relaunching over a runtime permission prompt cancels it (Android counts that as a denial), so the agent never saw the dialog, the app ran with the permission denied, and could re-ask and loop.

**Fix:**
- `tools/ui/provider.py`: new `SYSTEM_DIALOG_PACKAGES` (`com.google.android.permissioncontroller`, `com.android.permissioncontroller`, `com.android.packageinstaller`, `com.google.android.packageinstaller`, `com.google.android.gms` for the account picker / Smart Lock). Tolerated for `system_dialog_grace_captures` (default 5) consecutive captures, same counter as browsers (which keep their 40). Log line now says "browser" or "system dialog".
- Exploration goal (`crawler_agent_service._create_exploration_goal`) gains a generic PERMISSION DIALOGS paragraph: answer at once with "While using the app" / "Only this time" / "Allow"; dismiss a Google account picker unless using Google sign-in on purpose.
- Executor prompt (`config/prompts/executor/system.jinja2`) said to close permission requests with "Don't Allow"; now says to allow them, matching the goal.

**Tests:** `tests/domain/test_droidrun_target_package_guards.py` (dialog packages captured without relaunch; relaunch after grace), `tests/domain/test_crawler_agent_service.py` (goal carries the permission paragraph). Full suite green (1867 passed). Not tried on the phone.

**Not done:** pre-granting permissions (`adb install -g` / `pm grant`) as an opt-in run setting was discussed and left for later.
