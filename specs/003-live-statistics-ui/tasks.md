# Tasks: Live Statistics Dashboard Updates

**Branch**: `003-live-statistics-ui`  
**Input**: Design documents from `/specs/003-live-statistics-ui/`  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Project initialization and dependencies verification

- [x] T001 Verify PySide6 6.6+ is installed and compatible with current Python version
- [x] T002 Verify pytest configuration includes Qt testing support (pytest-qt)
- [x] T003 Create test fixtures directory structure: tests/unit/ and tests/integration/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add CrawlStatistics dataclass to src/mobile_crawler/ui/main_window.py with all 9 metrics
- [x] T005 Add instance variables to MainWindow.__init__() for _current_stats and _elapsed_timer
- [x] T006 Create _connect_statistics_signals() method in src/mobile_crawler/ui/main_window.py
- [x] T007 [P] Extend StepLogRepository with get_step_statistics() method in src/mobile_crawler/infrastructure/step_log_repository.py
- [x] T008 [P] Extend StepLogRepository with get_ai_statistics() method in src/mobile_crawler/infrastructure/step_log_repository.py
- [x] T009 [P] Extend StepLogRepository with count_screen_visits_for_run() method in src/mobile_crawler/infrastructure/step_log_repository.py
- [x] T010 [P] Extend ScreenRepository with count_unique_screens_for_run() method in src/mobile_crawler/infrastructure/screen_repository.py
- [x] T011 [P] Extend ScreenRepository with get_latest_screen_for_run() method in src/mobile_crawler/infrastructure/screen_repository.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Real-time Statistics Updates (Priority: P1) 🎯 MVP

**Goal**: Enable live statistics updates during active crawl showing steps, screens, AI calls, elapsed time, and progress bars

**Independent Test**: Start a crawl and verify all statistics update in real-time within 1 second of events, displaying accurate progress tracking

### Implementation for User Story 1

- [x] T012 [US1] Implement _on_crawl_started_stats() handler in src/mobile_crawler/ui/main_window.py
- [x] T013 [US1] Implement _on_step_completed_stats() handler in src/mobile_crawler/ui/main_window.py
- [x] T014 [US1] Implement _on_screenshot_captured_stats() handler in src/mobile_crawler/ui/main_window.py
- [x] T015 [US1] Implement _on_ai_response_stats() handler in src/mobile_crawler/ui/main_window.py
- [x] T016 [US1] Implement _update_dashboard_stats() central update method in src/mobile_crawler/ui/main_window.py
- [x] T017 [US1] Implement _update_elapsed_time() timer callback in src/mobile_crawler/ui/main_window.py
- [x] T018 [US1] Connect QTimer timeout signal to _update_elapsed_time in src/mobile_crawler/ui/main_window.py
- [x] T019 [US1] Call _connect_statistics_signals() in MainWindow.__init__() after widget creation
- [x] T020 [US1] Add defensive null checks to all statistics handler methods
- [x] T021 [US1] Test real-time updates: steps count increments during active crawl
- [x] T022 [US1] Test real-time updates: elapsed time updates every second
- [x] T023 [US1] Test real-time updates: progress bars advance with step/time progress
- [x] T024 [US1] Test statistics reset to zero when new crawl starts

**Checkpoint**: User Story 1 complete - users can see live statistics update during crawls

---

## Phase 4: User Story 2 - Success/Failure Rate Tracking (Priority: P2)

**Goal**: Display successful vs failed step counts to assess crawl quality

**Independent Test**: Run a crawl with intentional failures and verify successful/failed counters track correctly, with successful + failed = total

### Implementation for User Story 2

- [x] T025 [US2] Implement _on_action_executed_stats() handler in src/mobile_crawler/ui/main_window.py
- [x] T026 [US2] Add success/failure increment logic based on ActionResult.success field
- [x] T027 [US2] Update _update_dashboard_stats() to include successful_steps and failed_steps
- [x] T028 [US2] Add validation: verify total_steps == successful_steps + failed_steps
- [x] T029 [US2] Test success counter increments on successful action execution
- [x] T030 [US2] Test failure counter increments on failed action execution
- [x] T031 [US2] Test validation: sum of success + failure always equals total

