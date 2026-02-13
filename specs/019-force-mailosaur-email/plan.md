# Implementation Plan: Force Mailosaur for Email Verification

**Branch**: `019-force-mailosaur-email` | **Date**: 2026-01-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/019-force-mailosaur-email/spec.md`

## Summary

This feature replaces the Gmail-based email verification system (which used Appium UI automation of the Gmail Android app) with the Mailosaur API-based service. The primary goal is to:
1. Completely remove all Gmail-related code and tests
2. Update all system components to use `MailosaurService` for OTP and magic link extraction
3. Update UI configuration to support Mailosaur credentials

This is a **breaking change** with no backward compatibility - Mailosaur becomes the exclusive mechanism for email verification.

## Technical Context

**Language/Version**: Python 3.11+ (Project Standard)  
**Primary Dependencies**: mailosaur (SDK), PySide6 (GUI)  
**Storage**: SQLite via existing UserConfigStore  
**Testing**: pytest (unit and integration tests)  
**Target Platform**: Windows (primary), Linux (secondary)  
**Project Type**: Single desktop application with GUI  
**Performance Goals**: OTP/link extraction < 30 seconds (network dependent)  
**Constraints**: Requires Mailosaur account with API key and Server ID  
**Scale/Scope**: Single-user desktop application

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution is a template placeholder. Following standard software engineering practices:

- [x] **Test Coverage**: Integration tests will verify Mailosaur service functionality
- [x] **Simplicity**: Direct API integration (Mailosaur) is simpler than UI automation (Gmail)
- [x] **Clean Code**: Removing Gmail code eliminates complex Appium-based automation
- [x] **Documentation**: This plan documents the migration approach

**Gate Status**: ✅ PASS - Proceeding with Phase 0 research

## Project Structure

### Documentation (this feature)

```text
specs/019-force-mailosaur-email/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/mobile_crawler/
├── infrastructure/
│   ├── mailosaur/           # KEEP - Existing Mailosaur service
│   │   ├── __init__.py
│   │   ├── models.py        # MailosaurConfig dataclass
│   │   └── service.py       # MailosaurService class
│   └── gmail/               # DELETE - Entire directory
├── domain/
│   └── action_executor.py   # MODIFY - Replace GmailService with MailosaurService
├── ui/
│   ├── main_window.py       # MODIFY - Remove Gmail initialization, add Mailosaur
│   └── widgets/
│       └── settings_panel.py # MODIFY - Replace Gmail config with Mailosaur config

tests/
├── integration/
│   ├── device_verifier/
│   │   └── gmail/           # DELETE - Entire directory
│   ├── test_auth_gmail_e2e.py  # DELETE - File
│   └── test_mailosaur_e2e.py   # KEEP - Existing Mailosaur tests
└── unit/
    └── infrastructure/
        └── gmail/           # DELETE - Entire directory
```

**Structure Decision**: Maintain existing project structure. This is primarily a deletion and refactoring task, not a structural change.

## Migration Strategy

### Phase 1: Code Removal

Files/directories to delete:
1. `src/mobile_crawler/infrastructure/gmail/` - Entire directory (7 files)
2. `tests/integration/device_verifier/gmail/` - Entire directory (5+ files)
3. `tests/unit/infrastructure/gmail/` - Entire directory
4. `tests/integration/test_auth_gmail_e2e.py` - Single file

### Phase 2: Code Modification

Files requiring updates:

1. **`action_executor.py`**: 
   - Replace `GmailService` import with `MailosaurService`
   - Update `extract_otp()` to call `MailosaurService.get_otp()`
   - Update `click_verification_link()` to use `MailosaurService.get_magic_link()`

2. **`main_window.py`**:
   - Remove `GmailService` and `GmailAutomationConfig` imports
   - Add `MailosaurService` and `MailosaurConfig` imports
   - Update `_create_crawler_loop()` to instantiate `MailosaurService`
   - Update `_create_config_manager()` to use Mailosaur settings

3. **`settings_panel.py`**:
   - Remove "Test Gmail Account" field
   - Add "Mailosaur API Key" field
   - Add "Mailosaur Server ID" field  
   - Add "Mailosaur Test Email" field
   - Update `_load_settings()` and `_on_save_clicked()` for new fields

### Phase 3: Integration

Update integration points:
- Ensure `ConfigManager` stores Mailosaur credentials
- Verify `MailosaurService` is correctly injected into `ActionExecutor`
- Update AI action handlers to use new method signatures

## Complexity Tracking

> No constitution violations requiring justification.

| Item | Notes |
|------|-------|
| Gmail removal | Deletion of complex UI automation code simplifies codebase |
| API integration | Mailosaur SDK provides simpler, more reliable integration |
