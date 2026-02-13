# Research: Force Mailosaur for Email Verification

**Feature**: 019-force-mailosaur-email  
**Date**: 2026-01-15

## Executive Summary

This research consolidates findings for migrating from Gmail UI automation to Mailosaur API integration for email verification in the mobile crawler.

## Research Topics

### 1. Existing Mailosaur Service Capabilities

**Decision**: Use existing `MailosaurService` from `018-integrate-mailosaur` feature.

**Rationale**: The existing service already provides:
- `get_otp(email, timeout)` - Retrieves OTP codes from emails
- `get_magic_link(email, link_text, timeout)` - Retrieves verification links

**Alternatives Considered**:
- Building a new service: Rejected - existing implementation is functional
- Using raw Mailosaur API: Rejected - SDK wrapper is cleaner

**Current Implementation Review**:
```python
# src/mobile_crawler/infrastructure/mailosaur/service.py
class MailosaurService:
    def get_otp(self, email: str, timeout: int = 30) -> str
    def get_magic_link(self, email: str, link_text: Optional[str] = None, timeout: int = 30) -> str
```

### 2. Gmail Service Interface Analysis

**Decision**: Map Gmail service methods to Mailosaur equivalents.

**Current Gmail Interface**:
- `extract_otp(query: GmailSearchQuery, timeout_sec: int)` → Returns OTP string
- `click_verification_link(query: GmailSearchQuery, timeout_sec: int)` → Returns success bool

**Mapping to Mailosaur**:
| Gmail Method | Mailosaur Method | Notes |
|--------------|------------------|-------|
| `extract_otp(query, timeout)` | `get_otp(email, timeout)` | Query simplified to email address |
| `click_verification_link(query, timeout)` | `get_magic_link(email, link_text, timeout)` | Returns URL instead of clicking |

**Key Difference**: Gmail service clicked the link in-app. Mailosaur returns the URL, which must be handled differently (e.g., opened via ADB or used directly).

### 3. ActionExecutor Interface Changes

**Decision**: Modify `ActionExecutor` to accept `MailosaurService` instead of `GmailService`.

**Current Signature**:
```python
def __init__(self, appium_driver, gesture_handler, 
             adb_input_handler=None, gmail_service=None)
```

**New Signature**:
```python
def __init__(self, appium_driver, gesture_handler,
             adb_input_handler=None, mailosaur_service=None)
```

**Method Updates Required**:
1. `extract_otp(sender, subject)` → Use `mailosaur_service.get_otp(email)`
2. `click_verification_link(sender, subject)` → Use `mailosaur_service.get_magic_link(email)` then open URL

### 4. UI Configuration Changes

**Decision**: Replace Gmail-specific UI fields with Mailosaur configuration.

**Fields to Remove**:
- "Test Gmail Account" input

**Fields to Add**:
- "Mailosaur API Key" (password input, stores to `mailosaur_api_key`)
- "Mailosaur Server ID" (text input, stores to `mailosaur_server_id`)
- "Test Email" (text input - can keep existing, rename label)

**Storage Keys**:
- `mailosaur_api_key` - API key (treat as secret)
- `mailosaur_server_id` - Server ID
- `test_email` - Keep existing key for the test email address

### 5. Configuration Environment Variables

**Decision**: Support both UI configuration and environment variables.

**Environment Variables**:
- `MAILOSAUR_API_KEY` - Primary API key source
- `MAILOSAUR_SERVER_ID` - Server ID

**Priority**: Environment variables > UI settings (allows CI/CD override)

### 6. Error Handling Strategy

**Decision**: Translate Mailosaur errors to ActionResult failures.

**Mailosaur Error Types**:
- `MailosaurError` - General API errors
- Timeout when no message found

**ActionResult Mapping**:
```python
try:
    otp = mailosaur_service.get_otp(email, timeout)
    return ActionResult(success=True, input_text=otp)
except ValueError as e:
    return ActionResult(success=False, error_message=str(e))
except Exception as e:
    return ActionResult(success=False, error_message=f"Mailosaur error: {e}")
```

### 7. Files to Delete

**Decision**: Complete removal of Gmail-related code.

**Directories** (recursive deletion):
1. `src/mobile_crawler/infrastructure/gmail/`
   - `__init__.py`
   - `app_switcher.py`
   - `clipboard.py`
   - `config.py`
   - `navigator.py`
   - `reader.py`
   - `service.py`

2. `tests/integration/device_verifier/gmail/`
   - `__init__.py`
   - `email_sender.py`
   - `gmail_auth_verifier.py`
   - `gmail_configs.py`
   - `gmail_navigator.py`
   - `gmail_reader.py`
   - `app_switcher.py`
   - `clipboard_helper.py`

3. `tests/unit/infrastructure/gmail/`
   - `test_gmail_modules.py`

**Single Files**:
4. `tests/integration/test_auth_gmail_e2e.py`

### 8. Spec Directories to Preserve

**Decision**: Keep spec directories as historical reference.

The following spec directories mention Gmail but should NOT be deleted:
- `specs/001-integrate-gmail-auth/`
- `specs/013-app-auth-signup/`  
- `specs/016-auth-e2e-tests/`

These contain planning/design documents, not executable code.

## Implementation Order

1. **Delete Gmail code** - Remove all Gmail-related source and test files
2. **Update ActionExecutor** - Replace GmailService with MailosaurService
3. **Update main_window.py** - Change service initialization
4. **Update settings_panel.py** - Replace Gmail UI with Mailosaur UI
5. **Verify build** - Ensure no import errors
6. **Run tests** - Ensure Mailosaur integration tests pass

## Outstanding Questions

All research questions resolved. No outstanding items.
