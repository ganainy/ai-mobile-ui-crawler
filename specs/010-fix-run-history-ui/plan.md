# Implementation Plan - Fix Run History UI & Add Directory Access

**Branch**: `010-fix-run-history-ui` | **Date**: 2026-01-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-fix-run-history-ui/spec.md`

## Summary

This feature resolves User confusion regarding "zombie" runs (runs that crashed but show as "Running") and improves workflow by allowing direct access to session artifacts. We will implement auto-cleanup of stale runs on application startup and add a "Open Folder" feature to the History UI using fuzzy timestamp matching to locate artifact directories.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: PySide6, SQLite  
**Storage**: `crawler.db` (SQLite), specific folder structure in `output_data/`  
**Testing**: `pytest` for unit/integration logic
**Target Platform**: Windows (Desktop App)  
**Project Type**: Single instance Desktop Application  
**Constraints**: 
- Artifact folders use a timestamp format that defines their identity but isn't explicitly linked in the DB.
- Crawler runs in a thread within the main process; app restart implies all previous runs are dead.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Library-First**: N/A (UI/Infrastructure fix).
- **Test-First**: Will write tests for `StaleRunCleaner` and `SessionFolderManager` heuristics.
- **Simplicity**: Reusing existing `StaleRunCleaner` class but simplifying its logic to match the threading model. avoiding DB schema migration for folder paths by using filesystem heuristics.

## Phase 1: Design & Contracts

### Data Model Changes

No schema changes required. `Run` entity remains as is. 
Status values: `RUNNING`, `STOPPED`, `COMPLETED`, `ERROR`, `INTERRUPTED` (new).

### API / Interface Changes

1.  **`StaleRunCleaner`**
    -   `cleanup_stale_runs()`: Now unconditionally marks "RUNNING" runs as "INTERRUPTED" (assuming single-instance startup).

2.  **`SessionFolderManager`**
    -   `get_session_path(run: Run) -> Optional[str]`: New method to resolve folder path.

3.  **`RunHistoryView`**
    -   New Button: "Open Folder"
    -   Status Display update: Handle `INTERRUPTED` status color/text.

## Phase 2: Implementation Tasks

1.  **Update StaleRunCleaner**:
    -   Remove `psutil` dependency/logic.
    -   Implement simple `UPDATE` query for zombie runs.
    -   Add `INTERRUPTED` status to `Run` model constants/types if needed.

2.  **Integrate Cleanup**:
    -   Instantiate and call `StaleRunCleaner` in `MainWindow` startup sequence.

3.  **Enhance SessionFolderManager**:
    -   Implement `get_session_path` using `glob` and datetime comparison.

4.  **Update RunHistoryView**:
    -   Add "Open Folder" button and logic.
    -   Call `QDesktopServices.openUrl(QUrl.fromLocalFile(path))`.
    -   Handle "Folder not found" errors gracefully.

5.  **Tests**:
    -   Test `get_session_path` with various timestamp deltas.
    -   Test `cleanup_stale_runs` functionality.

## Project Structure

### Documentation (this feature)

```text
specs/010-fix-run-history-ui/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # N/A
├── contracts/           # N/A
└── tasks.md             # Phase 2 output
```

### Source Code

```text
src/mobile_crawler/
├── core/
│   └── stale_run_cleaner.py      # MODIFY: Simplify logic
├── infrastructure/
│   └── session_folder_manager.py # MODIFY: Add get_session_path
│   └── run_repository.py         # MODIFY: Add INTERRUPTED status handling if needed
├── ui/
│   ├── main_window.py            # MODIFY: Call cleaner on startup
│   └── widgets/
│       └── run_history_view.py   # MODIFY: Add Open Folder button
```
