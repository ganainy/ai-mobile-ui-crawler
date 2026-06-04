# Mobile Crawler Change Memory

Durable agent-maintained memory for `E:\VS-projects\mobile-crawler`. Newest entries first.

## Current Snapshot - 2026-06-04

Project state:
- Mobile Crawler is a Python 3.12 desktop/CLI tool for AI-assisted Android app exploration.
- The active agent runtime is internalized at `src/mobile_crawler/domain/crawler_agent`.
- `CrawlerAgentService` is the Mobile Crawler adapter/service around the internal runtime and imports runtime classes from `mobile_crawler.domain.crawler_agent`.
- The internal workflow class is now `CrawlerAgent`; the old `DroidAgent` symbol/module name has been removed from active source and docs.
- `docs/ARCHITECTURE.md` is the canonical architecture document.
- `.planning` and completed planning artifacts have been removed by design.
- `AGENTS.md` is currently missing from the workspace.
- `CLAUDE.md` is currently deleted in git status; this was not changed by the current doc-memory cleanup work.

Durable documentation:
- `README.md`: user/developer setup, usage, integrations, runtime overview, and documentation-memory rule.
- `docs/ARCHITECTURE.md`: architecture snapshot and runtime/component boundaries.
- `docs/readmes/`: grouped README-style docs other than the root README, including local OmniParser setup and internal crawler-agent notes.
- `.codex/project-memory/CHANGELOG.md`: compact session continuity and decision memory.
- `specs/*`: feature specs/contracts; keep active specs updated, but do not recreate completed planning files just for history.

Current notable features:
- PySide6 GUI and Click CLI entry points.
- Internalized `crawler_agent` runtime with accessibility-first UI parsing and OmniParser fallback.
- OmniParser backend selection supports Replicate and local FastAPI server modes.
- AI Crawler settings are grouped under General, AI Crawler, API Keys, and Integrations.
- App test credentials include address, email, and phone prompt fields.
- Optional MobSF analysis, PCAPdroid capture, screen recording, run history, reporting, logs, and statistics.

Validation baseline:
- For runtime changes, use targeted tests plus `pytest` and `ruff check .` when feasible.
- Documentation-only updates do not require code tests.

Open cleanup notes:
- Decide whether to restore, replace, or intentionally remove `CLAUDE.md`.
- Recreate `AGENTS.md` only if persistent project-wide agent instructions are needed.

## 2026-06-04 - Ran Ruff On Renamed Agent Files

Files touched:
- `src/mobile_crawler/core/crawler_loop.py`
- `src/mobile_crawler/domain/crawler_agent_service.py`
- `src/mobile_crawler/domain/crawler_agent/**/*.py`
- `tests/core/test_crawler_loop.py`
- `tests/core/test_droidrun_crawler_loop.py`
- `tests/domain/test_crawler_agent_service.py`
- `.codex/project-memory/CHANGELOG.md`

What changed:
- Ran Ruff after dev dependencies were installed.
- Applied Ruff auto-fixes to the Python files touched by the `CrawlerAgent`/`CrawlerAgentService` rename.
- Manually fixed remaining scoped Ruff issues in `crawler_agent_service.py`, `crawler_agent/__init__.py`, and the service tests.

Architecture impact:
- Runtime architecture unchanged.
- Background workflow event consumption now explicitly binds the workflow handler into the nested consumer task to satisfy Ruff's loop-variable closure rule.

Decisions:
- Did not run repo-wide auto-fix because Ruff reports a large pre-existing backlog across old specs, tests, and unrelated files.
- Excluded YAML example files from Python Ruff validation after Ruff tried to parse `credentials_example.yaml` as Python when passed explicitly.

Validation:
- Scoped Ruff check passed for the renamed agent/service Python files and related tests.
- `pytest tests/domain/test_crawler_agent_service.py tests/core/test_crawler_loop.py tests/core/test_droidrun_crawler_loop.py` passed: 82 tests, 1 existing collection warning.

Docs updated:
- `.codex/project-memory/CHANGELOG.md`

Follow-ups:
- Decide whether to do a separate repo-wide Ruff cleanup commit for the pre-existing lint backlog.

## 2026-06-04 - Added Crawler Agent Decision Loop README

Files touched:
- `docs/readmes/crawler-agent-decision-loop.md`
- `docs/readmes/INDEX.md`
- `README.md`
- `.codex/project-memory/CHANGELOG.md`

What changed:
- Added a detailed README-style document explaining how `CrawlerAgent` runs in FastAgent mode and Manager/Executor reasoning mode.
- Documented decision inputs, shared runtime state, action dispatch, loop termination, estimated timing costs, and speed/quality tuning levers.
- Linked the new document from the root README and `docs/readmes/INDEX.md`.

Architecture impact:
- Runtime architecture unchanged.
- Documentation now has a focused reference for understanding and tuning the agent decision loop.

Decisions:
- Kept this as a secondary README under `docs/readmes/` instead of expanding the root README further.
- Used estimated timing ranges as practical guidance, not benchmarks.

