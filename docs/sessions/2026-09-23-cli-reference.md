---
author: claude
date: 2026-09-23
---
# CLI reference

User asked where the CLI guide is and whether it is current. There was none beyond README's `### CLI` section, which covered only `crawl` and some of its flags.

- Added `docs/cli.md`, built from each command's `--help` plus the code (config lookup order, secret-key detection, API key env vars).
- README CLI section trimmed to a summary + link; model examples changed from `gemini-1.5-flash` to `gemini-3.8-flash`, the model the user runs.
- `crawler_agent_service.py` and `guided_scenarios_generator.py` now fall back to `gemini-3.8-flash` (was `gemini-1.5-flash`) when `ai_model` is unset. `tests/domain` green.
- Top-level `--help` now ends with a hint to run `COMMAND --help` and read `docs/cli.md` (epilog in `cli/main.py`).
- `portal` command renamed to `a11y-portal` (click group name; module stays `cli/commands/portal.py`), with the crawl warning, Portal manual steps, tests, CONTEXT.md and docs updated. No `portal` alias kept.
- `docs/cli.md`: venv activation note, Quick start (list devices -> list apps -> config set gemini_api_key -> a11y-portal status/enable -> 5-step crawl -> list runs/stats), Windows-only data path, reasoning-mode explained, `author` row dropped at the user's request. README venv path typo fixed.
- Quick start step 4 rewritten: A) install/enable Portal with on-device warnings (Play Protect, accessibility "full control" Allow, restricted settings); B) OmniParser via Replicate key or local Docker. Fixed stale `docs/readmes/` links in README and `docker/omniparser/README.md`. Noticed: `defaults.py` sets `mobsf_api_url` to `http://localhost:8001`, the OmniParser port (MobSF runs on 8000); not changed.
- Quick start step 6 expanded (open report, run folder table, `report` to rebuild) and an optional section for video, PCAPdroid and MobSF. Checked against run 180's folder; the HTML report has no AI reasoning, `steps.jsonl` does.
- Keep `docs/cli.md` in sync when adding CLI commands or flags.
- Doc cleanup: `docs/handoff-2026-09-23.md` (all items done) -> `docs/sessions/2026-09-23-handoff.md`; `docs/logging-audit.md` -> `docs/architecture/readmes/logging-audit.md` (added to its INDEX); deleted root `test_crawler_agent_integration.py` (ad-hoc import-check script outside `tests/`, still named "droidrun"). Kept `docs/Glossary.md` (CLAUDE.md stub); later deleted `run_cli.py` too (duplicate of the `mobile-crawler-cli` console script, needed the install anyway), README/ARCHITECTURE/cli.md updated. Links updated.
