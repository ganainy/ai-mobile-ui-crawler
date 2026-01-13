# Quickstart: Organized Session Folders

## For Users
After running a crawl, simply go to the **Run History** tab.
Find your run in the table and click the **📂 Open** button in the last column.
A file explorer window will open showing:
- `screenshots/`: All images captured by the AI.
- `reports/`: The PDF summary and MobSF security reports.
- `data/`: The full JSON export of the run.

## For Developers
To get the path for any session artifact:
1. Use `SessionFolderManager.get_session_path(run)`.
2. Use return value to build subfolder paths.

Example:
```python
mgr = SessionFolderManager()
root = mgr.get_session_path(run)
screenshot_dir = os.path.join(root, "screenshots")
```
