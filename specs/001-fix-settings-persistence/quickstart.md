# Quickstart: Fix Settings Persistence

**Feature**: 001-fix-settings-persistence  
**Date**: 2026-01-11

## Overview

This guide provides a quick reference for implementing settings persistence across all selector widgets.

---

## Implementation Summary

### Files to Modify

| File | Changes |
|------|---------|
| `src/mobile_crawler/ui/widgets/device_selector.py` | Add `config_store` param, load/save device_id |
| `src/mobile_crawler/ui/widgets/app_selector.py` | Add `config_store` param, load/save app_package |
| `src/mobile_crawler/ui/widgets/ai_model_selector.py` | Add `config_store` param, load/save provider + model |
| `src/mobile_crawler/ui/main_window.py` | Pass `user_config_store` to all selectors |
| `tests/ui/test_device_selector.py` | Add mock config_store fixture |
| `tests/ui/test_app_selector.py` | Add mock config_store fixture |
| `tests/ui/test_ai_model_selector.py` | Add mock config_store fixture |

---

## Implementation Pattern

Follow this pattern for each selector widget (based on existing SettingsPanel):

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mobile_crawler.infrastructure.user_config_store import UserConfigStore

class SelectorWidget(QWidget):
    def __init__(self, ..., config_store: "UserConfigStore", parent=None):
        super().__init__(parent)
        self._config_store = config_store
        # ... existing setup ...
        self._load_selection()  # NEW: restore on init
    
    def _load_selection(self):
        """Load previously saved selection."""
        saved_value = self._config_store.get_setting("last_xxx", default=None)
        if saved_value:
            # Apply the saved value to the widget
            self._apply_saved_selection(saved_value)
    
    def _on_selection_changed(self, value):
        """Handle selection change - existing method, add save."""
        # ... existing logic ...
        # NEW: persist the selection
        self._config_store.set_setting("last_xxx", value, "string")
```

---

## Storage Keys Reference

| Key | Widget | Saved When |
|-----|--------|------------|
| `last_device_id` | DeviceSelector | Device selected from dropdown |
| `last_app_package` | AppSelector | Package entered or selected |
| `last_ai_provider` | AIModelSelector | Provider changed |
| `last_ai_model` | AIModelSelector | Model selected |

---

## Testing Approach

### Test Fixture Pattern

```python
@pytest.fixture
def mock_config_store():
    """Create mock config store with in-memory SQLite."""
    conn = sqlite3.connect(":memory:")
    # Create schema
    conn.execute("""
        CREATE TABLE user_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            value_type TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    # Return mock that wraps the connection
    return MockConfigStore(conn)
```

### Test Cases for Each Widget

1. **Initialization with no saved value** → Widget shows default state
2. **Initialization with saved value** → Widget restores selection
3. **Selection change** → Value persisted to config store
4. **Saved value unavailable** → Graceful fallback, no error

---

## Verification Steps

After implementation, verify with manual testing:

1. **Start app fresh** (delete `user_config.db` if exists)
2. **Select device, app, AI provider/model**
3. **Close app completely**
4. **Restart app**
5. **Verify all selections are restored**

Database location:
- Windows: `%APPDATA%\mobile-crawler\user_config.db`
- macOS: `~/Library/Application Support/mobile-crawler/user_config.db`
- Linux: `~/.local/share/mobile-crawler/user_config.db`

---

## Common Pitfalls

1. **Don't save on every keystroke** for AppSelector - debounce or save on focus loss/enter
2. **Handle missing devices gracefully** - device may not be connected on restore
3. **Load provider before model** for AIModelSelector - model list depends on provider
4. **Update tests** - constructor signature changes will break existing tests
