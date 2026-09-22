---
author: claude
---
# CLI/GUI parity: grilling session

Question: bring the CLI up to date with the GUI, except elements that are inherently GUI-only (scrcpy live feed, screenshots).

## Findings (fact-finding pass, before grilling)
- Both CLI and GUI already share one config store: `UserConfigStore` (SQLite, `<app_data_dir>/user_config.db`), wrapped by `ConfigManager` (precedence SQLite -> `CRAWLER_*` env vars -> `config/defaults.py`). CLI's generic `config set KEY VALUE` / `config get` / `config list` can already reach almost any GUI-set key, including namespaced per-app keys (`app_account::<pkg>`, `guided_scenarios::<pkg>`).
- `max_actions_per_batch` and `a11y_checks` live in a **separate** YAML crawler-agent config, not exposed by either CLI or GUI — not a parity gap, out of scope.
- Pause/Resume is stubbed (no-op) in the GUI too — out of scope.
- `report`'s analysis bundle (`analysis_bundle.py`) already exports per-step AI request/response, tokens, and latency — most of what GUI's AI Monitor Panel shows. The one piece missing: phase-level Timing Breakdown (a11y/OmniParser/LLM sub-durations, validation retries), which lives only in `step_phase_repository` and was never exported.
- Real bug found: `crawl.py` never passes a `human_prompter` to `CrawlerLoop`, so CLI runs silently skip Human Fallback even when enabled in config.
- No CLI command lists installed packages on a device (GUI's AppSelector does, via `adb pm list packages -3`).

## Decisions (user, through grilling)
- Full parity scope: every GUI-configurable behavior should be reachable from the CLI, not just what's needed to run a crawl.
- Delivery: shared config store stays canonical; new `crawl` flags are only added for settings that are commonly tuned per run (not "set once" preferences), and those flags do not persist back to the store.
- One-time audit-and-fix; no ongoing enforcement/guardrail added.
- Human Fallback: fix the wiring so CLI blocks on a terminal prompt (code or skip) when triggered, honoring the existing configured wait-timeout-minutes (auto-skip on expiry). Add `--human-fallback`/`--no-human-fallback`.
- Docker auto-start: `crawl` should auto-start OmniParser/MobSF containers when enabled and not already running (matches GUI), and leave them running after the run finishes (no auto-stop).
- Step-by-step mode: worth building for CLI (user overrode the "skip" recommendation) — `--step-by-step`, pausing after each step with a compact text summary since there's no screenshot board to look at.
- New flags on `crawl`: `--parser-mode`, `--reasoning-mode`, `--exploration-objective` (Streaming Output and Agent Retry Count stay config-store-only).
- New commands: `scenarios generate/list/set` (full CRUD, not just generate), `mobsf-scan RUN_ID` (requires existing captured run data, no fresh APK pull), `stats RUN_ID` (table default, `--format json`), `list apps --device ID`.
- `report` gains the phase-level Timing Breakdown in its analysis bundle.
- `--device last` / `--package last` convenience flags reading the GUI's persisted `last_device_id`/`last_app_package`; no interactive picker (CLI stays scriptable/non-interactive).
- Explicitly staying GUI-only: scrcpy Live Feed, screenshot board with overlay, splitter layout, Open Run Folder, Docker-stop-on-close prompt, Log Viewer's interactive search (CLI output is already greppable).

## Filed as GitHub issues (ready-for-agent)
- #14 Human Fallback wiring + `--human-fallback` flag
- #15 Docker auto-start (OmniParser/MobSF) in `crawl`
- #16 `--step-by-step` mode
- #17 `--parser-mode`/`--reasoning-mode`/`--exploration-objective` flags
- #18 `scenarios generate/list/set` commands
- #19 `mobsf-scan RUN_ID`
- #20 `stats RUN_ID`
- #21 `list apps --device ID`
- #22 Export Timing Breakdown into `report`'s analysis bundle
- #23 `--device last` / `--package last`

Nothing implemented yet — this session was scoping/spec only.
