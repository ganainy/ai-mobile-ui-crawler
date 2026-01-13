# Implementation Plan: Organize Session Artifacts

**Branch**: `011-organize-session-artifacts` | **Date**: 2026-01-13 | **Spec**: [specs/011-organize-session-artifacts/spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-organize-session-artifacts/spec.md`

## Summary

The primary requirement is to consolidate all artifacts (screenshots, run exports, MobSF reports) into a single, session-specific directory structure. This ensures that users can easily access all related files for a specific crawl run from the UI. The technical approach involves updating the `SessionFolderManager` to be the source of truth for all storage paths, updating the database schema to store the session path, and refactoring several components (`CrawlerLoop`, `ScreenshotCapture`, `RunExporter`, `MobSFManager`, `ReportGenerator`) to use these dynamic paths.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: PySide6, ReportLab, requests, SQLite3, Appium-Python-Client  
**Storage**: SQLite3 (`runs` table update), Filesystem (Consolidated directory structure)  
**Testing**: pytest  
**Target Platform**: Windows (Desktop GUI Application)  
**Project Type**: single  
**Performance Goals**: Minimal overhead for folder creation and file movement (<100ms per run initialization)  
**Constraints**: Must maintain compatibility with existing runs (graceful fallback)  
**Scale/Scope**: ~100+ runs, each containing 10-100 screenshots and reports  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Rationale |
|------|--------|-----------|
| Library-First | Passed | Logic resides in `infrastructure` and `domain` services. |
| CLI Interface | Passed | Core functionality is usable via repositories and services. |
| Test-First | Passed | Integration tests will verify folder structure creation. |
| Integration Testing | Passed | Required for verifying file movements and UI link correctness. |
| Simplicity | Passed | Uses standard OS file explorer for directory access. |

## Project Structure

### Documentation (this feature)

```text
specs/011-organize-session-artifacts/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/mobile_crawler/
├── core/
│   ├── crawler_loop.py       # Update to use unified session paths
├── domain/
│   ├── report_generator.py   # Update PDF output path
├── infrastructure/
│   ├── session_folder_manager.py # Primary path logic and bug fixes
│   ├── screenshot_capture.py     # Update screenshot save location
│   ├── run_exporter.py          # Update JSON export location
│   ├── mobsf_manager.py         # Update report movement logic
│   ├── database.py              # Update schema (migration)
│   ├── run_repository.py       # Update run creation/update logic
├── ui/
│   ├── widgets/
│   │   ├── run_history_view.py   # Update "Open Folder" button logic
```

**Structure Decision**: Single project structure as per project standard. Logic is distributed across infrastructure (storage/pathing) and domain (orchestration).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| DB Migration | Adding `session_path` to `runs` table | Relying on heuristics (current state) is brittle and fails when files are moved. |
