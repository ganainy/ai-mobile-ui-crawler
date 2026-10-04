---
author: claude
updated: 2026-10-04
---
# Run 216 (app.vera.prod): black screenshot, Developer Options, ADB drop

## What the run showed
- Step 1 screenshot was fully black (app blocks capture); Portal a11y tree still worked (19 nodes). OmniParser then spent 149 s on the black frame and failed.
- The app showed an integrity screen demanding Developer Options off. The agent opened Settings and tapped the master "Use developer options" toggle; the wireless ADB link (`172.20.10.6:39107`) dropped. The trace ends at "attempting to reconnect"; the run stayed `RUNNING` in `crawler.db` (end_time null). Why it never closed is not known (reconnect probably hung; the process may have been killed).

## Changes
- New `domain/crawl_blockers.py`: `CrawlBlockedError` (kinds `screenshot_blocked`, `device_lost`), `is_blank_screenshot`, `find_crawl_blocked_error`, `SETTINGS_PACKAGES`.
- `AndroidStateProvider`: first capture black (re-read once after 1.5 s) or third black capture in a row raises `CrawlBlockedError`; a black frame in between skips OmniParser and uses the a11y tree. `omniparser` mode raises on a black frame. Foreground = Settings package: no grace, target app relaunched at once.
- `AndroidDriver._handle_connection_drop`: `adb connect` and reconnect now time out (20 s); a failed reconnect raises `device_lost` instead of the raw error.
- `CrawlerAgentService` returns a failed result with `crawl_blocked_kind` (no transient retry / relaunch); `CrawlerLoop` emits `on_error`; `MainWindow._on_run_error` shows a dialog.
- Goal text: "DEVICE SETTINGS ARE OFF LIMITS" rule.
- Tests: `tests/domain/test_crawl_blockers.py`, updated `test_android_driver_reconnection.py`.

## Follow-up: run 217
- The Settings guard worked: the app's own "open developer settings" retry button opened Settings (steps 1 and 7), and the next capture returned to the app at once (12:43:15, 12:45:18); the agent never acted inside Settings.
- The black-screenshot check did NOT fire: the frames are black except the Samsung edge-panel handle (0.2% of pixels), and the first version required every pixel black. Now blank = under 1% of pixels brighter than luminance 8; verified true on runs 216 and 217 screenshots.
- Agent kept probing the integrity screen (retry, help toggle, BSI info) for 8 steps before the user stopped it.

## Correction (user, runs 216-218)
- The real cause of the integrity screen was that the device had **no screen-lock PIN**; the app's on-screen text still said Developer Options must be off, so that message is misleading (my first diagnosis took it at face value). The blocked-screenshot message and goal rule no longer name Developer Options as the cause.

## Not done / unverified
- Not tried on the phone or in the GUI. Stale `RUNNING` runs from a killed process are still not swept at startup (two processes could be live, so left alone).
- Batch crawl does not abort on these errors yet.
- Pre-existing failures in the full run (identical with changes stashed): 2 in `test_portal_actions.py` (only when run after other tests), 3 in `test_main_window.py`, 2 in `test_session_folder_open.py`.
