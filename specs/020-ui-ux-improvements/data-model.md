# Data Model & Interfaces

**Feature**: UI/UX Improvements (Branch: `020-ui-ux-improvements`)

## 1. User Configuration (Persistence)

New keys to be added to `UserConfigStore` (SQLite/Settings):

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ui_step_by_step_enabled` | Boolean | `False` | Persists the state of the "Step-by-Step Mode" checkbox. |

## 2. Component Interfaces (Contracts)

### `AsyncOperation` (New Utility Class)

A generic thread wrapper for running blocking tasks without freezing the UI.

```python
class AsyncOperation(QThread):
    """
    Generic worker thread for running a target function in the background.
    """
    # Signals
    started = Signal()
    finished = Signal()
    result_ready = Signal(object)  # Emits the return value of target
    error_occurred = Signal(str)   # Emits error message if exception raised

    def __init__(self, target: Callable, *args, **kwargs):
        """
        :param target: Function to run
        :param args: Positional args for target
        :param kwargs: Keyword args for target
        """
        ...
    
    def run(self):
        """Executes target(*args, **kwargs), handles exceptions."""
        ...
```

### `SettingsPanel` (Refactored Structure)

The public interface remains largely the same (getters/setters), but the internal structure changes to Tabs.

```python
class SettingsPanel(QWidget):
    # Signals
    settings_saved = Signal()

    # Public Methods (Unchanged)
    def get_gemini_api_key(self) -> str: ...
    def get_max_steps(self) -> int: ...
    # ... etc ...
```

### `RunHistoryView` (Layout Contract)

```python
class RunHistoryView(QWidget):
    def set_minimum_visible_rows(self, rows: int):
        """
        Calculates and sets minimum height based on row height * rows.
        """
        ...
```
