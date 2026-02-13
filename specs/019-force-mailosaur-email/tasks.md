# Tasks: Force Mailosaur for Email Verification

**Input**: Design documents from `/specs/019-force-mailosaur-email/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: 6 unit tests in `tests/unit/domain/test_action_executor_mailosaur.py` ✅

**Organization**: Tasks organized by phase

---

## Phase 1: Setup (Gmail Code Removal)

**Purpose**: Remove all Gmail-related code before modifications to prevent import conflicts

- [X] T001 Delete Gmail infrastructure directory at `src/mobile_crawler/infrastructure/gmail/`
- [X] T002 Delete Gmail integration tests directory at `tests/integration/device_verifier/gmail/`
- [X] T003 Delete Gmail unit tests directory at `tests/unit/infrastructure/gmail/`
- [X] T004 Delete Gmail E2E test file at `tests/integration/test_auth_gmail_e2e.py`

**Checkpoint**: All Gmail code removed ✅

---

## Phase 2: Foundational (Core Dependency Updates)

**Purpose**: Update core components that depend on Gmail to use Mailosaur

- [X] T005 Update imports in `src/mobile_crawler/domain/action_executor.py`
- [X] T006 Update ActionExecutor constructor in `src/mobile_crawler/domain/action_executor.py`
- [X] T007 Update imports in `src/mobile_crawler/ui/main_window.py`
- [X] T008 Update `_create_crawler_loop()` in `src/mobile_crawler/ui/main_window.py`
- [X] T009 Update `_create_config_manager()` in `src/mobile_crawler/ui/main_window.py`

**Checkpoint**: Foundation ready ✅

---

## Phase 3: User Story 3 - Complete Gmail Code Removal

**Goal**: Verify all Gmail-related code is completely removed from the codebase

- [X] T010 Search for remaining Gmail references in `src/` directory and remove any found
- [X] T011 Search for remaining Gmail references in `tests/` directory and remove any found
- [X] T012 Verify `src/mobile_crawler/infrastructure/gmail/` directory no longer exists
- [X] T013 Run pytest to verify no import errors

**Checkpoint**: Pure Mailosaur environment ✅

---

## Phase 4: User Story 4 - Update ActionExecutor to Use Mailosaur

**Goal**: ActionExecutor uses MailosaurService for OTP and verification link extraction

- [X] T014 Implement `extract_otp()` method - replace Gmail logic with `mailosaur_service.get_otp()`
- [X] T015 Implement `click_verification_link()` method - replace Gmail logic with `mailosaur_service.get_magic_link()`
- [X] T016 Add `_open_url_via_adb()` helper to open extracted magic links directly on device
- [X] T017 Add error handling for cases where Mailosaur service is not configured
- [X] T018 Store `test_email` reference in ActionExecutor for fallback during extraction

**Checkpoint**: ActionExecutor functional with Mailosaur ✅

---

## Phase 5: User Story 1 - OTP Extraction via Mailosaur

**Goal**: Crawler can extract OTP codes from emails using Mailosaur API

- [X] T019 Implement extraction in `extract_otp` method
- [X] T020 Verify extraction with unit test (mock MailosaurService)
- [X] T021 Manual check of MailosaurService capability

**Checkpoint**: OTP extraction works ✅

---

## Phase 6: User Story 2 - Magic Link Extraction via Mailosaur

**Goal**: Crawler can extract verification links from emails using Mailosaur API

- [X] T022 Implement link extraction in `click_verification_link` method
- [X] T023 Implement ADB-based link opening
- [X] T024 Verify link extraction with unit test (mock MailosaurService)
- [X] T025 Manual check of MailosaurService capability

**Checkpoint**: Magic link extraction works ✅

---

## Phase 7: User Story 5 - UI Configuration for Mailosaur

**Goal**: Settings panel allows configuration of Mailosaur credentials

- [X] T026 Remove "Test Gmail Account" UI field from `src/mobile_crawler/ui/widgets/settings_panel.py`
- [X] T027 Add "Mailosaur API Key" password input field
- [X] T028 Add "Mailosaur Server ID" text input field
- [X] T029 Update `_load_settings()` in `SettingsPanel` for Mailosaur keys
- [X] T030 Update `_on_save_clicked()` in `SettingsPanel` for Mailosaur keys
- [X] T031 Add getter methods for Mailosaur config in `SettingsPanel`
- [X] T032 Update `_create_config_manager()` in `MainWindow` to read Mailosaur settings

**Checkpoint**: UI configuration ready ✅

---

## Phase 8: Polish & Final Verification

- [X] T033 Run unit tests for ActionExecutor Mailosaur integration
- [X] T034 Run Mailosaur integration tests (using SMTP sender)
- [X] T035 Verify application builds and imports successfully
- [X] T036 Update GEMINI.md to reflect Gmail removal
- [X] T037 Sanitize remaining Gmail references in test mocks/comments
- [X] T038 Mark previous Gmail specs as superseded

**Final Checkpost**: Feature complete and verified ✅
