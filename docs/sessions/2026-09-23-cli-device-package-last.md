---
author: claude
date: 2026-09-23
issue: 23
---
# CLI: `crawl --device last` / `--package last` (#23)

Worked in git worktree `.claude/worktrees/issue-23` (branch `issue-23-device-package-last`, from `d150245`) because the main checkout had another session's uncommitted `crawl.py` changes.

## What changed
- `src/mobile_crawler/cli/commands/crawl.py`: `_resolve_last(value, config_manager, key, option)` returns the value unchanged unless it is the literal `last`, in which case it reads `key` from `config_manager.user_config_store` (same store and keys the GUI's `DeviceSelector` / `AppSelector` write). Called right after `create_schema()`, so the resolved values feed the run record and the `app_package` config override. Missing/empty key raises `ValueError`, reported as `Error starting crawl: --device last: no saved 'last_device_id' ...` on stderr, exit 1, before a run is created.
- `--device` / `--package` help text mentions `'last'`.
- README: example line.
- Tests: `TestCrawlLastDeviceAndPackage` in `tests/cli/test_crawl_command.py` (written first, red, then green).

## Decisions
- Store read directly via `user_config_store.get_setting` (like the GUI), not `ConfigManager.get`, so a `CRAWLER_LAST_DEVICE_ID` env var doesn't leak in.
- CLI does not persist `last_*` after an explicit run: the issue only asks for reading. Worth a follow-up if the CLI should update them too.
- `last` is matched case-sensitively.

## Not done
- No typechecker in `.venv312`.
- Not tried against a real saved config / device.
