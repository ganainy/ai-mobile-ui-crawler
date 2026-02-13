# Phase 0 Requirements & Research

## Technical Context

**Language/Version**: Python 3.11
**Primary Frameworks**: PySide6 (UI), SQLite (Storage), Appium (Automation)
**Storage**: SQLite (`crawler.db`) + File System (`output_data/{device}_{pkg}_{date}`)
**Project Type**: Desktop Application (Windows target)
**Stale Detection**: `StaleRunCleaner` class exists but is unused. Current logic is flawed (uses `psutil` to check for *any* python process).
**Session Storage**: `SessionFolderManager` creates folders like `{device}_{pkg}_{timestamp}`. The timestamp is not stored in the DB `runs` table, making exact reconstruction difficult without heuristics.

## Research Findings

### 1. Stale Run Detection
- **Current State**: `StaleRunCleaner` is implemented in `core/stale_run_cleaner.py` but never instantiated or called. Its `_is_process_running` method returns `True` if *any* python process with "mobile_crawler" in cmdline is running (which includes the UI itself).
- **Issue**: This causes runs to appear "RUNNING" even after a crash, because the UI restart satisfies the "process running" check.
- **Decision**: 
    - Modify `StaleRunCleaner` to be invoked on Application Startup (in `MainWindow` or `AppContext`).
    - Change logic: On startup of the UI, *before* any new crawl is initiated, ALL runs marked as `RUNNING` are definitionally stale (since the crawler logic runs in the same process/threads as the previous session which must have died).
    - Exception: If the architecture changes to multi-process (worker process), this assumption fails. But currently `CrawlerLoop` runs in a thread (`threading.Thread`). Thus, if the App/UI restarts, all threads are gone.
    - **Proposed Fix**: simple `UPDATE runs SET status='INTERRUPTED' WHERE status='RUNNING'` on app launch.

### 2. Opening Session Directory
- **Current State**: `Run` object has `id`, `start_time` (datetime), `device_id`, `app_package`.
- **Folder Logic**: `output_data/{device_id}_{app_package}_{dd}_{mm}_{HH}_{MM}`.
- **Issue**: `SessionFolderManager` uses `datetime.now()` which might differ slightly from `Run.start_time` stored in DB.
- **Decision**: 
    - Implement `SessionFolderManager.get_session_path(run: Run) -> Optional[str]`.
    - Use `glob` to find folders matching `{device_id}_{app_package}_*`.
    - Parse timestamps from folder names and find the one closest to `Run.start_time` (within small delta, e.g. 1 minute).
    - If found, return path.
    - Add "Open Folder" button in `RunHistoryView` that calls this.

### 3. UI Display for Incomplete Runs
- **Current State**: `RunHistoryView` sets "N/A" for missing end time.
- **Decision**: 
    - Enhance `RunHistoryView` to show "Incomplete" or "Interrupted" in Status column if `status == 'RUNNING'` (and we know it's not the active run).
    - Or rely on the Startup Cleanup to fix the status in DB, so UI just shows "INTERRUPTED". This is cleaner.

## Plan Strategy

1.  **Backend**:
    -   Update `StaleRunCleaner` to simply mark all RUNNING runs as INTERRUPTED (since we are single-instance/threaded).
    -   Invoke `StaleRunCleaner.cleanup_stale_runs()` in `MainWindow.__init__` or `RunRepository` initialization.
    -   Add `get_session_folder(run)` to `SessionFolderManager`.

2.  **Frontend (RunHistoryView)**:
    -   Add "Open Folder" button.
    -   Connect button to `QDesktopServices.openUrl` (standard Qt way to open files/folders).
    -   Refresh table after cleanup to ensure correct status is shown.
