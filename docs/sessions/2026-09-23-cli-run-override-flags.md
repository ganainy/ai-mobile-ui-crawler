---
author: claude
updated: 2026-09-23
---
# Issue #17: crawl --parser-mode / --reasoning-mode / --exploration-objective

## What
First-class `crawl` flags for three settings that were reachable only through `config set`, as single-run overrides that must not persist.

## Changes
- `ConfigManager.override(key, value)` (`config/config_manager.py`): in-memory, per-instance values checked before SQLite/env/defaults in `get()`; never written to the store. Every reader in the run path (`CrawlerLoop`, `CrawlerAgentService`, `docker_autostart`, guided scenarios generator, config snapshot) reads through the same `ConfigManager` instance, so they all see the override.
- `cli/commands/crawl.py`: `--parser-mode {accessibility,boost,omniparser}` -> `ui_parser_mode`, `--reasoning-mode/--no-reasoning-mode` (tri-state, default = configured) -> `crawler_reasoning_mode`, `--exploration-objective TEXT` -> `exploration_objective`. Applied before Docker auto-start, so `--parser-mode accessibility` also skips starting OmniParser.

## Finding
The issue says the flags should behave "consistent with how `--steps`/`--duration` already behave", but those (and `--provider`, `--model`, `--enable-*`, `--no-report`) actually call `config_manager.set`, i.e. they DO persist to the SQLite store and leak into later GUI/CLI runs. Not changed here (out of scope); `override()` is the tool to fix them if wanted.

## Verification
- New tests: `tests/config/test_config_manager.py::TestRunOverrides`, `tests/cli/test_crawl_command.py::TestCrawlRunOverrides`.
- Full suite green. No typechecker in `.venv312`. Not tried in a real crawl.

## Code review
- Spec axis: nothing missing or out of scope; confirmed all run-path readers share the one `ConfigManager` and the GUI uses the same keys. Notes: `--exploration-objective ""` hides a stored objective for that run (left as is); the run config snapshot records `ui_parser_mode` but not reasoning mode / objective (pre-existing gap, possible follow-up).
- Standards axis (judgement calls): parser-mode list now exists in three places (CLI choice, settings panel, agent config comment); `--human-fallback` still uses a separate constructor override rather than `override()`; `_run` patch-stack helper is duplicated across test classes. Fixed: store fixture closes on failure, single `_run` return shape, unknown-mode test checks the message, redundant `.lower()` removed.
