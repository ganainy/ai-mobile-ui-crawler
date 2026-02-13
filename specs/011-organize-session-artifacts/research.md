# Research: Organize Session Artifacts

## Decision: Unified Session Directory Structure

**Chosen Structure**:
```text
output_data/
└── run_{ID}_{TIMESTAMP}/
    ├── screenshots/
    │   ├── step_1.png
    │   └── ...
    ├── reports/
    │   ├── crawl_report.pdf
    │   ├── mobsf_report.pdf
    │   └── mobsf_report.json
    ├── data/
    │   ├── run_export.json
    │   └── session_data.db (optional snippet)
    └── logs/
        └── crawler.log
```

**Rationale**:
- **Consolidation**: All files related to a run are under one parent folder.
- **Portability**: The entire folder can be zipped and shared.
- **Clarity**: Standardized subfolders help the user navigate quickly.

## Investigation: Component Refactoring

### 1. SessionFolderManager (Source of Truth)
- **Fix**: Implement `get_session_folder_path(run_id)` and ensure it's used by all components.
- **Path Storage**: Add `session_path` to the `runs` table to avoid expensive heuristic searches in the UI. Heuristics will be used as a fallback for old runs.

### 2. ScreenshotCapture
- **Current**: Saves to `screenshots/run_{id}/`.
- **Change**: Should accept a `target_directory` in its constructor or `capture_full` method, or resolve it via `SessionFolderManager`.

### 3. RunExporter
- **Current**: Saves to `AppData/Roaming/mobile-crawler/exports/`.
- **Change**: Should save to `{session_root}/data/`.

### 4. MobSFManager
- **Current**: Saves to `tempdir` and then attempts to move (with a bug in method name).
- **Change**: Pass the target `reports` directory directly.

### 5. ReportGenerator (PDF)
- **Current**: Saves to CWD.
- **Change**: Should save to `{session_root}/reports/`.

## Alternatives Considered

| Alternative | Rationale for Rejection |
|-------------|-------------------------|
| Symlinks | Windows support for symlinks requires specific permissions and can be brittle Across different file systems. |
| Single Flat Folder | Too cluttered when there are 100+ screenshots plus multiple reports. |
| Zip-only storage | Harder for users to browse "live" during a crawl. |

## Path Resolution Logic (Proposed)
1. Check `session_path` column in `runs` DB.
2. If null, use `SessionFolderManager.get_session_path(run)` (the existing heuristic method).
3. If still not found, "Open Folder" remains disabled.
