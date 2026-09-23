---
author: claude
date: 2026-09-23
---
# CLI picks the only connected device

**Ask:** `--device` should be optional in the CLI: use the device automatically when exactly one is connected; the flag only matters with several.

**Done:**
- New `cli/device_choice.py`: `resolve_device(device_id)` returns the given id, else the single device from `DeviceDetection.get_available_devices()` (status `device`), printing "Using device X (the only one connected)." on stderr. None connected or several -> `click.UsageError` (exit 2) naming the ids; adb errors -> `ClickException`.
- Used by `crawl` (still accepts `last`), `list apps` (`-d` no longer required) and `a11y-portal status|enable|install`. In `crawl` the lookup runs before the command's catch-all `try`, so a usage error keeps exit 2.
- Tests: `tests/cli/test_device_choice.py`; `list apps` "requires device" test now checks the several-devices case. `tests/cli` green.
- `docs/cli.md` updated (quick start drops `--device`, option tables say when it's needed).

**Not done:** not tried with a real device; code notes regenerate on the next commit. Uncommitted.
- Follow-up: `docs/cli.md` Quick start simplified to 6 steps (no `--device`); run-folder table moved to a new *Run folder* section, OmniParser setup to *Optional features*, Portal install/accessibility troubleshooting to *a11y-portal*; `crawl` examples show `--device` only for the several-devices case.
