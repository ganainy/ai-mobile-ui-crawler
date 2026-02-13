# Data Model

## Entities

### Run

Existing entity. No schema changes.

**Fields**:
- `id`: int (PK)
- `device_id`: str
- `app_package`: str
- `start_time`: datetime
- `end_time`: datetime (nullable)
- `status`: str (Enum-like)
    - Values: `RUNNING`, `STOPPED`, `ERROR`, `COMPLETED`, `INTERRUPTED` (New concept, reuse existing string field)

## Interface Definitions

### SessionFolderManager

```python
class SessionFolderManager:
    ...
    def get_session_path(self, run: Run) -> Optional[str]:
        """
        Resolves the artifact folder path for a given run by matching 
        device/package/timestamp patterns in the base directory.
        Returns absolute path or None if not found.
        """
        pass
```

### StaleRunCleaner

```python
class StaleRunCleaner:
    ...
    def cleanup_on_startup(self) -> int:
        """
        Marks all 'RUNNING' runs as 'INTERRUPTED'.
        Should be called once during application initialization.
        Returns count of fixed runs.
        """
        pass
```
