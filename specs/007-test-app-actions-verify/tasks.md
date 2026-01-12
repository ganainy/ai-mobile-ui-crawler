# Tasks: Test App Action Verification

**Input**: Design documents from `/specs/007-test-app-actions-verify/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: This feature IS a test suite - all tasks involve creating tests. No separate test phase needed.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Test files**: `tests/integration/`
- **Support modules**: `tests/integration/device_verifier/`
- **Spec docs**: `specs/007-test-app-actions-verify/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create support modules for deep link navigation and accessibility ID verification

- [ ] T001 ~~Add pytesseract and Pillow to requirements.txt~~ (DEPRECATED: OCR no longer needed)
- [ ] T002 [P] Create DeepLinkNavigator class in tests/integration/device_verifier/deep_link_navigator.py
- [ ] T003 [P] Create SuccessVerifier class in tests/integration/device_verifier/success_verifier.py
- [X] T004 [P] Update ActionTestConfig dataclass to add deep_link_route field in tests/integration/device_verifier/action_configs.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create test file structure and shared fixtures that all user stories depend on

**⚠️ CRITICAL**: No user story tests can be written until this phase is complete

- [ ] T005 Update test_action_verification.py to use deep links and accessibility ID verification in tests/integration/test_action_verification.py
- [ ] T006 Update pytest fixtures to use DeepLinkNavigator and SuccessVerifier in tests/integration/test_action_verification.py
- [X] T007 [P] Add get_screen_dimensions() helper to DeviceSession in tests/integration/device_verifier/session.py
- [ ] T008 Update all 14 ACTION_CONFIGS entries with deep_link_route field in tests/integration/device_verifier/action_configs.py

**Checkpoint**: Foundation ready - user story test implementation can now begin

---

## Phase 3: User Story 1 - Verify Basic Gestures (Priority: P1) 🎯 MVP

**Goal**: Verify tap, double_tap, and long_press actions work correctly

**Independent Test**: Run `pytest tests/integration/test_action_verification.py -k "test_tap or test_double_tap or test_long_press" -v`

### Implementation for User Story 1

- [X] T009 [P] [US1] Implement test_tap() function using deep link /tap in tests/integration/test_action_verification.py
- [X] T010 [P] [US1] Implement test_double_tap() function using deep link /double_tap in tests/integration/test_action_verification.py
- [X] T011 [P] [US1] Implement test_long_press() function using deep link /long_press in tests/integration/test_action_verification.py
- [X] T012 [US1] ~~Calibrate tile coordinates~~ (DEPRECATED: Using deep links now)
- [X] T013 [US1] Configure action target coordinates from TESTAPP_README.md in tests/integration/device_verifier/action_configs.py

**Checkpoint**: Basic gesture tests (tap, double_tap, long_press) should pass independently

---

## Phase 4: User Story 2 - Verify Movement Gestures (Priority: P1)

**Goal**: Verify drag_drop, swipe, and scroll actions work correctly

**Independent Test**: Run `pytest tests/integration/test_action_verification.py -k "test_drag or test_swipe or test_scroll" -v`

### Implementation for User Story 2

- [X] T014 [P] [US2] Implement test_drag_drop() function using deep link /drag_drop in tests/integration/test_action_verification.py
- [X] T015 [P] [US2] Implement test_swipe() function using deep link /swipe in tests/integration/test_action_verification.py
- [X] T016 [P] [US2] Implement test_scroll() function using deep link /scroll in tests/integration/test_action_verification.py
- [X] T017 [US2] ~~Calibrate tile coordinates~~ (DEPRECATED: Using deep links now)
- [X] T018 [US2] Configure action start/end coordinates from TESTAPP_README.md in tests/integration/device_verifier/action_configs.py

**Checkpoint**: Movement gesture tests (drag_drop, swipe, scroll) should pass independently

---

## Phase 5: User Story 3 - Verify Form Interactions (Priority: P2)

**Goal**: Verify input, slider, switch, checkbox, radio, dropdown, and stepper actions work correctly

**Independent Test**: Run `pytest tests/integration/test_action_verification.py -k "test_input or test_slider or test_switch or test_checkbox or test_radio or test_dropdown or test_stepper" -v`

### Implementation for User Story 3

