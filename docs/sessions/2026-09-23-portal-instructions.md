---
author: claude
date: 2026-09-23
---
# Portal instructions and auto-fix (GUI + CLI)

Item 3 of [handoff-2026-09-23](2026-09-23-handoff.md).

## Checked on the phone (SM-G991B, Android 15, Portal 0.7.25)
- The Portal app's top half is "Connect to Mobilerun": Sign in with Browser / Use API Key / Custom Connection. That is the Mobilerun cloud service. The crawler never uses it, nor the IP/token/ADB forward command under Connection Details: `portal_client.py` uses the content provider over adb and, for TCP, sets up the port forward and fetches the token through the content provider itself. "All Files Access" is also unused.
- "Socket Status: Service not available" = the accessibility service is off. The app has its own "Enable Now" button for it.
- Enabling over adb (`settings put secure enabled_accessibility_services ...`) works on this Samsung without root; `state_full` returned a tree right after.
- Force-stopping Portal (`am force-stop com.mobilerun.portal`) turned the service off again and cleared the setting. Written into the manual steps.
- Left the service **on** on the phone.

## Changes
- `ui/portal_actions.py` moved to `core/portal_actions.py` (Qt-free, now shared with the CLI). New `enable_portal` (enable over adb, wait for the service, overlay off, re-check), `fix_portal` (nothing if ready, enable if installed, install if missing) and `PORTAL_MANUAL_STEPS` (numbered Samsung/Android 15 steps: Accessibility > Installed apps, restricted setting, battery Unrestricted, how to check, and what in the Portal app is not needed).
- `portal.enable_portal_accessibility` now appends Portal to `enabled_accessibility_services` instead of overwriting it (overwriting turned off any other service, e.g. TalkBack). `_wait_for_portal_service` made public.
- Pre-run Warnings return `PreRunWarning(message, portal_fix)` (`"enable"` / `"install"` / None) instead of strings.
- GUI pre-run dialog: "Enable Portal and start" (only when installed but off; blocking ~3 s with a wait cursor), "Start anyway", Cancel; Portal problems get the manual steps under "Show Details". If enabling fails, a warning with the manual steps and the crawl does not start. Not-installed points to Settings' install button (minutes, so not done from the dialog).
- Settings: "Install / enable Portal" runs `fix_portal` (used to always reinstall with uninstall), tooltip updated; the manual steps show under the Portal row while Portal is not ready.
- CLI: `portal status|enable|install --device ID` (exit 1 + manual steps on stderr when not ready). `crawl` prints `Fix: mobile-crawler-cli portal enable --device ID` under a Portal warning.

## Verified
- Tests for all of the above (portal actions, append behaviour, CLI commands, crawl hint, dialog buttons with a stubbed QMessageBox, Settings help label). Full suite green.
- On the phone: `portal status` (ready, exit 0), turned the service off, `portal status` (off, exit 1), `portal enable` (ready, exit 0), content provider returns the a11y tree.
- The GUI dialog and Settings help label not seen in the real GUI.
