---
author: claude
date: 2026-09-23
---
# CLI reference

User asked where the CLI guide is and whether it is current. There was none beyond README's `### CLI` section, which covered only `crawl` and some of its flags.

- Added `docs/cli.md`, built from each command's `--help` plus the code (config lookup order, secret-key detection, API key env vars).
- README CLI section trimmed to a summary + link; model examples changed from `gemini-1.5-flash` to `gemini-3.8-flash`, the model the user runs.
- `crawler_agent_service.py` and `guided_scenarios_generator.py` now fall back to `gemini-3.8-flash` (was `gemini-1.5-flash`) when `ai_model` is unset. `tests/domain` green.
- Keep `docs/cli.md` in sync when adding CLI commands or flags.
- Doc cleanup: `docs/handoff-2026-09-23.md` (all items done) -> `docs/sessions/2026-09-23-handoff.md`; `docs/logging-audit.md` -> `docs/architecture/readmes/logging-audit.md` (added to its INDEX); deleted root `test_crawler_agent_integration.py` (ad-hoc import-check script outside `tests/`, still named "droidrun"). Kept `docs/Glossary.md` (CLAUDE.md stub) and `run_cli.py` (entry point referenced by README/ARCHITECTURE). Links updated.
