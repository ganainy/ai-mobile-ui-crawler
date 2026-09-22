---
author: claude
updated: 2026-09-22
---
# Issue #15: CLI auto-start OmniParser/MobSF Docker containers

## What
GUI already auto-starts MobSF/OmniParser Docker containers at launch when enabled (`MainWindow.start_mobsf_if_enabled` / `start_omniparser_if_enabled`); the CLI's `crawl` command never did, so an operator running MobSF or local OmniParser from the CLI had to start the container by hand first.

## Changes
- `MobSFDockerService.prepare()` (`infrastructure/mobsf_docker.py`): new method combining `ensure_running()` + `wait_for_api_key()` + `save_api_key()` — the full startup sequence `MobSFStartupWorker` used to inline. The worker now just delegates to it (`ui/mobsf_startup_worker.py`), so GUI and CLI share one implementation instead of two copies of the same sequence.
- New `infrastructure/docker_autostart.py`: `ensure_mobsf_running_if_enabled(config_manager)` / `ensure_omniparser_running_if_enabled(config_manager)`, blocking equivalents of the GUI's enable-check + start logic (reads `enable_mobsf_analysis` / `ui_parser_mode` / `omniparser_backend` / `omniparser_local_url` from config directly instead of Qt widgets). Each returns `None` when not applicable, else the `(ok, message)` result — deliberately Qt/click-agnostic so the still-unbuilt `mobsf-scan RUN_ID` command (separate issue) can reuse `ensure_mobsf_running_if_enabled` too.
- `cli/commands/crawl.py`: calls both functions after config overrides are applied and before the run starts; `_report_docker_autostart` echoes success/failure (failure is a warning on stderr, not a fatal error — matches GUI, which warns but doesn't block). Containers are left running afterwards (no stop call anywhere), matching GUI and the issue's explicit scope.

## Verification
- New tests: `tests/infrastructure/test_mobsf_docker.py::TestPrepare`, `tests/infrastructure/test_docker_autostart.py`, `tests/cli/test_crawl_command.py::TestCrawlDockerAutostart`.
- Full suite green (`.venv312/Scripts/python.exe -m pytest`, all pass except the 7 pre-existing skips).
- No typechecker is installed in `.venv312` (checked for mypy/pyright, neither present) — skipped that step.
- Not run against real Docker/MobSF/OmniParser containers or a real CLI crawl.

## Code review (Standards + Spec axes, parallel sub-agents)
- Standards: one hard violation (STATE.md/session note not yet written when the review ran — fixed by this note); judgement calls only otherwise (a `tuple[bool, str] | None` tri-state result repeated across 3 call sites; the enable/skip config checks intentionally mirror `main_window.py`'s GUI checks, called out in the module docstring as a deliberate port). Not changed further — both are minor and the duplication is a conscious, scoped choice.
- Spec: all issue requirements implemented correctly (auto-start before crawl, containers left running, logic factored for reuse by the future `mobsf-scan` command, GUI's close-time stop dialog correctly not ported). One real bug found: the auto-start success message was `click.echo`'d to stdout, which `crawl.py`'s `JSONEventListener` treats as a newline-delimited-JSON stream for machine consumers — a plain-text line would break that parsing. Fixed: `_report_docker_autostart` now always writes to stderr (both success and failure), matching the existing convention where `JSONEventListener` owns stdout. Tests updated to assert on `result.stderr`/`result.stdout` separately (Click 8.5's `CliRunner` exposes both).

## Open
- `mobsf-scan RUN_ID` command itself is a separate, not-yet-filed-as-built issue; this change only makes the auto-start reusable for it.