**Checkpoint**: User Story 2 complete - users can assess crawl quality via success/failure rates

---

## Phase 5: User Story 3 - Screen Discovery Metrics (Priority: P2)

**Goal**: Track unique screen discovery vs revisits to understand coverage efficiency

**Independent Test**: Run crawl and verify unique screens count increases for new screens, total visits increases for all screens including revisits

### Implementation for User Story 3

- [x] T032 [US3] Add screen hash tracking to _on_screenshot_captured_stats() in src/mobile_crawler/ui/main_window.py
- [x] T033 [US3] Query latest screen hash from ScreenRepository in screenshot handler
- [x] T034 [US3] Add screen hash to unique_screen_hashes set in CrawlStatistics
- [x] T035 [US3] Increment total_screen_visits counter in CrawlStatistics
- [x] T036 [US3] Implement screens_per_minute() calculation in CrawlStatistics class
- [x] T037 [US3] Update _update_dashboard_stats() to include screens_per_minute metric
- [x] T038 [US3] Test unique screens count increases only for new screens
- [x] T039 [US3] Test total visits increases for all screen visits including revisits
- [x] T040 [US3] Test screens per minute calculation: unique_screens / (elapsed_seconds / 60)

**Checkpoint**: User Story 3 complete - users can assess crawl coverage and efficiency

---

## Phase 6: User Story 4 - AI Performance Monitoring (Priority: P3)

**Goal**: Monitor AI API call counts and average response times for cost tracking and performance analysis

**Independent Test**: Make AI calls during crawl and verify call counter and average response time update accurately

### Implementation for User Story 4

- [x] T041 [US4] Extract response_time_ms from response_data in _on_ai_response_stats()
- [x] T042 [US4] Increment ai_call_count in CrawlStatistics
- [x] T043 [US4] Append response time to ai_response_times_ms list in CrawlStatistics
- [x] T044 [US4] Implement avg_ai_response_time() calculation in CrawlStatistics class
- [x] T045 [US4] Update _update_dashboard_stats() to include AI metrics
- [x] T046 [US4] Test AI call counter increments with each AI response
- [x] T047 [US4] Test average response time calculated as running average
- [x] T048 [US4] Test response time displays in milliseconds with 0 decimal places

**Checkpoint**: User Story 4 complete - users can monitor AI performance and costs

---

## Phase 7: User Story 5 - Statistics Reset and Persistence (Priority: P3)

**Goal**: Reset statistics on new crawl start and preserve final statistics in database

**Independent Test**: Complete a crawl, start new crawl, verify statistics reset to zero; check run history for preserved final values

### Implementation for User Story 5

- [x] T049 [US5] Implement _on_crawl_completed_stats() handler in src/mobile_crawler/ui/main_window.py
- [x] T050 [US5] Stop QTimer when crawl completes in completion handler
- [x] T051 [US5] Implement _query_final_statistics() method in src/mobile_crawler/ui/main_window.py
- [x] T052 [US5] Query step statistics from StepLogRepository in final statistics method
- [x] T053 [US5] Query screen counts from ScreenRepository in final statistics method
- [x] T054 [US5] Query AI statistics from StepLogRepository in final statistics method
- [x] T055 [US5] Calculate derived metrics (screens_per_minute) in final statistics
- [x] T056 [US5] Update dashboard with database-backed final statistics
- [x] T057 [US5] Clear _current_stats object after crawl completion
- [x] T058 [US5] Test statistics reset to zero when new crawl starts
- [x] T059 [US5] Test final statistics query returns accurate database values
- [x] T060 [US5] Test statistics preserved in database after crawl completion

**Checkpoint**: User Story 5 complete - statistics reset correctly and final values preserved

---

## Phase 8: Testing & Quality Assurance

**Purpose**: Comprehensive testing of all statistics functionality

### Unit Tests

