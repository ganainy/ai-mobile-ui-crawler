---
description: "Task list for Fix Device Interaction & Add Tests"
---

# Tasks: Fix Device Interaction & Add Tests

**Input**: Design documents from `/specs/006-fix-device-interaction/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create tests integration directory `tests/integration/device_verifier/`
- [x] T002 [P] Configure/Verify Appium dependencies (ensure `Appium-Python-Client` is available)

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Create base `VerificationCase` and `VerificationReport` dataclasses in `tests/integration/device_verifier/models.py`
- [x] T004 [P] Create CLI entry point scaffolding `tests/integration/verify_device_actions.py`
- [x] T005 Create Appium session helper to connect to device in `tests/integration/device_verifier/session.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

## Phase 3: User Story 1 - Device Action Verification Suite (Priority: P1) 🎯 MVP

**Goal**: Create a standalone script to verify Appium actions on the Test App.

**Independent Test**: Run `python tests/integration/verify_device_actions.py` and see reports.

### Implementation for User Story 1

- [x] T006 [P] [US1] Implement `tap_at` verification case (PlaygroundScreen Single Tap) in `tests/integration/device_verifier/cases/tap_cases.py`
- [x] T007 [P] [US1] Implement `double_tap` verification case (PlaygroundScreen Double Tap) in `tests/integration/device_verifier/cases/tap_cases.py`
- [x] T008 [P] [US1] Implement `long_press` verification case (PlaygroundScreen Long Press) in `tests/integration/device_verifier/cases/tap_cases.py`
- [x] T009 [P] [US1] Implement `input` verification case (SignupScreen text fields) in `tests/integration/device_verifier/cases/input_cases.py`
- [x] T010 [P] [US1] Implement `swipe`/`scroll` verification case (LongListScreen) in `tests/integration/device_verifier/cases/swipe_cases.py`
- [x] T011 [P] [US1] Implement `drag` verification case (PlaygroundScreen Drag & Drop) in `tests/integration/device_verifier/cases/drag_cases.py`
- [x] T012 [P] [US1] Implement `back` navigation verification case in `tests/integration/device_verifier/cases/nav_cases.py`
- [x] T013 [US1] Wire all cases into main runner `tests/integration/verify_device_actions.py`
- [x] T014 [US1] Add JSON reporting to `tests/integration/verify_device_actions.py`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

## Phase 4: User Story 2 - Robust Appium Driver Implementation (Priority: P1)

**Goal**: Refactor the driver to pass the verification suite.

**Independent Test**: Verification suite passes 100%.

### Implementation for User Story 2

- [x] T015 [P] [US2] Refactor `src/mobile_crawler/infrastructure/appium_driver.py` `tap_at` method for robust coordinate-based tapping
- [x] T016 [P] [US2] Refactor/Add `double_tap` method to `src/mobile_crawler/infrastructure/appium_driver.py`
- [x] T017 [P] [US2] Refactor/Add `long_press` method to `src/mobile_crawler/infrastructure/appium_driver.py`
- [x] T018 [P] [US2] Refactor `input` method in `src/mobile_crawler/infrastructure/appium_driver.py`
- [x] T019 [P] [US2] Refactor `swipe` method in `src/mobile_crawler/infrastructure/appium_driver.py` for smoothness/accuracy
- [x] T020 [P] [US2] Implement/Refactor `drag` method in `src/mobile_crawler/infrastructure/appium_driver.py`
- [x] T021 [US2] Verify `tests/integration/verify_device_actions.py` passes with new driver

**Checkpoint**: All user stories should now be independently functional

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T022 [P] Add documentation to `tests/integration/README.md` on how to run verifier
- [x] T023 Run final validation against `com.example.flutter_application_1`

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Depends on US1 (to verify the fix)

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently (Verification Suite Pass) → Deploy/Demo
4. Each story adds value without breaking previous stories
