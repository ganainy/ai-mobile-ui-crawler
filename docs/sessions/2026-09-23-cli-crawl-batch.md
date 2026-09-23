---
author: claude
date: 2026-09-23
---
# CLI: crawl several apps in one command

Goal: give `crawl` a list of apps, run each for a fixed time (e.g. 10 minutes), each as its own run. Settled by a grilling session, then built in worktree `.claude/worktrees/cli-crawl-batch` (branch `worktree-cli-crawl-batch`).

## Decisions
- A batch is a CLI convenience, not a domain concept: nothing stored, no batch id, `CONTEXT.md` unchanged, no ADR.
- `--package` is repeatable on the existing `crawl` command; one `--package` behaves exactly as before (no summary, no device/install checks, no force-stop).
- All apps share the same settings (no per-app overrides).
- Failure policy: an errored or missing app is recorded and the batch goes on; an unreachable device ends it (rest `NOT_RUN`). Exit 1 if any app didn't complete, 130 on Ctrl+C.
- Ctrl+C ends the whole batch; a still-`RUNNING` run is marked `STOPPED` / `user_stop`, a run that had already finished keeps its outcome.
- Previous app is force-stopped before the next starts; app data is not cleared (keeps App Account logins).
- Human Fallback keeps its setting; a stderr warning at batch start when it's on.
- Summary: `batch_completed` JSON event on stdout (`aborted_reason`, `runs[]` with package, run_id, status, stop_reason), readable table on stderr.
- Docker autostart runs once per batch. (The pre-run warnings step from the main checkout isn't in this branch's base, see below.)
- No per-app hard ceiling for hung teardown yet.

## Bug found and fixed
`--duration` was effectively ignored: the CLI saved `max_crawl_duration_seconds`, but `CrawlerLoop` reads `max_duration_seconds` first (the GUI's saved value) and applies it only when `limit_type == "duration"`, which the CLI never set. Same for `--steps` vs `max_steps`. Now `--steps`/`--duration` override `limit_type` plus `max_steps`/`max_duration_seconds`, and are mutually exclusive (usage error). `--model`, `--provider`, `--enable-*`, `--no-report` and the per-run `app_package` also became single-run overrides (`ConfigManager.override`), so CLI runs no longer change the GUI's saved settings.

## How the time limit behaves
`execute_exploration_task` wraps the agent in `asyncio.wait_for(timeout=max_duration)`, so exploration is cancelled at the limit. Teardown (video/pcap stop, MobSF, Run Report) runs after it, so wall-clock per app is duration + teardown. Apps run one after another, so a long app only delays the next. Caveat: a Human Fallback prompt blocks the crawl thread, so it can push past the limit.

## Code
- `cli/crawl_batch.py`: `run_crawl_batch(packages, BatchCrawler)`: ordering, failure and Ctrl+C rules, behind a small protocol.
- `cli/commands/crawl.py`: `_CliCrawler` (real device via `DeviceDetection`, `is_package_installed`, `ADBActionExecutor.force_stop_package`, runs table, fresh `CrawlerLoop` per run), `_report_batch`.
- `infrastructure/installed_apps.py`: `is_package_installed` (`pm path`; raises on adb errors so a lost device isn't read as a missing app).
- Tests: `tests/cli/test_crawl_batch.py`, new classes in `tests/cli/test_crawl_command.py`, `tests/infrastructure/test_installed_apps.py`. Full suite (minus integration) green with `PYTHONPATH=src`.

## Not done / open
- Not tried on a real device.
- Merged into main: conflicts with main's pre-run warnings, `RunStatsRepository` wiring and `--restart-app` resolved by keeping all of them; pre-run warnings run once per batch, and `restart_app_before_run` (default on) also force-stops each target app at run start. Fixes issue #25 (not closed yet).
