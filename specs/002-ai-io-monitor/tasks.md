# Tasks: AI Input/Output Monitor

**Input**: Design documents from `/specs/002-ai-io-monitor/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Tests**: Not explicitly requested in specification - tests included as standard practice for widget testing with pytest-qt.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3)
- Paths: `src/mobile_crawler/`, `tests/ui/`

---

## Phase 1: Setup

**Purpose**: No new project setup needed - adding to existing project

- [X] T001 Verify existing signal infrastructure in src/mobile_crawler/ui/signal_adapter.py has ai_request_sent and ai_response_received signals

---

## Phase 2: Foundational

**Purpose**: Core widget infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: Must complete before user story implementation

- [X] T002 Create AIMonitorPanel widget skeleton with QWidget base in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T003 Implement basic UI layout (QGroupBox, QVBoxLayout) with empty QListWidget in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T004 Create AIInteractionItem custom widget for list entries in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T005 Implement add_request() slot for pending state in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T006 Implement add_response() slot to complete interactions in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T007 Add visual status indicators (success=green, failed=red, pending=yellow) in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T008 Modify _create_right_panel() to use QTabWidget with LogViewer and AIMonitorPanel tabs in src/mobile_crawler/ui/main_window.py
- [X] T009 Add ai_monitor_panel instance variable and connect ai_request_sent/ai_response_received signals in src/mobile_crawler/ui/main_window.py
- [X] T010 [P] Create test file with basic initialization test in tests/ui/test_ai_monitor_panel.py

**Checkpoint**: Foundation ready - AI Monitor tab visible, can receive and display basic interactions

---

## Phase 3: User Story 1 - View Live AI Interactions During Crawl (Priority: P1) 🎯 MVP

**Goal**: Real-time display of AI prompts and responses as crawler executes

**Independent Test**: Start a crawl and observe AI interactions appear in monitor panel within 1 second

### Implementation for User Story 1

- [X] T011 [US1] Implement timestamp display formatting (HH:MM:SS) for each entry in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T012 [US1] Implement latency display (X.Xs format) in entry header in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T013 [US1] Implement token count display (in→out format, N/A if unavailable) in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T014 [US1] Implement prompt preview (truncated to 100 chars) in collapsed entry in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T015 [US1] Implement response preview (action + reasoning truncated) in collapsed entry in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T016 [US1] Implement smart scroll (_should_auto_scroll) to not interrupt user review in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T017 [US1] Implement error message display with red styling for failed interactions in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [ ] T018 [US1] Implement retry count badge display when retry_count > 0 in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T019 [P] [US1] Add test for add_request creates pending entry in tests/ui/test_ai_monitor_panel.py
- [X] T020 [P] [US1] Add test for add_response completes interaction in tests/ui/test_ai_monitor_panel.py
- [X] T021 [P] [US1] Add test for failed interaction visual distinction in tests/ui/test_ai_monitor_panel.py

**Checkpoint**: User Story 1 complete - can monitor live AI interactions during crawl

---

## Phase 4: User Story 2 - Review Historical AI Interactions (Priority: P2)

**Goal**: Expand/collapse entries to view full prompt and response details

**Independent Test**: Click on an interaction entry to see full details; collapse it back

### Implementation for User Story 2

- [X] T022 [US2] Implement collapsible/expandable entry widget with expand button in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T023 [US2] Implement full prompt display in expanded view (scrollable QTextEdit) in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T024 [US2] Implement full response display in expanded view with action details in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T025 [US2] Implement parsed action display (action type, bounding box, input_text) in expanded view in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T026 [US2] Implement reasoning display in expanded view in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T027 [US2] Implement step navigation - clicking step updates display in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T028 [P] [US2] Add test for expand/collapse toggle in tests/ui/test_ai_monitor_panel.py
- [X] T029 [P] [US2] Add test for full prompt visible in expanded state in tests/ui/test_ai_monitor_panel.py

**Checkpoint**: User Story 2 complete - can review detailed AI interactions for any step

---

## Phase 5: User Story 3 - Filter and Search AI Interactions (Priority: P3)

**Goal**: Filter by success/failure and search text across interactions

**Independent Test**: Apply filter to show only failed; search for "tap" to find matching entries

### Implementation for User Story 3

- [X] T030 [US3] Add filter controls row (QComboBox for status, QLineEdit for search, QPushButton for clear) in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T031 [US3] Implement status filter dropdown (All/Success Only/Failed Only) in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T032 [US3] Implement _apply_filters() to show/hide rows based on current filter state in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T033 [US3] Implement search text input with debounced filtering (300ms QTimer) in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T034 [US3] Implement text search matching against prompt and response content in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T035 [US3] Implement filter persistence when new interactions arrive in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T036 [US3] Implement clear() method to reset all entries and filters in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T037 [P] [US3] Add test for status filter shows only matching entries in tests/ui/test_ai_monitor_panel.py
- [X] T038 [P] [US3] Add test for search filters by text content in tests/ui/test_ai_monitor_panel.py
- [X] T039 [P] [US3] Add test for clear resets all entries in tests/ui/test_ai_monitor_panel.py

**Checkpoint**: User Story 3 complete - can filter and search through AI interactions

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Performance, edge cases, and final validation

- [X] T040 [P] Add docstrings to all public methods in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T041 [P] Handle edge case: extremely long responses with "show more" truncation in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T042 [P] Handle edge case: no AI provider configured - show informative message in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T043 [P] Handle edge case: database unavailable - show graceful error without blocking crawl in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T044 Validate performance with 100+ interactions - verify no UI lag in src/mobile_crawler/ui/widgets/ai_monitor_panel.py
- [X] T045 Run quickstart.md validation scenarios manually

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verification only
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - MVP delivery
- **User Story 2 (Phase 4)**: Depends on Foundational - can parallel with US1
- **User Story 3 (Phase 5)**: Depends on Foundational - can parallel with US1/US2
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: After Foundational - delivers core monitoring value
- **User Story 2 (P2)**: After Foundational - can start after US1 or in parallel
- **User Story 3 (P3)**: After Foundational - can start after US1/US2 or in parallel

### Parallel Opportunities

Within Foundational:
- T010 (test file) can run in parallel with T002-T009

Within User Story 1:
- T019, T020, T021 (tests) can run in parallel
- T011-T018 are sequential within the same file

Within User Story 2:
- T028, T029 (tests) can run in parallel

Within User Story 3:
- T037, T038, T039 (tests) can run in parallel

Cross-Story Parallelism:
- Once Foundational completes, US1/US2/US3 can be worked in parallel by different developers

---

## Parallel Example: Foundational Phase

```bash
# Sequential widget implementation:
T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009

# Parallel test file creation:
T010 (can start immediately after T002)
```

## Parallel Example: User Story Tests

```bash
# After implementation tasks complete, tests can run in parallel:
T019 + T020 + T021  # US1 tests
T028 + T029          # US2 tests
T037 + T038 + T039   # US3 tests
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T010)
3. Complete Phase 3: User Story 1 (T011-T021)
4. **STOP and VALIDATE**: Test live AI monitoring during crawl
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → AI Monitor tab visible, basic display works
2. Add User Story 1 → Live monitoring works → Demo MVP!
3. Add User Story 2 → Can expand entries for details → Demo
4. Add User Story 3 → Can filter and search → Demo
5. Polish → Edge cases handled, documented

---

## Notes

- All implementation in single file: `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- Integration in: `src/mobile_crawler/ui/main_window.py`
- Tests in: `tests/ui/test_ai_monitor_panel.py`
- No database changes needed - uses existing AIInteraction data via signals
- Commit after each task or logical group
- Total tasks: 45
