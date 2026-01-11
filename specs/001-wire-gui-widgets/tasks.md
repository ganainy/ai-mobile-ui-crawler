# Tasks: Wire Up GUI Widgets

**Input**: Design documents from `/specs/001-wire-gui-widgets/`  
**Prerequisites**: plan.md ✓, spec.md ✓, data-model.md ✓, contracts/signals.md ✓

**Tests**: Tests explicitly requested in spec.md Success Criteria (SC-001 through SC-006). Including GUI tests as P2.

**Organization**: Tasks grouped by user story from spec.md to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: MainWindow scaffolding and service initialization

- [x] T001 Create service factory method in src/mobile_crawler/ui/main_window.py
- [x] T002 [P] Add widget imports and type hints in src/mobile_crawler/ui/main_window.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Widget instantiation and layout - MUST complete before user story wiring

**⚠️ CRITICAL**: No user story work can begin until this phase is complete
- [x] T003 Instantiate all widgets with dependencies in src/mobile_crawler/ui/main_window.py
- [x] T004 Create QSplitter layout structure (left/center/right panels) in src/mobile_crawler/ui/main_window.py
- [x] T005 Add left panel with DeviceSelector, AppSelector, AIModelSelector, SettingsPanel in src/mobile_crawler/ui/main_window.py
- [x] T006 Add center panel with CrawlControlPanel, StatsDashboard in src/mobile_crawler/ui/main_window.py
- [x] T007 [P] Add right panel with LogViewer in src/mobile_crawler/ui/main_window.py
- [x] T008 Add bottom panel with RunHistoryView in src/mobile_crawler/ui/main_window.py
- [x] T009 Create QtSignalAdapter instance and attach to CrawlerLoop in src/mobile_crawler/ui/main_window.py

**Checkpoint**: All widgets visible in main window. Foundation ready for signal wiring.

---

## Phase 3: User Story 1 - Launch GUI and Configure AI Provider (Priority: P1) 🎯 MVP

**Goal**: User launches GUI, selects AI provider, enters API key, sees available models

**Independent Test**: Launch app → select provider → enter API key → verify models populate

### Implementation for User Story 1

- [x] T010 [US1] Connect AIModelSelector.model_selected signal to MainWindow._on_model_selected in src/mobile_crawler/ui/main_window.py
- [x] T011 [US1] Implement _on_model_selected slot to store provider/model config in src/mobile_crawler/ui/main_window.py
- [x] T012 [US1] Connect SettingsPanel api_key_changed to validate and store key in src/mobile_crawler/ui/main_window.py
- [x] T013 [US1] Implement _update_start_button_state method in src/mobile_crawler/ui/main_window.py
- [x] T014 [US1] Wire ProviderRegistry to AIModelSelector for model list population in src/mobile_crawler/ui/main_window.py
- [x] T015 [US1] Wire UserConfigStore to persist API keys and preferences between sessions in src/mobile_crawler/ui/main_window.py

**Checkpoint**: User Story 1 complete. Can configure AI provider and see models.

---

## Phase 4: User Story 2 - Select Device and Target App (Priority: P1)

**Goal**: User selects connected Android device, views and selects target app

**Independent Test**: Connect device → refresh → select device → view apps → select app

### Implementation for User Story 2

- [x] T016 [US2] Connect DeviceSelector.device_selected signal to MainWindow._on_device_selected in src/mobile_crawler/ui/main_window.py
- [x] T017 [US2] Implement _on_device_selected slot to update AppSelector device in src/mobile_crawler/ui/main_window.py
- [x] T018 [US2] Connect AppSelector.app_selected signal to MainWindow._on_app_selected in src/mobile_crawler/ui/main_window.py
- [x] T019 [US2] Implement _on_app_selected slot to store selected package in src/mobile_crawler/ui/main_window.py
- [x] T020 [US2] Update _update_start_button_state to check device + app + AI configured in src/mobile_crawler/ui/main_window.py

