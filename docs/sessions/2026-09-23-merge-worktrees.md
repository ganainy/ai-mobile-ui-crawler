---
author: claude
updated: 2026-09-23
---
# Merge worktree branches into main

## What
Merged the committed work of the CLI worktree branches into `main` and pushed to `origin/main` (which was still at ea35408, so #14–#19 went out in the same push):

- `issue-23-device-package-last` (#23)
- `issue-20-stats` (#20)
- `issue-21-list-apps` (#21)
- `issue-22-phase-timing` (#22, committed part only, up to 0d8103e)

## Conflicts
- `cli/commands/crawl.py` (#23): main had moved `_report_docker_autostart` to `cli/docker_autostart_report.py` (#19); kept that move and only added `_LAST` / `_resolve_last`.
- `tests/cli/test_crawl_command.py` (#23): kept both `TestCrawlRunOverrides` and `TestCrawlLastDeviceAndPackage`.
- `cli/main.py` (#20): registered `mobsf_scan`, `scenarios` and `stats`.
- `docs/STATE.md`: kept every branch's entries.
- `docs/code/`: regenerated with `scripts/gen_code_notes.py` after the merges.

## Not merged
- `agents/submodule-fetch-error-fix` (f636e4a, 2026-05-31): only bumps the `external/droidrun` submodule pointer, and main has since removed that submodule (DroidRun internalized as `crawler_agent`). Obsolete.
- `.kilo/worktrees/malachite-blinker` (detached at ea35408): already in main.
- Uncommitted #24 (write step logs) work in the `issue-22-phase-timing` worktree: another session was still working on it.

## Verification
Full suite on the merged tree: 1652 passed, 7 skipped, 1 failed. The failure, `test_gui_icon_path_uses_root_ico`, is an artifact of running from an export at `E:\mm`: it asserts that `mobile-crawler` appears in the checkout path.
