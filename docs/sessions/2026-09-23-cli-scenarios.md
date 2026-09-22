---
author: claude
updated: 2026-09-23
---
# Issue #18: CLI `scenarios` commands

## What
The GUI's Guided Scenarios group (list editor, website-URL override, Generate button) had no CLI equivalent. New `scenarios` command group in `cli/commands/scenarios.py`, registered in `cli/main.py`.

## Commands
- `scenarios list -p PKG`: numbered list (1-based), plus the URL override if set.
- `scenarios set -p PKG [TEXT]...`: replace the whole list (no TEXT clears it); `--website-url` sets or (empty string) clears the override, and leaves the list alone if no TEXT is given.
- `add [--position N] TEXT`, `edit INDEX TEXT`, `remove INDEX`, `move INDEX NEW_INDEX`: the GUI editor's add / inline edit / remove / move up-down. Out-of-range indexes fail without writing. Blank entries are dropped, as the GUI does on save.
- `scenarios generate -p PKG [--website-url URL]`: calls `generate_guided_scenarios` (same path as the GUI button). Without `--website-url` it uses the saved override. On success it replaces the list and saves list + override (the GUI does the same); on failure the warning goes to stderr, the old list is kept and it exits 1. `--provider`, `--model`, `--exploration-objective` are single-run overrides (`ConfigManager.override()`, not saved), like the matching `crawl` flags.

## Review
- Spec axis: the GUI writes the panel's provider/model/keys/objective into the config before generating, but the CLI only read the saved values, so an objective passed to `crawl --exploration-objective` (not saved) could never reach `generate`. Fixed with the override flags above. Also: exceptions outside the LLM step (e.g. web profile resolution) gave a raw traceback; now a one-line error and exit 1, like the GUI worker's catch.
- Standards axis: a "late import to avoid llama_index" was pointless because the key helpers already import that module; removed. Load/mutate/save repetition across add/edit/remove/move left as is (four short commands).
- Beyond the GUI, kept on purpose: `add --position`, `move` to any index, `set --website-url`.

## Status
23 tests in `tests/cli/test_scenarios_command.py` (real `UserConfigStore` on a temp DB, generator mocked). Full suite green (another session was building #19 `mobsf-scan` in the same tree at the same time; its files are not part of this commit). `generate` not tried against a real LLM / Play Store.