**Checkpoint**: User Story 2 complete. Can select device and app. Start button enables when ready.

---

## Phase 5: User Story 3 - Start and Monitor a Crawl (Priority: P1)

**Goal**: User starts crawl, monitors real-time logs and stats

**Independent Test**: Configure all settings → click Start → observe logs/stats updating

### Implementation for User Story 3

- [x] T021 [US3] Connect CrawlControlPanel.start_requested to MainWindow._start_crawl in src/mobile_crawler/ui/main_window.py
- [x] T022 [US3] Implement _start_crawl slot with QThread worker in src/mobile_crawler/ui/main_window.py
- [x] T023 [US3] Create CrawlerWorker QThread class in src/mobile_crawler/ui/main_window.py
- [x] T024 [US3] Connect QtSignalAdapter.step_started to LogViewer.log_message in src/mobile_crawler/ui/main_window.py
- [x] T025 [US3] Connect QtSignalAdapter.action_executed to LogViewer.log_message in src/mobile_crawler/ui/main_window.py
- [x] T026 [US3] Connect QtSignalAdapter.step_completed to StatsDashboard.update_stats in src/mobile_crawler/ui/main_window.py
- [x] T027 [US3] Add QTimer for elapsed time updates in StatsDashboard in src/mobile_crawler/ui/main_window.py
- [x] T028 [US3] Connect QtSignalAdapter.crawl_completed to MainWindow._on_crawl_completed in src/mobile_crawler/ui/main_window.py
- [x] T029 [US3] Update button states on crawl start (disable selectors, enable Pause/Stop) in src/mobile_crawler/ui/main_window.py

**Checkpoint**: User Story 3 complete. Can run full crawl with real-time monitoring.

---

## Phase 6: User Story 4 - Pause, Resume, and Stop Crawl (Priority: P2)

**Goal**: User can pause, resume, or stop running crawl

**Independent Test**: Start crawl → pause → verify paused → resume → verify continues → stop

### Implementation for User Story 4

- [x] T030 [US4] Connect CrawlControlPanel.pause_requested to MainWindow._pause_crawl in src/mobile_crawler/ui/main_window.py
- [x] T031 [US4] Connect CrawlControlPanel.resume_requested to MainWindow._resume_crawl in src/mobile_crawler/ui/main_window.py
- [x] T032 [US4] Connect CrawlControlPanel.stop_requested to MainWindow._stop_crawl in src/mobile_crawler/ui/main_window.py
- [x] T033 [US4] Implement _pause_crawl slot to call CrawlerLoop.pause() in src/mobile_crawler/ui/main_window.py
- [x] T034 [US4] Implement _resume_crawl slot to call CrawlerLoop.resume() in src/mobile_crawler/ui/main_window.py
- [x] T035 [US4] Implement _stop_crawl slot to call CrawlerLoop.stop() in src/mobile_crawler/ui/main_window.py
- [x] T036 [US4] Update button visibility on state changes (show Resume when paused) in src/mobile_crawler/ui/main_window.py
- [x] T037 [US4] Connect QtSignalAdapter.state_changed to update control panel state in src/mobile_crawler/ui/main_window.py

**Checkpoint**: User Story 4 complete. Full crawl control available.

---

## Phase 7: User Story 5 - View Run History (Priority: P3)

**Goal**: User can view past crawl runs and their results

**Independent Test**: Complete a crawl → view run history list → select run → see details

### Implementation for User Story 5

- [x] T038 [US5] Load run history from RunRepository on MainWindow init in src/mobile_crawler/ui/main_window.py
- [x] T039 [US5] Connect _on_crawl_completed to refresh RunHistoryView in src/mobile_crawler/ui/main_window.py
- [x] T040 [US5] Connect RunHistoryView.run_selected to display run details in src/mobile_crawler/ui/main_window.py

**Checkpoint**: User Story 5 complete. History viewing functional.

---