Validation:
- Documentation update only; no code tests run.
- Ran doc inventory and searched for the new document link.

Docs updated:
- `README.md`
- `docs/readmes/INDEX.md`
- `docs/readmes/crawler-agent-decision-loop.md`
- `.codex/project-memory/CHANGELOG.md`

Follow-ups:
- Add runtime timing metrics per state-capture, Manager LLM, Executor LLM, action execution, wait, and verification phase before making major speed optimizations.

## 2026-06-04 - Renamed Internal Workflow Agent

Files touched:
- `src/mobile_crawler/domain/crawler_agent/agent/droid/crawler_agent.py`
- `src/mobile_crawler/domain/crawler_agent/agent/droid/__init__.py`
- `src/mobile_crawler/domain/crawler_agent/agent/droid/state.py`
- `src/mobile_crawler/domain/crawler_agent/telemetry/events.py`
- `src/mobile_crawler/domain/crawler_agent/telemetry/__init__.py`
- `src/mobile_crawler/domain/crawler_agent_service.py`
- `README.md`
- `docs/ARCHITECTURE.md`
- `.codex/project-memory/CHANGELOG.md`

What changed:
- Renamed the internal workflow class from `DroidAgent` to `CrawlerAgent`.
- Renamed the module from `agent/droid/droid_agent.py` to `agent/droid/crawler_agent.py`.
- Renamed related internal types and telemetry events from `DroidAgentState`/`DroidAgent*Event` to `CrawlerAgentState`/`CrawlerAgent*Event`.
- Updated `CrawlerAgentService` to instantiate and hold `_crawler_agent`.

Architecture impact:
- Runtime behavior unchanged.
- Naming now reflects that Mobile Crawler runs the internalized crawler-agent workflow rather than an external DroidRun agent.

Decisions:
- Kept `DroidConfig` and other broader runtime/config names for now because this request was scoped to the workflow agent identity.
- Kept the `agent/droid/` package path because it still describes the Android/mobile device workflow area.

Validation:
- `pytest tests/domain/test_crawler_agent_service.py tests/core/test_crawler_loop.py tests/core/test_droidrun_crawler_loop.py` passed: 82 tests, 1 existing collection warning.
- Import check passed for `CrawlerAgent`, `CrawlerAgentState`, and `CrawlerAgentService`.
- Search check found no active `DroidAgent`, `droid_agent`, or `_droid_agent` references in source, tests, or docs; historical memory entries still mention the old names as rename context.
- `ruff` was not available on PATH or as `python -m ruff` in the current shell.

Docs updated:
- `README.md`
- `docs/ARCHITECTURE.md`
- `.codex/project-memory/CHANGELOG.md`

Follow-ups:
- Consider later cleanup for remaining broad DroidRun/Droid-prefixed config, DTO, and compatibility labels if the project should remove all inherited terminology.

## 2026-06-04 - Renamed Internal Agent Service

Files touched:
- `src/mobile_crawler/domain/crawler_agent_service.py`
- `src/mobile_crawler/core/crawler_loop.py`
- `tests/domain/test_crawler_agent_service.py`
- `tests/core/test_crawler_loop.py`
- `tests/core/test_droidrun_crawler_loop.py`
- `README.md`
- `docs/ARCHITECTURE.md`
- `.codex/project-memory/CHANGELOG.md`

What changed:
- Renamed the Mobile Crawler adapter from `DroidRunAgentService` to `CrawlerAgentService`.
- Renamed the service module from `droidrun_agent_service.py` to `crawler_agent_service.py`.
- Updated imports, test patches, docs, and memory to use the new service name.

Architecture impact:
- Runtime behavior unchanged.
- Naming now matches the internalized `crawler_agent` runtime instead of implying an external DroidRun bridge.

Decisions:
- Kept runtime DTO names such as `DroidRunGoal`, `DroidRunResult`, and `DroidRunLogHandler` for now because they still describe inherited runtime semantics/log formats.

Validation:
- `pytest tests/domain/test_crawler_agent_service.py tests/core/test_crawler_loop.py tests/core/test_droidrun_crawler_loop.py` passed: 82 tests.
- `ruff` was not available on PATH or as `python -m ruff` in the current shell.

Docs updated:
- `README.md`
- `docs/ARCHITECTURE.md`
- `.codex/project-memory/CHANGELOG.md`

Follow-ups:
- Consider a later deeper terminology cleanup for remaining DroidRun-prefixed DTOs and UI labels.

## 2026-06-04 - Grouped Secondary README Docs

Files touched:
- `README.md`
- `.codex/project-memory/CHANGELOG.md`
- `docs/readmes/INDEX.md`
- `docs/readmes/local-omniparser-setup.md`
- `docs/readmes/crawler-agent-app-cards.md`
- `docs/readmes/crawler-agent-external.md`
- `docs/readmes/spec-017-ui-monitor-improvements-contracts.md`
- `docs/readmes/spec-023-uiautomator-crash-recovery-contracts.md`
- `docs/readmes/spec-024-crawl-stability-fixes-contracts.md`
- `C:\Users\amrmo\.codex\skills\mobile-crawler-doc-memory\scripts\doc_targets.py`

