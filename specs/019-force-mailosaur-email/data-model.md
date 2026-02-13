# Data Model: Force Mailosaur for Email Verification

**Feature**: 019-force-mailosaur-email  
**Date**: 2026-01-15

## Overview

This feature primarily involves code deletion and refactoring. The data model changes are minimal - mainly configuration storage for Mailosaur credentials.

## Entities

### MailosaurConfig (Existing)

**Location**: `src/mobile_crawler/infrastructure/mailosaur/models.py`

**Status**: No changes required - already exists

```python
@dataclass
class MailosaurConfig:
    """Configuration for Mailosaur service."""
    api_key: str
    server_id: str
```

**Fields**:
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `api_key` | str | Mailosaur API key | Required, non-empty |
| `server_id` | str | Mailosaur server ID | Required, non-empty |

### Configuration Storage

**Location**: SQLite database via `UserConfigStore`

**New Settings Keys**:
| Key | Type | Description | Source Priority |
|-----|------|-------------|-----------------|
| `mailosaur_api_key` | string | Mailosaur API key | Env > UI |
| `mailosaur_server_id` | string | Mailosaur server ID | Env > UI |

**Removed Settings Keys**:
| Key | Replacement |
|-----|-------------|
| `test_gmail_account` | `test_email` (keep existing) |

## Entity Relationships

```
┌─────────────────────┐
│   UserConfigStore   │
│   (SQLite)          │
├─────────────────────┤
│ mailosaur_api_key   │──────┐
│ mailosaur_server_id │──────┤
│ test_email          │──────┤
└─────────────────────┘      │
                             ▼
                    ┌─────────────────┐
                    │  MailosaurConfig │
                    │  (Runtime)       │
                    ├─────────────────┤
                    │ api_key         │
                    │ server_id       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ MailosaurService │
                    ├─────────────────┤
                    │ get_otp()       │
                    │ get_magic_link()│
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  ActionExecutor  │
                    ├─────────────────┤
                    │ extract_otp()   │
                    │ click_verif...()│
                    └─────────────────┘
```

## State Transitions

Not applicable - this feature does not introduce new stateful entities.

## Validation Rules

### MailosaurConfig Validation

```python
def validate_mailosaur_config(config: MailosaurConfig) -> list[str]:
    """Validate Mailosaur configuration.
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if not config.api_key or not config.api_key.strip():
        errors.append("Mailosaur API key is required")
    
    if not config.server_id or not config.server_id.strip():
        errors.append("Mailosaur Server ID is required")
    
    # Server ID format validation (typically 8 characters)
    if config.server_id and len(config.server_id) < 6:
        errors.append("Mailosaur Server ID appears invalid (too short)")
    
    return errors
```

### Email Validation

The `test_email` field should be a valid Mailosaur email format:
- Pattern: `*@<server_id>.mailosaur.net`
- Example: `test.user@abc12345.mailosaur.net`

## Deleted Entities

The following entities are removed as part of Gmail deletion:

### GmailAutomationConfig (Deleted)
- Was located at: `src/mobile_crawler/infrastructure/gmail/config.py`

### GmailSearchQuery (Deleted)  
- Was located at: `src/mobile_crawler/infrastructure/gmail/config.py`

### Various Gmail classes (Deleted)
- `GmailNavigator`
- `GmailReader`
- `GmailService`
- `AppSwitcher`
- `ClipboardHelper`
