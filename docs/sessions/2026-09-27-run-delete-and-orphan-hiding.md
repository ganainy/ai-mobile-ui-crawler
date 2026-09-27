---
author: claude
updated: 2026-09-27
---
# GUI run deletion now removes files too; runs with deleted folders disappear from the list

Two gaps in `RunHistoryView` (`ui/widgets/run_history_view.py`):

1. The GUI's "Delete Run" button (and confirmation dialog already existed) only called `RunRepository.delete_run` — DB rows only. The CLI's `delete` command (`cli/commands/delete.py`) already deleted the session folder too via `SessionFolderManager`; the GUI never did, so every GUI delete left screenshots/videos/pcaps/reports orphaned on disk.
2. A run whose folder had been deleted by hand (outside the app) stayed listed with normal-looking rows — only the "Open" button noticed (disabled, "Folder not found" tooltip).

## Changes
- `_on_delete_clicked` now resolves the run's session path via `SessionFolderManager` and calls `delete_session_folder` before deleting the DB row, matching the CLI. A folder delete failure is logged and doesn't block the DB delete (a warning is more useful than blocking the whole action over stray locked files).
- `_load_runs` filters out any run where `run.session_path` is set but `os.path.exists(run.session_path)` is false — i.e. the folder was recorded but is now gone. A run that never had `session_path` recorded (pre-migration data) is left alone; that's a different, older situation than "the user just deleted it," and hiding it would be surprising with no clear cause.

## Tests
`tests/ui/test_run_history_view.py`: `test_delete_removes_session_folder_from_disk` (folder actually removed from a `tmp_path` dir), `test_table_hides_run_whose_recorded_folder_is_gone`, `test_table_keeps_run_whose_recorded_folder_still_exists`, `test_table_keeps_run_with_no_recorded_path`. `MockRunRepository.add_run` gained an optional `session_path` param. Full suite green except four pre-existing, unrelated failures: the two known `stats_dashboard` failures in `test_main_window.py`, and two in `tests/ui/test_session_folder_open.py` (`cellWidget(0, 9)` — stale test still checking the Open button's old column index; it moved to column 15 when the artifact-presence columns landed in `171341e` and this test was never updated. Confirmed pre-existing by stashing this session's changes and re-running against `171341e` directly — not touched here, out of scope).

Not tried in the real GUI.
