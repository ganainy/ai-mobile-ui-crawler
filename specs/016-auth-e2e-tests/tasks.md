# Tasks: Gmail-Integrated Auth E2E Tests

**Input**: Design documents from `/specs/016-auth-e2e-tests/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Note**: This task list extends the existing simulated auth tests (already implemented) with **real Gmail integration** for production-like OTP and email link verification.

**Existing Implementation**: Simulated auth tests are complete (US1-US7 with hardcoded OTP/tokens).

**New Scope**: Add Gmail automation module for real-world email verification workflows.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story/capability this task belongs to (e.g., GM-OTP, GM-LINK)
- Include exact file paths in descriptions

## Path Conventions

This feature extends the **existing test infrastructure**:
- **Gmail Module**: `tests/integration/device_verifier/gmail/`
- **Auth Module**: `tests/integration/device_verifier/auth/` (existing, to be updated)
- **Test Suite**: `tests/integration/test_auth_gmail_e2e.py` (new)

---

## Phase 1: Setup (Gmail Module Infrastructure)

**Purpose**: Create the Gmail automation module structure and configuration

- [x] T001 Create Gmail module directory at `tests/integration/device_verifier/gmail/`
- [x] T002 Create `tests/integration/device_verifier/gmail/__init__.py` with module exports
- [x] T003 [P] Create `tests/integration/device_verifier/gmail/gmail_configs.py` with selectors, patterns, and constants from research.md
- [x] T004 [P] Create `GmailAutomationConfig` dataclass in `tests/integration/device_verifier/gmail/gmail_configs.py`

---

## Phase 2: Foundational (Core Gmail Automation)

**Purpose**: Implement the core Gmail automation classes that ALL Gmail-based features depend on

**⚠️ CRITICAL**: No Gmail integration tests can run until this phase is complete

### Gmail Navigator

- [x] T005 Create `GmailNavigator` class skeleton in `tests/integration/device_verifier/gmail/gmail_navigator.py`
- [x] T006 Implement `open_gmail()` method in `tests/integration/device_verifier/gmail/gmail_navigator.py`
- [x] T007 Implement `is_inbox_visible()` method in `tests/integration/device_verifier/gmail/gmail_navigator.py`
- [x] T008 Implement `refresh_inbox()` method in `tests/integration/device_verifier/gmail/gmail_navigator.py`
- [x] T009 Implement `open_first_email()` method in `tests/integration/device_verifier/gmail/gmail_navigator.py`
- [x] T010 Implement `open_email_by_subject()` method in `tests/integration/device_verifier/gmail/gmail_navigator.py`
- [x] T011 Implement `search_emails()` method in `tests/integration/device_verifier/gmail/gmail_navigator.py`
- [x] T012 Implement `go_back()` and `is_email_open()` methods in `tests/integration/device_verifier/gmail/gmail_navigator.py`
- [x] T013 Add error classes `GmailNavigationError`, `GmailNotInstalledError`, `NoEmailsFoundError` in `tests/integration/device_verifier/gmail/gmail_navigator.py`

### Gmail Reader

- [x] T014 [P] Create `GmailReader` class skeleton in `tests/integration/device_verifier/gmail/gmail_reader.py`
- [x] T015 [P] Create `OTPResult` and `LinkResult` dataclasses in `tests/integration/device_verifier/gmail/gmail_reader.py`
- [x] T016 Implement `get_email_content()` method in `tests/integration/device_verifier/gmail/gmail_reader.py`
- [x] T017 Implement `extract_otp()` method with regex patterns in `tests/integration/device_verifier/gmail/gmail_reader.py`
- [x] T018 Implement `extract_verification_link()` method in `tests/integration/device_verifier/gmail/gmail_reader.py`
- [x] T019 Add error classes `GmailReadError`, `OTPNotFoundError`, `LinkNotFoundError` in `tests/integration/device_verifier/gmail/gmail_reader.py`

### App Switcher

- [x] T020 [P] Create `AppSwitcher` class skeleton in `tests/integration/device_verifier/gmail/app_switcher.py`
- [x] T021 [P] Create `AppState` dataclass in `tests/integration/device_verifier/gmail/app_switcher.py`
- [x] T022 Implement `switch_to_gmail()` method in `tests/integration/device_verifier/gmail/app_switcher.py`
- [x] T023 Implement `switch_to_test_app()` method in `tests/integration/device_verifier/gmail/app_switcher.py`
- [x] T024 Implement `get_current_app()` and `is_gmail_foreground()` methods in `tests/integration/device_verifier/gmail/app_switcher.py`
- [x] T025 Implement `ensure_gmail()` and `ensure_test_app()` helper methods in `tests/integration/device_verifier/gmail/app_switcher.py`

**Checkpoint**: Gmail automation module is importable and methods are callable ✅

---

## Phase 3: GM-OTP - Real OTP Extraction from Gmail (Priority: P1) 🎯 MVP

**Goal**: Extract OTP codes from real emails in Gmail and use them in the test app

**Independent Test**: Trigger OTP email → Switch to Gmail → Open email → Extract OTP → Return to app → Paste OTP → Verify success

### Implementation

- [x] T026 [GM-OTP] Implement `copy_otp_to_clipboard()` method in `tests/integration/device_verifier/gmail/gmail_reader.py`
- [x] T027 [GM-OTP] Implement `click_verification_link()` method in `tests/integration/device_verifier/gmail/gmail_reader.py`
- [x] T028 [GM-OTP] Add `wait_for_email()` polling function in `tests/integration/device_verifier/gmail/gmail_navigator.py`
- [x] T029 [GM-OTP] Update `tests/integration/device_verifier/auth/auth_form_filler.py` with `paste_otp()` method using clipboard

### Clipboard Support

- [x] T030 [GM-OTP] Create `ClipboardHelper` class in `tests/integration/device_verifier/gmail/clipboard_helper.py`
- [x] T031 [GM-OTP] Implement `set_clipboard()` method in `tests/integration/device_verifier/gmail/clipboard_helper.py`
- [x] T032 [GM-OTP] Implement `get_clipboard()` method in `tests/integration/device_verifier/gmail/clipboard_helper.py`
- [x] T033 [GM-OTP] Implement `paste_from_clipboard()` method (long-press + paste) in `tests/integration/device_verifier/gmail/clipboard_helper.py`

### Test Case

- [x] T034 [GM-OTP] Create Gmail test fixtures in `tests/integration/conftest.py` (gmail_navigator, gmail_reader, app_switcher)
- [x] T035 [GM-OTP] Create `test_gmail_otp_extraction` in `tests/integration/test_auth_gmail_e2e.py`
- [x] T036 [GM-OTP] Add configuration for Gmail test email sender/subject in test config

**Checkpoint**: Real OTP extraction from Gmail works end-to-end ✅

---

## Phase 4: GM-LINK - Click Verification Links in Gmail (Priority: P1)

**Goal**: Click verification links in Gmail emails that trigger deep links back to the test app

**Independent Test**: Trigger link email → Switch to Gmail → Open email → Click verification link → App receives deep link → Verify authenticated state

### Implementation

- [x] T037 [GM-LINK] Implement `find_verification_button()` method in `tests/integration/device_verifier/gmail/gmail_reader.py`
- [x] T038 [GM-LINK] Implement `extract_and_trigger_link()` fallback using ADB in `tests/integration/device_verifier/gmail/gmail_reader.py`
- [x] T039 [GM-LINK] Update `AppSwitcher` to detect when app was opened via deep link in `tests/integration/device_verifier/gmail/app_switcher.py`

### Test Case

- [x] T040 [GM-LINK] Create `test_gmail_verification_link_click` in `tests/integration/test_auth_gmail_e2e.py`
- [x] T041 [GM-LINK] Add verification that app received deep link and transitioned to authenticated state

**Checkpoint**: Clicking verification links in Gmail works end-to-end ✅

---

## Phase 5: GM-SEARCH - Advanced Email Search (Priority: P2)

**Goal**: Support searching for emails by sender, subject, and time filters

**Independent Test**: Send email → Search by sender/subject → Verify correct email found

### Implementation

- [x] T042 [GM-SEARCH] Create `GmailSearchQuery` dataclass in `tests/integration/device_verifier/gmail/gmail_configs.py`
- [x] T043 [GM-SEARCH] Implement `build_search_query()` method in `tests/integration/device_verifier/gmail/gmail_navigator.py`
- [x] T044 [GM-SEARCH] Implement `clear_search()` method in `tests/integration/device_verifier/gmail/gmail_navigator.py`
- [x] T045 [GM-SEARCH] Add `filter_by_timestamp()` capability (select emails newer than X) in `tests/integration/device_verifier/gmail/gmail_navigator.py`

### Test Case

- [x] T046 [GM-SEARCH] Create `test_gmail_search_by_sender` in `tests/integration/test_auth_gmail_e2e.py`
- [x] T047 [GM-SEARCH] Create `test_gmail_search_by_subject` in `tests/integration/test_auth_gmail_e2e.py`

**Checkpoint**: Email search filters work correctly ✅

---

## Phase 6: GM-RESILIENCE - Error Handling & Recovery (Priority: P2)

**Goal**: Ensure Gmail automation can recover from errors, popups, and slow loading

**Independent Test**: Simulate error (open wrong app) → Call recovery → Verify Gmail back in inbox

### Implementation

- [x] T048 [GM-RESILIENCE] Add Gmail sign-in detection in `tests/integration/device_verifier/gmail/gmail_navigator.py`
- [x] T049 [GM-RESILIENCE] Implement retry logic for `wait_for_email()`
- [x] T050 [GM-RESILIENCE] Add screenshot capture on Gmail automation failures
- [x] T051 [GM-RESILIENCE] Implement `recover_from_unknown_state()`
- [x] T052 [GM-RESILIENCE] Add timeout handling for all Gmail operations

**Checkpoint**: Gmail automation is robust and self-healing ✅

---

## Phase 7: GM-COMBINED - Full E2E Auth Integration (Priority: P1) 🎯

**Goal**: Integrate Gmail automation into the main E2E test suite

**Independent Test**: Complete signup flow from app start to home screen using Gmail

### Implementation

- [x] T053 [GM-COMBINED] Integrate Gmail automation with existing `auth_verifier`
- [x] T054 [GM-COMBINED] Create `GmailAuthVerifier` wrapper in `tests/integration/device_verifier/gmail/gmail_auth_verifier.py`
- [x] T055 [GM-COMBINED] Implement full signup-to-home test with real Gmail verification in `tests/integration/test_auth_gmail_e2e.py`

**Checkpoint**: End-to-end authentication with real Gmail works ✅

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, documentation, and cleanup

- [x] T058 [P] Add docstrings to all Gmail module classes and methods
- [x] T059 [P] Update `tests/integration/device_verifier/gmail/__init__.py` with public exports
- [x] T060 Run all Gmail E2E tests and verify 90% pass rate
- [x] T061 [P] Update `specs/016-auth-e2e-tests/quickstart.md` with Gmail setup instructions
- [x] T062 Capture screenshots for Gmail flow documentation
- [x] T063 Code cleanup: remove debug prints, standardize error messages
- [x] T064 [P] Update `GEMINI.md` with Gmail automation commands

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 - BLOCKS all Gmail features
- **Phases 3-4 (P1 Features)**: Depend on Phase 2 completion
  - GM-OTP and GM-LINK can proceed in parallel
- **Phases 5-7 (P2 Features)**: Depend on Phase 3 or Phase 4 completion
  - Can proceed in parallel once P1 phases complete
- **Phase 8 (Polish)**: Depends on all desired features being complete

### Feature Dependencies

| Feature | Depends On | Can Start After |
|---------|------------|-----------------|
| GM-OTP (Real OTP) | Foundational (Phase 2) | Phase 2 |
| GM-LINK (Click Links) | Foundational (Phase 2) | Phase 2 |
| GM-SEARCH (Email Search) | GM-OTP or GM-LINK | Phase 3 or 4 |
| GM-RESILIENCE (Error Handling) | GM-OTP or GM-LINK | Phase 3 or 4 |
| GM-COMBINED (Full Flows) | GM-OTP + GM-LINK | Phase 3 + 4 |

### Parallel Opportunities

**Phase 2 Parallel Tasks**:
- T014-T019 (GmailReader) ‖ T020-T025 (AppSwitcher)
- T003-T004 (gmail_configs.py) ‖ T005-T013 (GmailNavigator)

**Cross-Feature Parallel**:
- T026-T036 (GM-OTP) ‖ T037-T041 (GM-LINK)
- T042-T047 (GM-SEARCH) ‖ T048-T054 (GM-RESILIENCE)

---

## Implementation Strategy

### MVP First (GM-OTP Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: GM-OTP (Real OTP extraction)
4. **STOP and VALIDATE**: Test OTP extraction with a real email
5. Build on success before adding more features

### Incremental Delivery

1. Setup + Foundational → Gmail module ready
2. Add GM-OTP → Real OTP extraction working (MVP!)
3. Add GM-LINK → Link clicking working
4. Add GM-SEARCH → Advanced email search
5. Add GM-RESILIENCE → Robust error handling
6. Add GM-COMBINED → Full production-like auth flows
7. Each feature adds value without breaking previous features

---

## Task Summary

| Phase | Task Count | Description |
|-------|------------|-------------|
| Phase 1: Setup | 4 | Module infrastructure |
| Phase 2: Foundational | 21 | Core Gmail automation classes |
| Phase 3: GM-OTP | 11 | Real OTP extraction (MVP) |
| Phase 4: GM-LINK | 5 | Click verification links |
| Phase 5: GM-SEARCH | 6 | Advanced email search |
| Phase 6: GM-RESILIENCE | 7 | Error handling & retry |
| Phase 7: GM-COMBINED | 3 | Full auth flows |
| Phase 8: Polish | 7 | Documentation & cleanup |
| **TOTAL** | **64** | |

---

## Notes

- [P] tasks = different files, no dependencies
- [Feature] label maps task to specific Gmail capability for traceability
- Each feature should be independently completable and testable
- Gmail app MUST be signed in on test device before running tests
- Run tests: `pytest tests/integration/test_auth_gmail_e2e.py -v`
- Commit after each task or logical group
- Stop at any checkpoint to validate feature independently
