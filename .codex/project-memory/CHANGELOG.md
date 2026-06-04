# Mobile Crawler Change Memory

Durable agent-maintained memory for `E:\VS-projects\mobile-crawler`. Newest entries first.

## Current Snapshot - 2026-06-04

Project state:
- Mobile Crawler is a Python 3.12 desktop/CLI tool for AI-assisted Android app exploration.
- The active agent runtime is internalized at `src/mobile_crawler/domain/crawler_agent`.
- `DroidRunAgentService` remains the Mobile Crawler adapter/service name, but it imports runtime classes from `mobile_crawler.domain.crawler_agent`.
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
