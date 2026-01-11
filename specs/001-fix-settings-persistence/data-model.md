# Data Model: Fix Settings Persistence

**Feature**: 001-fix-settings-persistence  
**Date**: 2026-01-11  
**Status**: Complete

## Overview

This feature extends the existing `user_config.db` SQLite database schema with additional keys for persisting selector widget state. No schema changes are required - only new key-value entries in existing tables.

---

## Existing Schema (No Changes Required)

### Table: `user_config`

Stores non-sensitive configuration values.

| Column | Type | Description |
|--------|------|-------------|
| `key` | TEXT PRIMARY KEY | Setting identifier |
| `value` | TEXT | Setting value (serialized) |
| `value_type` | TEXT NOT NULL | Type hint: 'string', 'int', 'float', 'bool', 'json' |
| `updated_at` | TEXT NOT NULL | ISO 8601 timestamp |

### Table: `secrets`

Stores encrypted sensitive values.

| Column | Type | Description |
|--------|------|-------------|
| `key` | TEXT PRIMARY KEY | Secret identifier |
| `encrypted_value` | BLOB NOT NULL | Fernet-encrypted value |
| `updated_at` | TEXT NOT NULL | ISO 8601 timestamp |

---

## New Configuration Keys

### Added to `user_config` Table

| Key | Value Type | Default | Description |
|-----|------------|---------|-------------|
| `last_device_id` | string | None | Device identifier (e.g., "279cb9b1") |
| `last_app_package` | string | None | Android package name (e.g., "com.example.app") |
| `last_ai_provider` | string | None | AI provider ID (e.g., "gemini", "openrouter") |
| `last_ai_model` | string | None | Model identifier (e.g., "models/gemini-2.0-flash") |

**Note**: No new secrets table entries needed - selector widget values are not sensitive.

---

## Entity Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                         user_config.db                          │
├─────────────────────────────────────────────────────────────────┤
│  user_config table                                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Settings Panel (existing)                               │    │
│  │   • system_prompt                                       │    │
│  │   • max_steps                                           │    │
│  │   • max_duration_seconds                                │    │
│  │   • test_username                                       │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ Selector Widgets (NEW)                                  │    │
│  │   • last_device_id          ← DeviceSelector            │    │
│  │   • last_app_package        ← AppSelector               │    │
│  │   • last_ai_provider        ← AIModelSelector           │    │
│  │   • last_ai_model           ← AIModelSelector           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  secrets table                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Encrypted Credentials (existing, no changes)            │    │
│  │   • gemini_api_key                                      │    │
│  │   • openrouter_api_key                                  │    │
│  │   • test_password                                       │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Validation Rules

### `last_device_id`
- **Format**: Non-empty string, typically alphanumeric
- **Constraint**: None (device may not exist at restore time)
- **Behavior on Invalid**: Ignored, widget shows default "no device" state

### `last_app_package`
- **Format**: Valid Android package name pattern (`[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+`)
- **Constraint**: None (app may not be installed)
- **Behavior on Invalid**: Shown in input field for user to correct

### `last_ai_provider`
- **Format**: One of: `"gemini"`, `"openrouter"`, `"ollama"`
- **Constraint**: Must be a known provider ID
- **Behavior on Invalid**: Ignored, widget shows "Select a provider..."

### `last_ai_model`
- **Format**: Model identifier string (provider-specific format)
- **Constraint**: None (model may be deprecated/unavailable)
- **Behavior on Invalid**: Provider selected, model shows as unavailable

---

## State Transitions

### Device Selection State

```
┌─────────────┐     User selects      ┌─────────────┐
│  No Device  │ ──────────────────▶   │  Device     │
│  Selected   │                       │  Selected   │
└─────────────┘                       └─────────────┘
       │                                     │
       │ App starts                          │ App starts
       │ (no saved ID)                       │ (with saved ID)
       ▼                                     ▼
┌─────────────┐                       ┌─────────────┐
│  Load empty │                       │  Load saved │
│  state      │                       │  device_id  │
└─────────────┘                       └─────────────┘
                                             │
                         ┌───────────────────┴───────────────────┐
                         │                                       │
                         ▼                                       ▼
                  ┌─────────────┐                         ┌─────────────┐
                  │ Device found │                         │ Device not  │
                  │ → Select it  │                         │ found       │
                  └─────────────┘                         └─────────────┘
                                                                 │
                                                                 ▼
                                                          ┌─────────────┐
                                                          │ Show status │
                                                          │ "not found" │
                                                          └─────────────┘
```

### AI Model Selection State

```
┌──────────────┐    Provider     ┌──────────────┐    Model       ┌──────────────┐
│  No Provider │ ───changed───▶  │  Provider    │ ───changed───▶ │  Model       │
│  Selected    │                 │  Selected    │                │  Selected    │
└──────────────┘                 └──────────────┘                └──────────────┘
       │                                │                               │
       │ Save: None                     │ Save: provider               │ Save: model
       │                                │                               │
       └────────────────────────────────┴───────────────────────────────┘
                                        │
                                        ▼ On restore
                              ┌──────────────────┐
                              │ Load provider,   │
                              │ then load model  │
                              └──────────────────┘
```

---

## Migration

No migration required. The existing `user_config` table schema supports arbitrary key-value pairs. New keys are simply inserted on first save.

---

## Data Lifecycle

| Event | Action |
|-------|--------|
| Widget selection change | INSERT OR REPLACE into user_config |
| App startup | SELECT from user_config, restore if found |
| Widget cleared | DELETE from user_config OR set to empty string |
| App uninstall | Database file deleted (platform handles) |

---

## Performance Considerations

| Operation | Expected Time | Notes |
|-----------|---------------|-------|
| Single key read | <1ms | SQLite is fast for key-value lookups |
| Single key write | <5ms | With WAL mode, writes are async |
| All keys read (startup) | <10ms | 8-10 keys total |

No performance concerns for this feature.