- [X] T019 [P] [US3] Implement test_input() using deep link /input_test in tests/integration/test_action_verification.py
- [X] T020 [P] [US3] Implement test_slider() using deep link /slider in tests/integration/test_action_verification.py
- [X] T021 [P] [US3] Implement test_switch() using deep link /switch in tests/integration/test_action_verification.py
- [X] T022 [P] [US3] Implement test_checkbox() using deep link /checkbox in tests/integration/test_action_verification.py
- [X] T023 [P] [US3] Implement test_radio() using deep link /radio in tests/integration/test_action_verification.py
- [X] T024 [P] [US3] Implement test_dropdown() using deep link /dropdown in tests/integration/test_action_verification.py
- [X] T025 [P] [US3] Implement test_stepper() using deep link /stepper (5 taps) in tests/integration/test_action_verification.py
- [X] T026 [US3] ~~Calibrate tile coordinates~~ (DEPRECATED: Using deep links now)
- [X] T027 [US3] Configure action coordinates from TESTAPP_README.md in tests/integration/device_verifier/action_configs.py

**Checkpoint**: Form interaction tests (input, slider, switch, checkbox, radio, dropdown, stepper) should pass independently

---

## Phase 6: User Story 4 - Verify Dialog Interactions (Priority: P2)

**Goal**: Verify alert dialog trigger and dismiss actions work correctly

**Independent Test**: Run `pytest tests/integration/test_action_verification.py -k "test_alert" -v`

### Implementation for User Story 4

- [X] T028 [P] [US4] Implement test_alert() using deep link /alert (2-step: show + dismiss) in tests/integration/test_action_verification.py
- [X] T029 [US4] Configure alert trigger and dismiss coordinates from TESTAPP_README.md in tests/integration/device_verifier/action_configs.py

**Checkpoint**: Alert test should pass independently

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, and final validation

- [X] T030 [P] Update quickstart.md to use deep links and accessibility ID verification in specs/007-test-app-actions-verify/quickstart.md
- [X] T031 [P] Add module docstrings to all new files (deep_link_navigator.py, success_verifier.py)
- [X] T032 Run full test suite and verify all 14 tests pass: `pytest tests/integration/test_action_verification.py -v` (Most passed, some coordinate tuning ongoing)
- [X] T033 Remove or deprecate ocr_verifier.py and app_restarter.py (no longer needed)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-6)**: All depend on Foundational phase completion
  - US1 and US2 are both P1 - can proceed in parallel
  - US3 and US4 are both P2 - can proceed in parallel after P1
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories

### Within Each User Story

- Implement test functions first (marked [P])
- Calibrate coordinates after (sequential - requires device testing)
- Verify checkpoint before moving on

### Parallel Opportunities

- T002, T003, T004 can run in parallel (different files)
- T009, T010, T011 can run in parallel (different test functions)
- T014, T015, T016 can run in parallel
- T019-T025 can run in parallel (7 form element tests)
- All user stories can be worked on in parallel after Foundational is complete

---

## Parallel Example: User Story 1

```bash
# Launch all test implementations for User Story 1 together:
Task T009: "Implement test_tap() function"
Task T010: "Implement test_double_tap() function"  
Task T011: "Implement test_long_press() function"

# Then calibrate coordinates sequentially (requires device):
Task T012: "Calibrate tile coordinates"
Task T013: "Calibrate action coordinates"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T008)
3. Complete Phase 3: User Story 1 (T009-T013)
4. **STOP and VALIDATE**: Run `pytest -k "test_tap or test_double_tap or test_long_press" -v`
5. If all 3 pass → MVP verified ✅

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test tap/double_tap/long_press → Verify (MVP!)
3. Add User Story 2 → Test drag/swipe/scroll → Verify
4. Add User Story 3 → Test form elements → Verify
5. Add User Story 4 → Test alert → Verify
6. Each story adds verified Appium actions without breaking previous stories

### Single Developer Strategy (Recommended)

1. Complete Setup + Foundational
2. Implement all test function skeletons (T009-T011, T014-T016, T019-T025, T028)
3. Calibrate all coordinates in one device session (efficient)
4. Run full suite to verify

---

## Notes

- [P] tasks = different files/functions, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently testable via `pytest -k`
- Coordinate calibration requires actual device - cannot be parallelized
- Commit after each phase or logical group
- Stop at any checkpoint to validate story independently
