---
author: claude
updated: 2026-09-23
---
# Issue #19: CLI `mobsf-scan RUN_ID`

## What
The GUI's Run History "Run MobSF" action had no CLI equivalent. `mobile-crawler mobsf-scan RUN_ID` now runs MobSF static analysis on a finished run.

## Difference from the GUI
The GUI's `analyze_run` always pulls a fresh APK from the device over adb. The issue forbids that for the CLI: the command only scans an APK already stored in the run's session folder (`<session>/apks/<package>.apks` split archive, else `<package>.apk`). Those files exist only if MobSF already ran for that run (e.g. `auto_run_mobsf_after_crawl`), because `extract_apk_from_device` is the only thing that writes there. Traffic captures are not used; MobSF static analysis only needs the APK.

## Changes
- `MobSFManager.find_stored_apk(run)`: resolves the session folder (`run.session_path`, else `SessionFolderManager.get_session_path`) without creating folders, returns the stored APK path or None.
- `MobSFManager.perform_complete_scan(..., apk_path=None)`: when given, skips the device pull. `analyze_run` gained `apk_path` and `log_callback` pass-throughs (GUI and crawl loop callers unchanged).
- New `cli/commands/mobsf_scan.py`, registered in `cli/main.py`. Order: run lookup, `enable_mobsf_analysis` check (error says `config set enable_mobsf_analysis true`), stored-APK check, then `ensure_mobsf_running_if_enabled` (#15; failure is a warning), then scan. The cheap checks come first so a missing APK doesn't wait on a Docker start. Progress to stderr, result (hash, JSON, PDF, score) to stdout; any failure exits 1.

## Review fixes
- `find_stored_apk` fell back to `SessionFolderManager` when `run.session_path` was stale, but `analyze_run` didn't, so the APK came from one folder and reports went to the stale one. Both now use `MobSFManager._resolve_session_path` (tested).
- The autostart message helper moved out of `crawl.py` to `cli/docker_autostart_report.py`, and both commands now use it, so they print the same wording.

## Status
Full suite green. No typechecker in `.venv312`. Not tried against a real MobSF container or a real stored run. Results are not persisted to the DB (the GUI doesn't either).
