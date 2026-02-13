# Tasks: App Authentication and Signup Support

**Input**: Design documents from `/specs/013-app-auth-signup/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL - not explicitly requested in spec, so test tasks are not included. Focus on implementation tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below follow existing project structure: `src/mobile_crawler/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database migration and infrastructure setup

- [ ] T001 Create database migration script for app_credentials table in src/mobile_crawler/infrastructure/migrations/002_add_app_credentials.sql
- [ ] T002 [P] Update UserConfigStore.create_schema() to create app_credentials table in src/mobile_crawler/infrastructure/user_config_store.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Implement AppSwitcher class in src/mobile_crawler/infrastructure/app_switcher.py per contracts/app-switcher.md
- [ ] T004 [P] Implement CredentialManager class in src/mobile_crawler/domain/credential_manager.py per contracts/credential-manager.md
- [ ] T005 [P] Implement GmailInteraction class in src/mobile_crawler/domain/gmail_interaction.py per contracts/gmail-interaction.md
- [ ] T006 [P] Implement AuthManager class in src/mobile_crawler/domain/auth_manager.py per contracts/auth-manager.md

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Configure Test Email for Authentication (Priority: P1) 🎯 MVP

**Goal**: User can configure and save a test email address in the Settings panel that persists across application restarts and is accessible to the crawler configuration system.

**Independent Test**: Add test email field to Settings panel, save it, verify it persists and is accessible to crawler configuration system.

### Implementation for User Story 1

- [ ] T007 [US1] Add test_email_input QLineEdit field to SettingsPanel in src/mobile_crawler/ui/widgets/settings_panel.py
- [ ] T008 [US1] Add test email validation (email format regex) in SettingsPanel._validate_email() method in src/mobile_crawler/ui/widgets/settings_panel.py
- [ ] T009 [US1] Update SettingsPanel._load_settings() to load test_email from UserConfigStore in src/mobile_crawler/ui/widgets/settings_panel.py
- [ ] T010 [US1] Update SettingsPanel._on_save_clicked() to save test_email as encrypted secret in src/mobile_crawler/ui/widgets/settings_panel.py
- [ ] T011 [US1] Add get_test_email() method to SettingsPanel in src/mobile_crawler/ui/widgets/settings_panel.py
- [ ] T012 [US1] Update ConfigManager to support test_email configuration in src/mobile_crawler/config/config_manager.py
- [ ] T013 [US1] Update MainWindow._create_config_manager() to include test_email from settings panel in src/mobile_crawler/ui/main_window.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently - users can configure test email in UI and it persists

---

## Phase 4: User Story 2 - Handle App Signup with Email Verification (Priority: P1)

**Goal**: Crawler detects signup screens, completes signup form, switches to Gmail to retrieve verification (OTP or link), completes verification, and stores credentials.

**Independent Test**: Crawl an app requiring email verification signup, observe crawler switch to Gmail, retrieve verification, complete signup, and store credentials.

**Dependencies**: Requires User Story 1 (test email must be configured) and all foundational components (T003-T006)

### Implementation for User Story 2

- [ ] T014 [US2] Add authentication detection logic to AI prompt builder in src/mobile_crawler/domain/prompt_builder.py
- [ ] T015 [US2] Implement AuthManager.detect_authentication_required() method in src/mobile_crawler/domain/auth_manager.py
- [ ] T016 [US2] Implement AuthManager.handle_signup_flow() method in src/mobile_crawler/domain/auth_manager.py
- [ ] T017 [US2] Implement AuthManager.handle_email_verification() method in src/mobile_crawler/domain/auth_manager.py
- [ ] T018 [US2] Implement GmailInteraction.locate_verification_email() method in src/mobile_crawler/domain/gmail_interaction.py
- [ ] T019 [US2] Implement GmailInteraction.extract_otp_code() method using OCR service in src/mobile_crawler/domain/gmail_interaction.py
- [ ] T020 [US2] Implement GmailInteraction.find_confirmation_link() method using AI vision in src/mobile_crawler/domain/gmail_interaction.py
- [ ] T021 [US2] Implement GmailInteraction.retrieve_verification() complete flow in src/mobile_crawler/domain/gmail_interaction.py
- [ ] T022 [US2] Integrate AuthManager into CrawlerLoop to detect and handle authentication in src/mobile_crawler/core/crawler_loop.py
- [ ] T023 [US2] Add credential storage after successful signup in AuthManager.handle_signup_flow() in src/mobile_crawler/domain/auth_manager.py
- [ ] T024 [US2] Update CredentialManager.store_credentials() to handle credential encryption and storage in src/mobile_crawler/domain/credential_manager.py

**Checkpoint**: At this point, User Story 2 should be fully functional - crawler can complete signup flows with email verification and store credentials

---

## Phase 5: User Story 3 - Reuse Stored Credentials for Subsequent Crawls (Priority: P2)

**Goal**: Crawler checks for stored credentials at crawl start and when auth screen detected, uses them to auto-login, falls back to signup if login fails.

**Independent Test**: Crawl an app that requires signup (stores credentials), then crawl same app again and verify it uses stored credentials to log in directly.

**Dependencies**: Requires User Story 2 (credential storage must work first)

### Implementation for User Story 3