## Phase 8: GUI Tests (Priority: P2)

**Purpose**: Verify UI behavior with pytest-qt

- [X] T041 [P] Create test fixture for MainWindow with mocked services in tests/ui/test_main_window.py
- [X] T042 [P] Test window launches with all widgets visible in tests/ui/test_main_window.py
- [X] T043 [P] Test Start button disabled when not configured in tests/ui/test_main_window.py
- [X] T044 [P] Test Start button enabled when device+app+AI configured in tests/ui/test_main_window.py
- [X] T045 [P] Test signal connections work (device_selected updates AppSelector) in tests/ui/test_main_window.py
- [X] T046 [P] Test button state changes on crawl start/pause/stop in tests/ui/test_main_window.py

**Checkpoint**: All GUI tests pass with pytest.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, documentation, cleanup

- [x] T047 [P] Add error dialogs for Appium not running in src/mobile_crawler/ui/main_window.py
- [x] T048 [P] Add error dialogs for invalid API key in src/mobile_crawler/ui/main_window.py
- [x] T049 [P] Add error dialogs for no devices found in src/mobile_crawler/ui/main_window.py
- [x] T050 [P] Update quickstart.md with final usage instructions in specs/001-wire-gui-widgets/quickstart.md
- [x] T051 Run quickstart.md validation to verify complete workflow

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase
  - US1 (AI Config) and US2 (Device/App) can run in parallel
  - US3 (Start/Monitor) depends on US1 + US2 completion
  - US4 (Pause/Resume/Stop) depends on US3 completion
  - US5 (History) can run after US3
- **Tests (Phase 8)**: Can run after Foundational, parallel to user stories
- **Polish (Phase 9)**: Depends on all stories complete

### User Story Dependencies

```
Phase 2 (Foundation)
       │
       ├───────────────┬───────────────┐
       ▼               ▼               │
   Phase 3 (US1)   Phase 4 (US2)       │
       │               │               │
       └───────┬───────┘               │
               ▼                       │
         Phase 5 (US3) ◄───────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
  Phase 6 (US4)   Phase 7 (US5)
       │               │
       └───────┬───────┘
               ▼
         Phase 9 (Polish)
```

### Parallel Opportunities

Within Foundation (Phase 2):
- T007 can run in parallel with T005, T006

Within User Story 3:
- T023, T024, T025 can run in parallel (different signal connections)

Within Tests (Phase 8):
- All test tasks (T040-T045) can run in parallel

Within Polish (Phase 9):
- All error dialog tasks (T046-T048) can run in parallel

---

## Parallel Example: Phase 8 Tests

```bash
# Launch all test tasks together:
Task: "Create test fixture for MainWindow" → tests/ui/test_main_window.py
Task: "Test window launches with all widgets" → tests/ui/test_main_window.py
Task: "Test Start button disabled" → tests/ui/test_main_window.py
Task: "Test Start button enabled" → tests/ui/test_main_window.py
Task: "Test signal connections work" → tests/ui/test_main_window.py
Task: "Test button state changes" → tests/ui/test_main_window.py
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (widget layout visible)
3. Complete Phase 3: User Story 1 (AI configuration)
4. Complete Phase 4: User Story 2 (Device/App selection)
5. Complete Phase 5: User Story 3 (Start and monitor crawl)
6. **STOP and VALIDATE**: Full crawl works end-to-end
7. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → All widgets visible in window (demo)
2. Add US1 + US2 → Can configure all settings (demo)
3. Add US3 → Can run complete crawl with monitoring (MVP!)
4. Add US4 → Full control over crawl execution
5. Add US5 → History viewing
6. Polish → Production ready

---

## Notes

- All tasks target src/mobile_crawler/ui/main_window.py (single file modification)
- Tests target tests/ui/test_main_window.py (new file)
- [P] marks parallel-safe tasks
- [Story] maps each task to specific user story
- Stop at any checkpoint to validate independently
- Commit after completing each phase
