# Research: Fix Settings Persistence

**Feature**: 001-fix-settings-persistence  
**Date**: 2026-01-11  
**Status**: Complete

## Summary

This document captures research findings for implementing settings persistence across all selector widgets (DeviceSelector, AppSelector, AIModelSelector) to match the existing SettingsPanel behavior.

---

## Current State Analysis

### What IS Working: SettingsPanel Persistence

The `SettingsPanel` widget correctly implements load/save persistence:

**Load Pattern** (`_load_settings()` called in `__init__`):
- Loads on widget initialization
- Uses `get_secret_plaintext()` for encrypted values (API keys, passwords)
- Uses `get_setting()` for regular values with defaults

**Save Pattern** (`_on_save_clicked()`):
- Saves on explicit "Save Settings" button click
- Uses `set_secret_plaintext()` for sensitive data
- Uses `set_setting()` for regular config values
- Emits `settings_saved` signal after successful save

### What is NOT Persisted: Selector Widgets

| Widget | Has ConfigStore? | Saves on Change? | Restores on Init? |
|--------|------------------|------------------|-------------------|
| DeviceSelector | ❌ No | ❌ No | ❌ No |
| AppSelector | ❌ No | ❌ No | ❌ No |
| AIModelSelector | ❌ No | ❌ No | ❌ No |

These widgets only maintain in-memory state and emit signals on selection change.

---

## Existing Storage Schema

### Regular Settings Table (`user_config`)

| Key | Type | Description |
|-----|------|-------------|
| `system_prompt` | string | Custom AI system prompt |
| `max_steps` | int | Maximum crawl steps |
| `max_duration_seconds` | int | Maximum crawl duration |
| `test_username` | string | Test account username |

### Encrypted Secrets Table (`secrets`)

| Key | Description |
|-----|-------------|
| `gemini_api_key` | Gemini API key (encrypted) |
| `openrouter_api_key` | OpenRouter API key (encrypted) |
| `test_password` | Test account password (encrypted) |

---

## Design Decisions

### Decision 1: Where to Add Persistence Logic

**Options Considered:**

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inject `UserConfigStore` into each selector widget | Self-contained, follows SettingsPanel pattern | More constructor parameters, more coupling |
| B | MainWindow manages persistence centrally | Centralized, uses existing signal infrastructure | MainWindow grows larger |
| C | Hybrid - widgets accept optional config_store | Flexible, backwards compatible | Inconsistent API |

**Decision**: **Option A** - Inject `UserConfigStore` into each selector widget

**Rationale**:
1. Matches the existing SettingsPanel pattern for consistency
2. Each widget is responsible for its own persistence (single responsibility)
3. Widgets can be tested independently with mock config stores
4. Changes are isolated to widget files and their tests

### Decision 2: When to Save

**Options Considered:**

| Trigger | Pros | Cons |
|---------|------|------|
| On selection change | Immediate persistence, no data loss | More DB writes |
| On app close | Single write, efficient | Data loss on crash |
| On explicit save button | User control | Inconsistent UX vs Settings panel |

**Decision**: **Save on selection change**

**Rationale**:
1. Device/App/Model selection is a discrete action that should persist immediately
2. SQLite writes are fast (<1ms typically)
3. User expectation is that selection changes take effect immediately
4. No need for separate "Save" button for each selector

### Decision 3: When to Restore

**Options Considered:**

| Trigger | Approach |
|---------|----------|
| Widget `__init__` | Each widget loads its own last selection |
| MainWindow post-init | Centralized restoration after all widgets created |

**Decision**: **Widget `__init__`** (like SettingsPanel)

**Rationale**:
1. Consistent with SettingsPanel pattern
2. Self-contained - widget doesn't depend on external initialization
3. Simpler testing

### Decision 4: Handling Unavailable Selections

For device/model that may not be available at restore time:

**Decision**: 
- **Device**: Store device_id, attempt to select if device found in refresh
- **App Package**: Store package name, restore to input field (always valid)
- **AI Model**: Store provider + model, restore provider first, then model if available

**Graceful Fallback**:
- If stored device not found: Show in status, don't select anything
- If stored model not found: Show provider, leave model unselected with message

---

## Proposed Storage Keys

### New Keys for Selector Widgets

| Key | Type | Widget | Description |
|-----|------|--------|-------------|
| `last_device_id` | string | DeviceSelector | Last selected device identifier |
| `last_app_package` | string | AppSelector | Last entered/selected app package |
| `last_ai_provider` | string | AIModelSelector | Last selected AI provider |
| `last_ai_model` | string | AIModelSelector | Last selected vision model |

All new keys use regular `user_config` table (not encrypted - no sensitive data).

---

## Implementation Approach

### Pattern to Replicate (from SettingsPanel)

```python
class SelectorWidget(QWidget):
    def __init__(self, config_store: "UserConfigStore", ...):
        super().__init__(...)
        self._config_store = config_store
        self._setup_ui()
        self._load_selection()  # Restore on init
    
    def _load_selection(self):
        """Load previously saved selection from config store."""
        saved_value = self._config_store.get_setting("key", default=None)
        if saved_value:
            self._apply_selection(saved_value)
    
    def _on_selection_changed(self, value):
        """Handle selection change - save and emit."""
        self._config_store.set_setting("key", value, "string")
        self.selection_signal.emit(value)
```

### Files to Modify

1. **DeviceSelector** (`device_selector.py`):
   - Add `config_store` parameter to `__init__`
   - Add `_load_selection()` method
   - Add save call in `_on_device_changed()`

2. **AppSelector** (`app_selector.py`):
   - Add `config_store` parameter to `__init__`
   - Add `_load_selection()` method
   - Add save call in `_on_text_changed()` and `_on_combo_changed()`

3. **AIModelSelector** (`ai_model_selector.py`):
   - Add `config_store` parameter to `__init__`
   - Add `_load_selection()` method
   - Add save calls in `_on_provider_changed()` and `_on_model_changed()`

4. **MainWindow** (`main_window.py`):
   - Pass `user_config_store` to all selector widgets

5. **Tests**: Update tests for all modified widgets

---

## Alternatives Rejected

### Alternative: Use QSettings Instead of SQLite

**Why Rejected**: 
- Already have SQLite infrastructure in UserConfigStore
- QSettings would introduce inconsistency (some settings in SQLite, some in registry/plist)
- UserConfigStore provides encryption for sensitive data

### Alternative: Save on App Close Only

**Why Rejected**:
- Risk of data loss on crash
- Inconsistent with immediate save behavior in SettingsPanel API keys

---

## Dependencies

- No new external dependencies required
- Uses existing `UserConfigStore` class
- Uses existing PySide6 widget patterns

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Device ID changes between sessions | Low | Gracefully show "device not found" message |
| Model deprecated/removed | Low | Show "model unavailable", prompt re-selection |
| Database corruption | Low | Existing fallback to defaults, handled by UserConfigStore |
| Constructor signature change breaks tests | Medium | Update all test fixtures to provide config_store |
