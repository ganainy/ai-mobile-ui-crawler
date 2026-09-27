---
author: claude
updated: 2026-09-27
---
# MobSF: one scan per package build, not per crawl

User request: MobSF analysis is unique per package, so don't redo it every time the same app is crawled again; crawling an app multiple times shouldn't run MobSF more than once (unless the app's build actually changed).

## Design decisions (asked the user)
- Cache key: package + app version, not package name alone — a new app version should still get a fresh scan.
- Override: a persisted Settings checkbox ("Force rescan") plus a `--force-mobsf-rescan` / `--force-rescan` CLI flag, both read into the existing `force_mobsf_rescan` config key (single-run CLI use goes through `ConfigManager.override`, never persisted).

## Implementation
- New `mobsf_scans` table (`infrastructure/database.py`, doc'd in `migrations/012_add_mobsf_scans.sql`) and `MobSFScanRepository` (`infrastructure/mobsf_scan_repository.py`): one row per `(app_package, apk_sha256)`, plus an `app_version_key` ("versionName:versionCode") column for a lookup that doesn't need the APK bytes at all.
- `MobSFManager.perform_complete_scan` now checks the cache twice:
  1. Before pulling anything: if a device APK version is queryable via a cheap `adb shell dumpsys package` call, look up `(package, version_key)` — a hit skips the device pull entirely.
  2. After the APK is on disk (pulled or already-stored): hash it (sha256) and look up `(package, apk_sha256)` — a hit skips upload/scan/poll/report-download.
  A hit copies the cached PDF/JSON into *this* run's `reports/mobsf/` folder (so `RunFolderLayout.find_mobsf_json_report()` and the Run Report keep working unchanged) and returns the cached scorecard dict as `security_score`, so `crawler_loop.py`'s `on_mobsf_finished` / run_stats wiring needed no changes.
  A successful fresh scan writes its own record to the cache afterward.
  `force_mobsf_rescan` (config key, default off) skips both lookups but the sha256 is still computed and still written to the cache.
- `MobSFManager.__init__` gained an optional `mobsf_scan_repository` param (same pattern as `session_folder_manager`); production code leaves it unset and gets one backed by the shared `crawler.db` lazily. Existing unit tests that reach `perform_complete_scan` needed a stub injected (`Mock` with `find_by_version`/`find_by_hash` returning `None`) so they don't touch a real on-disk DB.
- Settings: new "Force rescan" checkbox under MobSF Static Analysis (enabled/disabled with the MobSF checkbox, same as "Automatically run after each successful crawl"). CLI: `crawl --force-mobsf-rescan`, `mobsf-scan RUN_ID --force-rescan`.

## Result
New `tests/infrastructure/test_mobsf_scan_repository.py` (CRUD + conflict-replace + "most recent wins" for the version lookup) and a new `TestMobSFScanCache` class in `tests/infrastructure/test_mobsf_manager.py` (hash-hit reuses report and skips the API entirely, force-rescan bypasses the cache, a fresh scan gets cached, version-hit skips the device pull). Full suite green except the four failures already tracked as pre-existing and unrelated (`stats_dashboard` AttributeError in `tests/ui/test_main_window.py`, stale column index in `tests/ui/test_session_folder_open.py`). Not tried against a real MobSF container or a real device.
