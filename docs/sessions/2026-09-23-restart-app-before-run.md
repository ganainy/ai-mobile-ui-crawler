---
author: claude
date: 2026-09-23
---
# Restart the app before each run

Item 2 of [handoff-2026-09-23](2026-09-23-handoff.md). Run 180 started on the sign-up form that run 179 left open.

## Changes
- New config key `restart_app_before_run` (default True, `config/defaults.py`).
- `CrawlerAgentService._ensure_target_app_active_before_crawler(app_package, force_restart=...)`: with the key on, calls `ADBActionExecutor.force_stop_package` first, then launches the app as before (the "already active" early return now only happens when the key is off, since the app is no longer in front after the stop). A failed force-stop is logged as a warning and the launch goes ahead.
- Only the first launch restarts; the crash/transient retry loop in `execute_exploration_task` resumes without force-stopping again.
- Force-stop keeps app data (login, half-finished sign-up survive; the app just starts at its launch screen). `pm clear` was not added (destructive; ask first).
- GUI: "Restart the app before each run" checkbox under Crawl Limits in Settings (tooltip explains data is kept); saved/loaded/reset.
- CLI: `crawl --restart-app/--no-restart-app`, single-run override via `ConfigManager.override()`, not persisted.
- Config snapshot records `restart_app_before_run`.

## Verified
- Tests: force-stop called before launch when on, not called when off; CLI flags override without persisting; settings default on + save/reload; snapshot key; defaults key/type. Full suite green.
- Not tried on the phone.