What changed:
- Moved every README-style Markdown file other than the root `README.md` into `docs/readmes/`.
- Added `docs/readmes/INDEX.md` as the folder guide.
- Updated the root README and project memory to point to the grouped folder.
- Updated the doc target helper to track the new local OmniParser setup path.

Architecture impact:
- None.

Decisions:
- Keep root `README.md` as the main project entry point.
- Keep secondary README-style files grouped under `docs/readmes/`.

Validation:
- Documentation update only; no code tests run.

Docs updated:
- `README.md`
- `.codex/project-memory/CHANGELOG.md`
- `docs/readmes/INDEX.md`

Follow-ups:
- None.

## 2026-06-04 - Updated READMEs And Project Memory

Files touched:
- `README.md`
- `docs/readmes/local-omniparser-setup.md`
- `docs/ARCHITECTURE.md`
- `.codex/project-memory/CHANGELOG.md`

What changed:
- Added a current project-state section to the root README.
- Updated the root README to point future state tracking at README, active specs, `docs/ARCHITECTURE.md`, and project memory instead of completed planning docs.
- Refreshed the architecture doc from the old external DroidRun snapshot to the current internalized `crawler_agent` runtime.
- Added current OmniParser integration status to the local setup README.
- Populated this memory file with a current project snapshot for future sessions.

Architecture impact:
- Runtime architecture unchanged.
- Documentation now reflects the existing internalized agent runtime and `docs/ARCHITECTURE.md` as canonical.

Decisions:
- Keep completed planning artifacts removed.
- Use project memory as the compact continuity layer.

Validation:
- Documentation update only; no code tests run.

Docs updated:
- `README.md`
- `docs/readmes/local-omniparser-setup.md`
- `docs/ARCHITECTURE.md`
- `.codex/project-memory/CHANGELOG.md`

Follow-ups:
- Review whether `CLAUDE.md` should remain deleted.

## 2026-06-04 - Removed Implemented Planning Docs

Files touched:
- `.gitignore`
- `.codex/project-memory/CHANGELOG.md`
- `docs/ARCHITECTURE.md`
- `C:\Users\amrmo\.codex\skills\mobile-crawler-doc-memory\SKILL.md`
- `C:\Users\amrmo\.codex\skills\mobile-crawler-doc-memory\scripts\doc_targets.py`

What changed:
- Removed the hidden `.planning` folder and did not keep completed planning artifacts once their work was already implemented.
- Promoted the canonical project architecture document from `.planning/codebase/ARCHITECTURE.md` to `docs/ARCHITECTURE.md`.
- Updated the project doc-memory skill to use `docs/ARCHITECTURE.md`, active specs, README, and change memory instead of durable planning files.
- Removed `.planning/` from `.gitignore`.

Architecture impact:
- Runtime architecture unchanged.
- Canonical architecture documentation path is now `docs/ARCHITECTURE.md`.

Decisions:
- Completed planning files should be removed rather than carried forward as durable documentation.
- Durable outcomes should live in `docs/ARCHITECTURE.md`, active specs, README, and `.codex/project-memory/CHANGELOG.md`.

Validation:
- Verified `.planning` no longer exists after the move.
- Re-ran path searches for stale `.planning` references.

Docs updated:
- `docs/ARCHITECTURE.md`
- `.codex/project-memory/CHANGELOG.md`

Follow-ups:
- Use `docs/ARCHITECTURE.md` for future architecture updates.

## 2026-06-04 - Added Documentation Memory Skill

Files touched:
- `AGENTS.md`
- `.codex/project-memory/CHANGELOG.md`
- `C:\Users\amrmo\.codex\skills\mobile-crawler-doc-memory\SKILL.md`
- `C:\Users\amrmo\.codex\skills\mobile-crawler-doc-memory\references\change-memory-template.md`
- `C:\Users\amrmo\.codex\skills\mobile-crawler-doc-memory\scripts\doc_targets.py`

What changed:
- Created a project-specific Codex skill that keeps Markdown docs, planning state, architecture notes, and durable change memory current after meaningful repo changes.
- Added a repo-local memory file for future session continuity.
- Added AGENTS.md instructions so the repo itself advertises the documentation-memory workflow.

Architecture impact:
- None to runtime architecture.
- Documentation policy now treats `docs/ARCHITECTURE.md` as the canonical project architecture file.

Decisions:
- Reused the explicit Markdown progress-memory pattern found in the local `broad-sysadmin-lab-coach` skill.
- Did not install a curated upstream skill because no matching documentation/architecture-memory skill was found.

Validation:
- Ran `doc_targets.py` against the repo and confirmed documentation inventory output.

Docs updated:
- `AGENTS.md`
- `.codex/project-memory/CHANGELOG.md`

Follow-ups:
- Restart Codex after this session so the new global skill is auto-discovered in future conversations.
