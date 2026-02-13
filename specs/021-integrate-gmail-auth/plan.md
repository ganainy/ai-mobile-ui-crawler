# Implementation Plan: Integrate Gmail Auth

**Feature Branch**: `001-integrate-gmail-auth`
**Feature Spec**: `specs/001-integrate-gmail-auth/spec.md`

## Summary
Port existing Gmail interaction logic (OTP extraction, link clicking) from test utilities to a production-ready infrastructure adapter in `src`. Integrate the Gmail account management into the application's global settings and implement auto-switching in the Gmail app.

## Technical Context
- **Infrastructure**: Existing Appium and ADB based automation.
- **Components to Port**: `GmailNavigator`, `GmailReader`, `AppSwitcher`, `ClipboardHelper`.
- **New Components**: `GmailAccountSwitcher` (UI-based account switching in Gmail), `ConfigManager` updates for "Target Gmail Account".
- **Target Location**: `src/mobile_crawler/infrastructure/gmail/`.

## Constitution Check
- **Principle I: Library-First**: The Gmail integration will be implemented as a standalone package within `infrastructure`.
- **Principle III: Test-First**: Existing E2E tests will be refactored to use the new production code, ensuring parity.
- **Principle IV: Integration Testing**: Full E2E flow with `auth_test_app` will be the primary validation.

## Gates
- **G-001**: `pytest tests/integration/test_auth_gmail_e2e.py` must pass with 100% success.
- **G-002**: `GmailService` must be accessible via dependency injection or a clean factory.
- **G-003**: "Target Gmail Account" must be configurable in the UI and persisted.

## Phase 0: Outline & Research
1. **Research Task**: UI selectors for Gmail's account switcher (different versions of Gmail).
2. **Research Task**: Best practices for persistence of "Target Gmail Account" in `ConfigManager`.

## Phase 1: Design & Contracts
1. **Data Model**: Update `GmailAutomationConfig` and transient models to include `target_account`.
2. **Contracts**: Define `GmailService` interface.
3. **Agent Context**: Update with `Appium`, `ADB`, and Gmail automation technologies.

## Phase 2: Implementation Planning (Tasks)
1. Port foundational modules (`config.py`, `reader.py`, `navigator.py`, `app_switcher.py`, `clipboard.py`).
2. Implement `GmailAccountSwitcher` for multi-account support.
3. Update `src/mobile_crawler/config/config_manager.py` to support `gmail_account`.
4. Update Desktop UI to include `Target Gmail Account` field.
5. Implement `GmailService` orchestration.
6. Refactor tests and verify.