- [ ] T025 [US3] Implement CredentialManager.get_credentials() method in src/mobile_crawler/domain/credential_manager.py
- [ ] T026 [US3] Implement CredentialManager.has_credentials() method in src/mobile_crawler/domain/credential_manager.py
- [ ] T027 [US3] Implement CredentialManager.update_last_successful_login() method in src/mobile_crawler/domain/credential_manager.py
- [ ] T028 [US3] Implement CredentialManager.delete_credentials() method in src/mobile_crawler/domain/credential_manager.py
- [ ] T029 [US3] Implement AuthManager.attempt_login_with_stored_credentials() method in src/mobile_crawler/domain/auth_manager.py
- [ ] T030 [US3] Update AuthManager.handle_authentication() to check for stored credentials first in src/mobile_crawler/domain/auth_manager.py
- [ ] T031 [US3] Add credential check at crawl start in CrawlerLoop.run() in src/mobile_crawler/core/crawler_loop.py
- [ ] T032 [US3] Implement fallback logic: if login fails, delete old credentials and proceed with signup in AuthManager.handle_authentication() in src/mobile_crawler/domain/auth_manager.py
- [ ] T033 [US3] Update credential storage after successful signup when replacing old credentials in AuthManager.handle_signup_flow() in src/mobile_crawler/domain/auth_manager.py

**Checkpoint**: At this point, User Story 3 should be fully functional - crawler reuses stored credentials for subsequent crawls

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T034 [P] Add error handling for Gmail app not installed scenario in AppSwitcher.switch_to_gmail() in src/mobile_crawler/infrastructure/app_switcher.py
- [ ] T035 [P] Add error handling for verification email not found scenario in GmailInteraction.retrieve_verification() in src/mobile_crawler/domain/gmail_interaction.py
- [ ] T036 [P] Add logging for authentication flows in AuthManager methods in src/mobile_crawler/domain/auth_manager.py
- [ ] T037 [P] Add logging for credential operations in CredentialManager methods in src/mobile_crawler/domain/credential_manager.py
- [ ] T038 [P] Handle edge case: multiple verification emails in Gmail (use most recent) in GmailInteraction.locate_verification_email() in src/mobile_crawler/domain/gmail_interaction.py
- [ ] T039 [P] Handle edge case: OTP code expiration timeout in GmailInteraction.retrieve_verification() in src/mobile_crawler/domain/gmail_interaction.py
- [ ] T040 [P] Add validation for app_package format in CredentialManager methods in src/mobile_crawler/domain/credential_manager.py
- [ ] T041 [P] Update documentation in quickstart.md with troubleshooting section for common issues
- [ ] T042 [P] Run quickstart.md validation to ensure all examples work

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001-T002) - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion (T003-T006)
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P1): Can start after Foundational + User Story 1 (needs test_email configured)
  - User Story 3 (P2): Can start after User Story 2 (needs credential storage working)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Requires User Story 1 (test_email must be configured) + Foundational
- **User Story 3 (P2)**: Requires User Story 2 (credential storage must work first)

### Within Each User Story

- Core infrastructure before integration
- Individual methods before orchestration
- Story complete before moving to next priority

### Parallel Opportunities

- **Setup Phase**: T001 and T002 can run in parallel (different files)
- **Foundational Phase**: T003, T004, T005, T006 can all run in parallel (different files, no dependencies)
- **User Story 1**: T007-T013 can be worked on sequentially (same file modifications)
- **User Story 2**: T014-T024 can be worked on with some parallelization:
  - T014, T015 can be parallel
  - T018, T019, T020 can be parallel (different methods in same file, but can be worked on separately)
  - T021 depends on T018-T020
  - T022 depends on T015-T021
  - T023-T024 depend on T022
- **User Story 3**: T025-T033 are mostly sequential (building on each other)
- **Polish Phase**: T034-T042 can all run in parallel (different files/methods)

---

## Parallel Example: Foundational Phase

```bash
# Launch all foundational components in parallel (different files):
Task: "Implement AppSwitcher class in src/mobile_crawler/infrastructure/app_switcher.py"
Task: "Implement CredentialManager class in src/mobile_crawler/domain/credential_manager.py"
Task: "Implement GmailInteraction class in src/mobile_crawler/domain/gmail_interaction.py"
Task: "Implement AuthManager class in src/mobile_crawler/domain/auth_manager.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T006) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (T007-T013)
4. **STOP and VALIDATE**: Test User Story 1 independently - configure test email, verify it persists
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP - test email configuration)
3. Add User Story 2 → Test independently → Deploy/Demo (Full signup flow with email verification)
4. Add User Story 3 → Test independently → Deploy/Demo (Credential reuse)
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (test email UI)
   - Developer B: Can start User Story 2 prep (but needs US1 for test_email)
3. After User Story 1:
   - Developer A: User Story 2 (signup flow)
   - Developer B: User Story 3 prep (but needs US2 for credential storage)
4. After User Story 2:
   - Developer A: User Story 3 (credential reuse)
   - Developer B: Polish phase tasks

---

## Task Summary

**Total Tasks**: 42

**By Phase**:
- Phase 1 (Setup): 2 tasks
- Phase 2 (Foundational): 4 tasks
- Phase 3 (User Story 1): 7 tasks
- Phase 4 (User Story 2): 11 tasks
- Phase 5 (User Story 3): 9 tasks
- Phase 6 (Polish): 9 tasks

**By User Story**:
- User Story 1: 7 tasks
- User Story 2: 11 tasks
- User Story 3: 9 tasks

**Parallel Opportunities**: 
- Foundational phase: 4 tasks can run in parallel
- Polish phase: 9 tasks can run in parallel
- Some User Story 2 tasks can be parallelized

**Suggested MVP Scope**: 
- Phase 1 (Setup) + Phase 2 (Foundational) + Phase 3 (User Story 1) = 13 tasks
- This delivers test email configuration, which is the foundation for all authentication flows

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- All tasks include exact file paths for clarity