- [ ] T061 [P] Create tests/unit/test_crawl_statistics.py for CrawlStatistics class
- [ ] T062 [P] Test CrawlStatistics.avg_ai_response_time() with empty list returns 0.0
- [ ] T063 [P] Test CrawlStatistics.avg_ai_response_time() calculates correct average
- [ ] T064 [P] Test CrawlStatistics.elapsed_seconds() returns correct duration
- [ ] T065 [P] Test CrawlStatistics.screens_per_minute() with zero elapsed time returns 0.0
- [ ] T066 [P] Test CrawlStatistics.screens_per_minute() calculates correct rate
- [ ] T067 [P] Create tests/unit/test_step_log_repository_stats.py for repository methods
- [ ] T068 [P] Test StepLogRepository.get_step_statistics() with mock database
- [ ] T069 [P] Test StepLogRepository.get_ai_statistics() with mock database
- [ ] T070 [P] Test StepLogRepository.count_screen_visits_for_run() with mock database
- [ ] T071 [P] Create tests/unit/test_screen_repository_stats.py for repository methods
- [ ] T072 [P] Test ScreenRepository.count_unique_screens_for_run() with mock database
- [ ] T073 [P] Test ScreenRepository.get_latest_screen_for_run() with mock database

### Integration Tests

- [ ] T074 Create tests/integration/test_statistics_event_flow.py for full event flow
- [ ] T075 Test crawl_started signal initializes statistics and resets dashboard
- [ ] T076 Test step_completed signal increments total steps counter
- [ ] T077 Test action_executed signal updates success/failure counters
- [ ] T078 Test screenshot_captured signal updates screen discovery metrics
- [ ] T079 Test ai_response_received signal updates AI performance metrics
- [ ] T080 Test QTimer triggers elapsed time updates every second
- [ ] T081 Test crawl_completed signal queries database and updates final statistics
- [ ] T082 Test full crawl lifecycle: start → events → completion → reset

### Manual Testing

- [ ] T083 Manual test: Start GUI and run real crawl on physical device
- [ ] T084 Manual test: Verify all statistics update in real-time during crawl
- [ ] T085 Manual test: Verify progress bars advance correctly
- [ ] T086 Manual test: Verify elapsed time ticks every second
- [ ] T087 Manual test: Verify final statistics match database values after completion
- [ ] T088 Manual test: Start new crawl and verify statistics reset to zero
- [ ] T089 Manual test: Check run history view for preserved final statistics

---

## Phase 9: Polish & Documentation

**Purpose**: Code quality, documentation, and refinements

- [ ] T090 [P] Add docstrings to all new methods in MainWindow
- [ ] T091 [P] Add inline comments explaining signal handler flow
- [ ] T092 [P] Add docstrings to CrawlStatistics class and methods
- [ ] T093 [P] Add docstrings to new repository query methods
- [ ] T094 [P] Update README.md with statistics features section
- [ ] T095 [P] Add logging statements for debugging statistics updates
- [ ] T096 Code review: Verify thread safety of all signal handlers
- [ ] T097 Code review: Verify defensive null checks in all handlers
- [ ] T098 Code review: Verify division by zero protection in calculations
- [ ] T099 Performance test: Run 1000+ step crawl and verify UI remains responsive
- [ ] T100 Performance test: Verify memory usage stays under 100 KB for statistics

---

## Dependencies Graph

### User Story Completion Order

```
Phase 1 (Setup) → Phase 2 (Foundational)
                        ↓
        ┌───────────────┴───────────────┐
        ↓                               ↓
    Phase 3 (US1: P1) ─────────→   Phase 4 (US2: P2)
        │                               │
        │                               ↓
        │                          Phase 5 (US3: P2)
        │                               │
        └───────────────┬───────────────┘
                        ↓
                   Phase 6 (US4: P3)
                        ↓
                   Phase 7 (US5: P3)
                        ↓
                   Phase 8 (Testing)
                        ↓
                   Phase 9 (Polish)
```

**Critical Path**: Setup → Foundational → US1 (MVP) → Testing → Delivery

**Parallel Work**: US2, US3, US4, US5 can be developed in parallel after US1 complete

---

## Parallel Execution Examples

### Phase 2: Foundational (Maximum Parallelism)

**Team Size**: 3 developers

