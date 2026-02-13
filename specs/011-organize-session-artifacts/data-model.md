# Data Model: Organize Session Artifacts

## Database Schema Updates

### Table: `runs`
Added a new column `session_path` to track the root directory of all assets for a specific run.

| Column | Type | Description |
|--------|------|-------------|
| `session_path` | TEXT | Absolute or relative path to the unified session folder. |

### Migration Logic
```sql
ALTER TABLE runs ADD COLUMN session_path TEXT;
```

## Entity: Session Directory

A physical directory structure representing a self-contained crawl session.

### Properties:
- **Identifier**: `run_{ID}_{TIMESTAMP}`
- **Standard Subdirectories**:
    - `screenshots/`
    - `reports/`
    - `data/`
    - `logs/`

## State Transitions
1. **Uninitialized**: No folder exists.
2. **Created**: Root and subdirs created at the start of `CrawlerLoop.run`. `runs.session_path` updated in DB.
3. **Populated**: Components write files to subdirs during/after crawl.
4. **Finalized**: Export and Reports added to the folder.
5. **Deleted**: Entire directory removed via `shutil.rmtree` if run is deleted from UI.
