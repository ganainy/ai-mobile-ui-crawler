---
author: claude
date: 2026-09-23
---
# Run Stats for CLI runs, screen ids, pre-run warnings

Follow-up to [run 179](2026-09-23-cli-crawl-myfitnesspal.md). The user asked to fix three findings in place.

## Pre-run Warnings (GUI + CLI)
- New `core/pre_run_warnings.py`: `collect_pre_run_warnings(config_manager, device_id)` runs two checks in parallel (~2 s worst case on Windows):
  - Portal not installed / accessibility service off while `ui_parser_mode` is `boost` or `accessibility` (uses `portal.get_portal_status`).
  - `enable_tracing` on, provider `phoenix`, and `phoenix_url` does not answer (`tracing_setup.check_phoenix_reachable`, made public, 1 s timeout).
- CLI `crawl`: prints `Warning: ...` to stderr (stdout stays the JSON stream) and starts the run.
- GUI `_start_crawl`: wait cursor while checking, warnings go to the log, then a Yes/No "Start the crawl anyway?" dialog (default No). Not seen in the real GUI.
- A check that itself fails (adb error) is skipped silently.

## Run Stats saved by CrawlerLoop
- New `core/run_stats_recorder.py` (`RunStatsRecorder`, a `CrawlerEventListener`). `CrawlerLoop(run_stats_repository=...)` adds it and saves once: before the Run Report on success (so the report can use it), in `finally` for errored runs. GUI and CLI both pass a `RunStatsRepository`.
- GUI's own `RuntimeStatsCollector` feeding and `_save_run_stats` removed from `main_window.py` (the live dashboard's `CrawlStatistics` is unchanged).
- Fixed on the way: GUI-saved stats always had Total Steps 0 because they counted `on_step_completed`, which nothing emits. Steps now come from `on_action_timing` (one tool = one step, matching step_logs).
- `run_stats` has no device column, so device info is not recorded (it never was: the GUI's `_device_info` was never set).

## Screen ids
- `CrawlerAgentService` now runs the existing (previously unused) `ScreenTracker` on each decision's screenshot: step_logs `from_screen_id` = screen of the decision's screenshot, `to_screen_id` filled when the next screenshot is identified (`StepLogRepository.set_pending_to_screen`). Emits `on_screen_processed` (the listener method existed; nothing emitted it). `runs.unique_screens` now set from the tracker.
- GUI dashboard counts screens from `on_screen_processed` instead of its own pHash of each screenshot.
- Analysis Bundle's "Unique screens visited" counts from and to ids (the start screen only appears as a from id).
- `most_visited_screen_id` is now persisted when it is a real screen id.
- Screens are matched against all screens in the DB (any run, any app), as `ScreenTracker` was written; a blank/loading screen can match another app's. Fixed later the same day, see [screen matching](2026-09-23-screen-matching.md).

## Verified
- Full suite green. New tests: `tests/core/test_pre_run_warnings.py`, `tests/core/test_run_stats_recorder.py`, `tests/domain/test_crawler_agent_screen_ids.py`, `TestCrawlerLoopRunStats`, `TestCrawlPreRunWarnings`.
- Real CLI run 180 (MyFitnessPal, 5 steps, `boost`): both warnings printed; `stats 180` now shows data (5 steps, 2 unique screens, 5 visits); `runs.unique_screens` = 2; bundle says 2. Screenshots 2-5 were the same sign-up form with different password text (hash distance 1-5), so 2 screens is right.
