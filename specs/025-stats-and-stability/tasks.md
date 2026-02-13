# Tasks: Statistics Display and Crawl Stability Improvements

**Input**: Design documents from `/specs/025-stats-and-stability/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Tests are OPTIONAL for this feature. Unit tests are included for critical components.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## User Stories Summary

| Story | Priority | Title |
|-------|----------|-------|
| US1 | P1 | View OCR Processing Time in Statistics |
| US2 | P1 | View Action Execution Timing in Statistics |
| US3 | P2 | View Timing Breakdown for Operations (Screenshot timing) |
| US4 | P1 | Crawl Respects Configured Duration Limit |
| US5 | P2 | PCAPdroid Capture Starts Without Permission Prompt |
| US6 | P2 | Video Recording Starts Successfully |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Extension of existing event infrastructure for timing events

- [X] T001 Add `on_ocr_completed` method stub to `CrawlerEventListener` in `src/mobile_crawler/core/crawler_event_listener.py`
- [X] T002 [P] Add `on_screenshot_timing` method stub to `CrawlerEventListener` in `src/mobile_crawler/core/crawler_event_listener.py`
- [X] T003 [P] Add `ocr_completed` Signal to `QtSignalAdapter` in `src/mobile_crawler/ui/signal_adapter.py`
- [X] T004 [P] Add `screenshot_timing` Signal to `QtSignalAdapter` in `src/mobile_crawler/ui/signal_adapter.py`
- [X] T005 Add `on_ocr_completed` handler method to `QtSignalAdapter` in `src/mobile_crawler/ui/signal_adapter.py`
- [X] T006 Add `on_screenshot_timing` handler method to `QtSignalAdapter` in `src/mobile_crawler/ui/signal_adapter.py`

**Checkpoint**: Event infrastructure extended - all timing events can now be emitted and received

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend `CrawlStatistics` dataclass with timing accumulators (required by all timing stories)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Add OCR timing fields (`ocr_total_time_ms`, `ocr_operation_count`) to `CrawlStatistics` in `src/mobile_crawler/ui/main_window.py`
- [X] T008 [P] Add action timing fields (`action_total_time_ms`, `action_count`) to `CrawlStatistics` in `src/mobile_crawler/ui/main_window.py`
- [X] T009 [P] Add screenshot timing fields (`screenshot_total_time_ms`, `screenshot_count`) to `CrawlStatistics` in `src/mobile_crawler/ui/main_window.py`
- [X] T010 Add `avg_ocr_time_ms()` method to `CrawlStatistics` in `src/mobile_crawler/ui/main_window.py`
- [X] T011 [P] Add `avg_action_time_ms()` method to `CrawlStatistics` in `src/mobile_crawler/ui/main_window.py`
- [X] T012 [P] Add `avg_screenshot_time_ms()` method to `CrawlStatistics` in `src/mobile_crawler/ui/main_window.py`
- [X] T013 Connect `ocr_completed` signal to handler in `MainWindow._setup_central_widget()` in `src/mobile_crawler/ui/main_window.py`
- [X] T014 Connect `screenshot_timing` signal to handler in `MainWindow._setup_central_widget()` in `src/mobile_crawler/ui/main_window.py`

**Checkpoint**: Foundation ready - CrawlStatistics can track all timing metrics

---

## Phase 3: User Story 1 - View OCR Processing Time in Statistics (Priority: P1) 🎯 MVP

**Goal**: Display average OCR processing time in the Statistics panel in real-time

**Independent Test**: Start a crawl and verify the "OCR Avg: Xms" metric appears and updates after each step

### Implementation for User Story 1

- [X] T015 [US1] Emit `on_ocr_completed` event after grounding completes in `CrawlerLoop._execute_step()` in `src/mobile_crawler/core/crawler_loop.py`
- [X] T016 [US1] Add "Operation Timing" section header label to `StatsDashboard._setup_ui()` in `src/mobile_crawler/ui/widgets/stats_dashboard.py`
- [X] T017 [US1] Add `ocr_avg_label` QLabel to `StatsDashboard._setup_ui()` in `src/mobile_crawler/ui/widgets/stats_dashboard.py`
- [X] T018 [US1] Add `ocr_avg_ms` parameter to `StatsDashboard.update_stats()` in `src/mobile_crawler/ui/widgets/stats_dashboard.py`
- [X] T019 [US1] Update `ocr_avg_label` in `StatsDashboard.update_stats()` in `src/mobile_crawler/ui/widgets/stats_dashboard.py`
- [X] T020 [US1] Add `_on_ocr_completed` handler to accumulate OCR timing in `MainWindow` in `src/mobile_crawler/ui/main_window.py`
- [X] T021 [US1] Call `stats_dashboard.update_stats()` with OCR timing from handler in `src/mobile_crawler/ui/main_window.py`
- [X] T022 [US1] Reset OCR timing fields in `StatsDashboard.reset()` in `src/mobile_crawler/ui/widgets/stats_dashboard.py`

**Checkpoint**: OCR average time is displayed and updates in real-time during crawl

---

## Phase 4: User Story 2 - View Action Execution Timing in Statistics (Priority: P1)

**Goal**: Display average action execution time in the Statistics panel in real-time

**Independent Test**: Start a crawl with multiple actions and verify "Action Avg: Xms" updates after each action

### Implementation for User Story 2

- [X] T023 [US2] Add action timing tracking (start time before action) in `CrawlerLoop._execute_action_with_recovery()` in `src/mobile_crawler/core/crawler_loop.py`
- [X] T024 [US2] Calculate action duration and add to existing `on_action_executed` event emission in `src/mobile_crawler/core/crawler_loop.py`
- [X] T025 [US2] Add `action_avg_label` QLabel to `StatsDashboard._setup_ui()` in `src/mobile_crawler/ui/widgets/stats_dashboard.py`
- [X] T026 [US2] Add `action_avg_ms` parameter to `StatsDashboard.update_stats()` in `src/mobile_crawler/ui/widgets/stats_dashboard.py`
- [X] T027 [US2] Update `_on_action_executed` to accumulate action timing in `MainWindow` in `src/mobile_crawler/ui/main_window.py`
- [X] T028 [US2] Call `stats_dashboard.update_stats()` with action timing after each action in `src/mobile_crawler/ui/main_window.py`

**Checkpoint**: Action average time is displayed and updates in real-time during crawl

---

## Phase 5: User Story 3 - View Timing Breakdown for Operations (Priority: P2)

**Goal**: Display screenshot capture average time to complete the "Operation Timing" section

**Independent Test**: Start a crawl and verify all 4 timing metrics (OCR, AI, Action, Screenshot) appear in Statistics panel

### Implementation for User Story 3

- [X] T029 [US3] Add screenshot timing measurement in `CrawlerLoop._execute_step()` before/after capture in `src/mobile_crawler/core/crawler_loop.py`
- [X] T030 [US3] Emit `on_screenshot_timing` event after screenshot capture in `src/mobile_crawler/core/crawler_loop.py`
- [X] T031 [US3] Add `screenshot_avg_label` QLabel to `StatsDashboard._setup_ui()` in `src/mobile_crawler/ui/widgets/stats_dashboard.py`
- [X] T032 [US3] Add `screenshot_avg_ms` parameter to `StatsDashboard.update_stats()` in `src/mobile_crawler/ui/widgets/stats_dashboard.py`
- [X] T033 [US3] Add `_on_screenshot_timing` handler to accumulate screenshot timing in `MainWindow` in `src/mobile_crawler/ui/main_window.py`
- [X] T034 [US3] Call `stats_dashboard.update_stats()` with screenshot timing in `src/mobile_crawler/ui/main_window.py`

**Checkpoint**: All 4 timing metrics (OCR, AI, Action, Screenshot) are displayed in Statistics panel

---

## Phase 6: User Story 4 - Crawl Respects Configured Duration Limit (Priority: P1)

**Goal**: Fix early crawl termination and improve completion reason logging

**Independent Test**: Configure 120-second duration, start crawl on multi-screen app, verify it runs ~120 seconds

### Implementation for User Story 4

- [ ] T035 [US4] Add detailed logging when `_execute_step()` returns False in `src/mobile_crawler/core/crawler_loop.py`
- [ ] T036 [US4] Improve `_get_completion_reason()` to return specific reasons in `src/mobile_crawler/core/crawler_loop.py`
- [ ] T037 [US4] Add logging for duration limit config values at crawl start in `CrawlerLoop.run()` in `src/mobile_crawler/core/crawler_loop.py`
- [ ] T038 [US4] Verify `max_crawl_duration_seconds` is correctly read from UI in `_create_config_manager()` in `src/mobile_crawler/ui/main_window.py`
- [ ] T039 [US4] Add debug logging in `_should_continue()` showing time remaining in `src/mobile_crawler/core/crawler_loop.py`
- [ ] T040 [US4] Ensure `signup_completed` flag only stops crawl when appropriate in `src/mobile_crawler/core/crawler_loop.py`

**Checkpoint**: Crawl runs for configured duration unless valid early exit reason exists

---

## Phase 7: User Story 5 - PCAPdroid Capture Starts Without Permission Prompt (Priority: P2)

**Goal**: Improve PCAPdroid integration to avoid permission dialogs

**Independent Test**: Configure PCAPdroid API key, enable traffic capture, start crawl, verify no permission dialog appears

### Implementation for User Story 5

- [ ] T041 [US5] Add pre-flight check for PCAPdroid API control status in `TrafficCaptureManager.start_capture_async()` in `src/mobile_crawler/domain/traffic_capture_manager.py`
- [ ] T042 [US5] Add warning message when API key is not configured in `TrafficCaptureManager` in `src/mobile_crawler/domain/traffic_capture_manager.py`
- [ ] T043 [US5] Add user guidance message about configuring PCAPdroid API key correctly in `src/mobile_crawler/domain/traffic_capture_manager.py`
- [ ] T044 [US5] Add pre-crawl validation for traffic capture config in `MainWindow._can_start_crawl()` in `src/mobile_crawler/ui/main_window.py`
- [ ] T045 [US5] Log PCAPdroid configuration status at crawl start in `CrawlerLoop._initialize_traffic_capture()` in `src/mobile_crawler/core/crawler_loop.py`

**Checkpoint**: PCAPdroid starts without permission dialog when API key is properly configured

---

## Phase 8: User Story 6 - Video Recording Starts Successfully (Priority: P2)

**Goal**: Handle video recording initialization errors gracefully

**Independent Test**: Enable video recording, start crawl, verify no "No such process" errors and crawl continues

### Implementation for User Story 6

- [ ] T046 [US6] Add try-except wrapper for "No such process" error in `AppiumDriver.start_recording_screen()` in `src/mobile_crawler/infrastructure/appium_driver.py`
- [ ] T047 [US6] Return success if pre-cleanup fails with "No such process" in `src/mobile_crawler/infrastructure/appium_driver.py`
- [ ] T048 [US6] Add retry logic for recording start if first attempt fails in `VideoRecordingManager.start_recording()` in `src/mobile_crawler/domain/video_recording_manager.py`
- [ ] T049 [US6] Ensure crawl continues if video recording fails (graceful degradation) in `CrawlerLoop._initialize_video_recording()` in `src/mobile_crawler/core/crawler_loop.py`
- [ ] T050 [US6] Add user notification when video recording fails to start in `src/mobile_crawler/core/crawler_loop.py`

**Checkpoint**: Video recording starts successfully or degrades gracefully without blocking crawl

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and cleanup

- [X] T051 [P] Update quickstart.md with verification steps in `specs/025-stats-and-stability/quickstart.md`
- [X] T052 [P] Add unit tests for `CrawlStatistics` avg methods in `tests/unit/test_crawl_statistics.py`
- [X] T053 [P] Add unit tests for `StatsDashboard` timing display in `tests/unit/test_stats_dashboard.py`
- [X] T054 Run manual verification using quickstart.md scenarios
- [X] T055 Update README if any new configuration options added

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Phase 2 completion
  - US1, US2, US4 are P1 priority - implement first
  - US3, US5, US6 are P2 priority - implement after P1 stories
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Phase 2 - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Phase 2 - Builds on US1/US2 UI sections
- **User Story 4 (P1)**: Can start after Phase 2 - Independent of timing stories
- **User Story 5 (P2)**: Can start after Phase 2 - Independent stability fix
- **User Story 6 (P2)**: Can start after Phase 2 - Independent stability fix

### Within Each User Story

- Core logic before UI updates
- Signal/event emission before signal handling
- Accumulator updates before display updates

### Parallel Opportunities

- Phase 1: T001-T006 can mostly run in parallel (separate methods/signals)
- Phase 2: T007-T012 can run in parallel (separate fields/methods)
- US1 + US2 + US4: Can be developed in parallel (different subsystems)
- US5 + US6: Can be developed in parallel (different managers)
- Phase 9: All tasks can run in parallel

---

## Parallel Example: P1 Stories

```bash
# After Phase 2 completes, launch P1 stories in parallel:

# Developer A: User Story 1 (OCR timing)
Task: "Emit on_ocr_completed event after grounding in crawler_loop.py"
Task: "Add ocr_avg_label to StatsDashboard"

# Developer B: User Story 2 (Action timing)  
Task: "Add action timing tracking in crawler_loop.py"
Task: "Add action_avg_label to StatsDashboard"

# Developer C: User Story 4 (Duration enforcement)
Task: "Add detailed logging when _execute_step returns False"
Task: "Improve _get_completion_reason"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 4 Only)

1. Complete Phase 1: Setup (event infrastructure)
2. Complete Phase 2: Foundational (CrawlStatistics extension)
3. Complete Phase 3: User Story 1 (OCR timing display)
4. Complete Phase 6: User Story 4 (Duration enforcement)
5. **STOP and VALIDATE**: Test independently
6. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. Add US1 (OCR timing) → Test → Demo (visible timing metric!)
3. Add US2 (Action timing) → Test → Demo
4. Add US4 (Duration fix) → Test → Demo (stability improvement!)
5. Add US3 (Screenshot timing) → Test → Demo (complete timing section)
6. Add US5 + US6 (PCAPdroid + Video) → Test → Demo (stability polish)
7. Polish phase

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