**Developer 1**: T004, T005, T006 (MainWindow setup)  
**Developer 2**: T007, T008, T009 (StepLogRepository extensions)  
**Developer 3**: T010, T011 (ScreenRepository extensions)

**Duration**: ~2-3 hours (if done in parallel)

---

### Phase 3: User Story 1 (Core MVP)

**Team Size**: 2 developers

**Developer 1**: T012, T013, T017, T018 (Event handlers + timer)  
**Developer 2**: T014, T015, T016, T019, T020 (Dashboard updates + wiring)

Then both: T021-T024 (Testing in parallel)

**Duration**: ~4-5 hours (if done in parallel)

---

### Phase 4-7: User Stories 2-5 (Post-MVP Features)

**Team Size**: 4 developers (one per story)

**Developer 1**: T025-T031 (US2: Success/Failure)  
**Developer 2**: T032-T040 (US3: Screen Discovery)  
**Developer 3**: T041-T048 (US4: AI Performance)  
**Developer 4**: T049-T060 (US5: Reset/Persistence)

**Duration**: ~3-4 hours per story (if done in parallel)

---

### Phase 8: Testing (Maximum Parallelism)

**Team Size**: 3 developers

**Developer 1**: T061-T066 (Unit tests for CrawlStatistics)  
**Developer 2**: T067-T073 (Unit tests for repositories)  
**Developer 3**: T074-T082 (Integration tests)

Manual testing: T083-T089 (Sequential, requires device)

**Duration**: ~3-4 hours (if done in parallel)

---

## Implementation Strategy

### MVP First (Recommended)

**Sprint 1 - MVP** (Deliver User Story 1):
- Phase 1: Setup (T001-T003) - 30 minutes
- Phase 2: Foundational (T004-T011) - 3 hours
- Phase 3: User Story 1 (T012-T024) - 5 hours
- Basic Testing (T074, T083-T084) - 1 hour

**Total MVP**: ~9 hours → **Immediate user value: Live statistics updates**

**Sprint 2 - Enhanced Metrics** (US2 + US3):
- Phase 4: User Story 2 (T025-T031) - 3 hours
- Phase 5: User Story 3 (T032-T040) - 3 hours
- Testing (T075-T079, T085-T086) - 2 hours

**Total Sprint 2**: ~8 hours → **Added value: Quality tracking + Coverage metrics**

**Sprint 3 - Advanced Features** (US4 + US5):
- Phase 6: User Story 4 (T041-T048) - 2 hours
- Phase 7: User Story 5 (T049-T060) - 3 hours
- Testing (T080-T082, T087-T089) - 2 hours

**Total Sprint 3**: ~7 hours → **Added value: AI monitoring + Persistence**

**Sprint 4 - Quality** (Complete testing + polish):
- Phase 8: Full test suite (T061-T089) - 4 hours
- Phase 9: Documentation (T090-T100) - 2 hours

**Total Sprint 4**: ~6 hours → **Production ready**

---

## Summary

**Total Tasks**: 100  
**Estimated Effort**: 30-36 hours (single developer, sequential)  
**MVP Effort**: 9 hours (User Story 1 only)  
**Parallelization Potential**: 12-15 hours (team of 3-4 developers)

**Task Breakdown**:
- Setup: 3 tasks
- Foundational: 8 tasks (blocking, but parallelizable)
- User Story 1 (P1): 13 tasks → MVP
- User Story 2 (P2): 7 tasks
- User Story 3 (P2): 9 tasks
- User Story 4 (P3): 8 tasks
- User Story 5 (P3): 12 tasks
- Testing: 29 tasks (highly parallelizable)
- Polish: 11 tasks (parallelizable)

**Critical Success Factors**:
1. Complete foundational tasks first (T004-T011) before any user story work
2. Deliver MVP (User Story 1) early for immediate user value
3. Maintain thread safety via Qt signals throughout
4. Add defensive null checks in every handler
5. Test with real devices for manual validation

**Risk Mitigation**:
- All handlers include defensive checks for null statistics
- Division by zero protected in all calculations
- Database queries have fallback to in-memory values
- Unit tests verify calculations before integration
- Integration tests verify full event flow before manual testing
