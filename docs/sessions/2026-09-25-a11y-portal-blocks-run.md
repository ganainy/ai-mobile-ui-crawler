---
author: claude
date: 2026-09-25
---
# Portal off blocks the run in accessibility mode

User pasted logs of runs 184 and 185 (Google Fit, CLI).

- Run 184: wireless adb device `adb-RFCR31561LM-...` not found; everything after (PCAPdroid "not installed", video) follows from that. Not a code problem.
- Run 185: the Pre-run Warning said Portal's accessibility service was off (`ui_parser_mode` = `accessibility`), the crawl started anyway, spent ~27 s on traffic capture, video and LLM loading, then `UIStateProvider.get_state` raised at step 1 ("Accessibility mode has no accessibility tree").

## Change
- `PreRunWarning.blocks_run` (default False); the Portal warning sets it in `accessibility` mode only (`boost` falls back to OmniParser, so it stays a warning).
- CLI `crawl`: prints all warnings, then `ClickException("Crawl not started: fix the problem above first.")` if any blocks; no Run is created.
- GUI `_confirm_pre_run_warnings`: no "Start anyway" button when a warning blocks; "Enable Portal and start" and Cancel remain.
- `CONTEXT.md` (Pre-run Warning) and `docs/cli.md` (Portal section) updated.
- Tests: `tests/core/test_pre_run_warnings.py`, `tests/cli/test_crawl_command.py`, `tests/ui/test_main_window.py`; all three files green.

## Follow-ups (same session)
- `android.py` no longer logs "(retrying in 60s)" on a Portal failure: the warning is just the reason; the 60 s Portal cooldown goes to DEBUG. In accessibility mode the provider fails the step right after, so the retry promise was false. Test added in `tests/domain/test_android_driver_accessibility.py`.
- `tests/cli/test_crawl_command.py` defined `TestCrawlPreRunWarnings` twice, so the first class never ran. Renamed it `TestCrawlStartsWithWarnings` and made its test pass `PreRunWarning` objects instead of plain strings; both of its tests now run and pass.
- `tests/core`, `tests/cli`, `tests/ui`, `tests/domain`: 1429 passed.

## Not done
- Not tried on the phone.
