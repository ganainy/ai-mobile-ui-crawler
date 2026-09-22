---
author: claude
updated: 2026-09-23
---
# Issue #21: CLI `list apps --device ID`

## What
The CLI had no way to find a valid `crawl --package` value short of raw `adb shell pm list packages -3`. `list apps --device ID` now lists the device's third-party packages with their app names, the same enumeration the GUI's AppSelector uses.

## Changes
- New Qt-free `infrastructure/installed_apps.py`: `fetch_third_party_packages_output` (runs `adb -s ID shell pm list packages -3`, raises `RuntimeError` on failure/timeout), `parse_package_list` (valid names only, sorted), `is_valid_package_name`, `list_third_party_packages`. AppSelector's `_fetch_packages` / `_on_list_success` / `_validate_package` now delegate to it (behaviour unchanged, except a missing adb binary now surfaces as `RuntimeError("ADB command failed: ...")` instead of a raw `FileNotFoundError`; both reach the same error dialog).
- `list` command: new `apps` target, `--device/-d` (required for `apps`, `UsageError` otherwise), `--no-names` (skip name resolution). Names come from `AppMetadataResolver` (same as the GUI enrichment, disk-cached; first lookup pulls the APK). Unresolved names show as `-` in the table and `null` in JSON (`[{"package", "name"}]`).
- `--limit` default is now `None`: runs/devices still default to 10, apps list everything unless `-n` is given (limit applied before name resolution).
- `DatabaseManager` is now only created for `list runs`.

## Status
Suite green (1582 passed, 7 skipped). Not tried against a real device.

## Review fixes (before commit)
- `--device` / `--no-names` on `list runs|devices` were silently ignored; now a `UsageError`.
- Name resolution runs serially (possibly an APK pull per app) with no feedback; a "Resolving names for N apps (use --no-names to skip)..." line now goes to stderr first (stdout stays clean JSON).
- Module-level `logger` in `list.py` instead of an in-function `logging` import.
- Not done: `AppMetadataResolver` still extracts/caches icons the CLI never shows (shared resolver, cached, left as is).
