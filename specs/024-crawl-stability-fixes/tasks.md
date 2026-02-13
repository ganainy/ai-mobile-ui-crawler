# Tasks: Crawl Stability & Observability Fixes

**Input**: Design documents from `/specs/024-crawl-stability-fixes/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Tests**: Unit tests included as verification for bug fixes.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Project Type**: Single Python project with PyQt6 UI
- **Source**: `src/mobile_crawler/`
- **Tests**: `tests/unit/`, `tests/integration/`

---

## Phase 1: Setup (Configuration Changes)

**Purpose**: Add new configuration defaults and verify existing infrastructure

- [x] T001 Add `mobsf_request_timeout` config default (300s) in `src/mobile_crawler/config/defaults.py`
- [x] T002 [P] Verify existing logging infrastructure has timestamps in `src/mobile_crawler/core/log_sinks.py`

---

## Phase 2: Foundational (No Blocking Prerequisites)

**Purpose**: This feature is bug fixes to existing code - no foundational infrastructure changes required

**Note**: All user stories can proceed independently as they modify different files/functions.

**Checkpoint**: Ready to begin user story implementation

---

## Phase 3: User Story 1 - Reliable MobSF Analysis Completion (Priority: P1) 🎯 MVP

**Goal**: MobSF analysis waits long enough (10+ minutes) for large APKs to complete analysis without timeout errors

**Independent Test**: Upload a large APK, verify system waits until MobSF reports completion or extended timeout is reached

### Implementation for User Story 1

- [x] T003 [US1] Update `_make_api_request()` to use configurable timeout in `src/mobile_crawler/infrastructure/mobsf_manager.py`
- [x] T004 [US1] Add `timeout` parameter to `_make_api_request()` method signature in `src/mobile_crawler/infrastructure/mobsf_manager.py`
- [x] T005 [US1] Update `perform_complete_scan()` to pass extended timeout for PDF/JSON downloads in `src/mobile_crawler/infrastructure/mobsf_manager.py`
- [x] T006 [US1] Add progress logging during extended polling in `src/mobile_crawler/infrastructure/mobsf_manager.py`
- [x] T007 [P] [US1] Add unit test for configurable timeout in `tests/unit/test_mobsf_manager.py`

**Checkpoint**: MobSF analysis for APKs taking 5-10 minutes should complete without timeout errors

---

## Phase 4: User Story 2 - Clean PCAPdroid Session Management (Priority: P1)

**Goal**: PCAPdroid is properly stopped before starting a new crawl session, preventing capture conflicts

**Independent Test**: Start crawl, interrupt it, start new crawl - verify no PCAP file conflicts

### Implementation for User Story 2

- [x] T008 [US2] Add `_stop_any_existing_capture_async()` helper method in `src/mobile_crawler/domain/traffic_capture_manager.py`
- [x] T009 [US2] Call `_stop_any_existing_capture_async()` at start of `start_capture_async()` in `src/mobile_crawler/domain/traffic_capture_manager.py`
- [x] T010 [US2] Add brief wait (1s) after precautionary stop before starting new capture in `src/mobile_crawler/domain/traffic_capture_manager.py`
- [x] T011 [P] [US2] Add unit test for stop-before-start behavior in `tests/unit/test_traffic_capture_manager.py`

**Checkpoint**: Zero PCAP file conflicts when starting new crawl sessions

---

## Phase 5: User Story 3 - Accurate Time-Based Crawl Duration (Priority: P1)

**Goal**: Time-based crawls run for the exact configured duration, not a stale value

**Independent Test**: Set 300s in UI, start crawl, verify it runs for full 300 seconds

### Implementation for User Story 3

- [x] T012 [US3] Move `max_crawl_steps` config read from `__init__` to `run()` method in `src/mobile_crawler/core/crawler_loop.py`
- [x] T013 [US3] Move `max_crawl_duration_seconds` config read from `__init__` to `run()` method in `src/mobile_crawler/core/crawler_loop.py`
- [x] T014 [US3] Add debug log showing configured duration at crawl start in `src/mobile_crawler/core/crawler_loop.py`
- [x] T015 [P] [US3] Add unit test verifying config is read at run() time in `tests/unit/test_crawler_loop.py`

**Checkpoint**: Time-based crawls run for 100% of configured duration

---

## Phase 6: User Story 4 - Graceful Crawl Termination (Priority: P2)

**Goal**: Stop button triggers same cleanup path as normal termination, saving all artifacts

**Independent Test**: Click Stop during crawl, verify all artifacts (screenshots, PCAP, logs) are saved

### Implementation for User Story 4

- [x] T016 [US4] Extract cleanup logic into `_cleanup_crawl_session()` method in `src/mobile_crawler/core/crawler_loop.py`
- [x] T017 [US4] Call `_cleanup_crawl_session()` from both normal completion and STOPPING state handling in `src/mobile_crawler/core/crawler_loop.py`
- [x] T018 [US4] Ensure MobSF analysis is skipped gracefully if crawl was stopped early in `src/mobile_crawler/core/crawler_loop.py`
- [x] T019 [US4] Add `_stopped_early` flag to track manual stop vs natural completion in `src/mobile_crawler/core/crawler_loop.py`
- [x] T020 [P] [US4] Add unit test for graceful stop cleanup in `tests/unit/test_crawler_loop.py`

**Checkpoint**: Stop button results in all session artifacts being properly saved

---

## Phase 7: User Story 5 - Pause-Aware Timer (Priority: P2)

**Goal**: Paused time doesn't count toward crawl duration limit

**Independent Test**: Set 60s duration, pause for 30s, verify crawl runs for 60s of active time (90s wall clock)

### Implementation for User Story 5

- [x] T021 [US5] Add `_paused_duration: float` field to track cumulative pause time in `src/mobile_crawler/core/crawler_loop.py`
- [x] T022 [US5] Add `_pause_start_time: Optional[float]` field in `src/mobile_crawler/core/crawler_loop.py`
- [x] T023 [US5] Update `pause()` method to record pause start time in `src/mobile_crawler/core/crawler_loop.py`
- [x] T024 [US5] Update `resume()` method to accumulate paused duration in `src/mobile_crawler/core/crawler_loop.py`
- [x] T025 [US5] Update `_should_continue()` to subtract `_paused_duration` from elapsed time in `src/mobile_crawler/core/crawler_loop.py`
- [x] T026 [US5] Track pause time during step-by-step wait loop in `src/mobile_crawler/core/crawler_loop.py`
- [x] T027 [US5] Reset pause tracking fields in `run()` method before crawl starts in `src/mobile_crawler/core/crawler_loop.py`
- [x] T028 [P] [US5] Add unit test for pause-aware timer behavior in `tests/unit/test_crawler_loop.py`

**Checkpoint**: Paused crawls show 0 seconds advancement during pause

---

## Phase 8: User Story 6 - OCR Performance Statistics (Priority: P3)

**Goal**: Average OCR operation time is tracked and displayed in crawl statistics

**Independent Test**: Run crawl with OCR, verify average OCR time appears in statistics

### Implementation for User Story 6

- [x] T029 [US6] Add `_ocr_total_time: float` field in `src/mobile_crawler/core/crawler_loop.py`
- [x] T030 [US6] Add `_ocr_operation_count: int` field in `src/mobile_crawler/core/crawler_loop.py`
- [x] T031 [US6] Accumulate OCR timing in `_execute_step()` after grounding operation in `src/mobile_crawler/core/crawler_loop.py`
- [x] T032 [US6] Calculate OCR average and include in `on_crawl_completed` event in `src/mobile_crawler/core/crawler_loop.py`
- [x] T033 [US6] Reset OCR tracking fields at start of `run()` method in `src/mobile_crawler/core/crawler_loop.py`
- [x] T034 [P] [US6] Add OCR average time display to statistics panel (if exists) in `src/mobile_crawler/ui/widgets/`
- [x] T035 [P] [US6] Add unit test for OCR statistics accumulation in `tests/unit/test_crawler_loop_ocr_stats.py`

**Checkpoint**: OCR average time is visible in statistics after crawl completion

---

## Phase 9: User Story 7 - Timestamped Logs (Priority: P3)

**Goal**: Every log message includes a timestamp in consistent format

**Independent Test**: Check any log output and verify timestamps are present

### Implementation for User Story 7

- [x] T036 [US7] Audit `src/mobile_crawler/core/log_sinks.py` - verify all sinks include timestamps (expected: already done)
- [x] T037 [US7] Verify UI LogViewer displays timestamps in `src/mobile_crawler/ui/widgets/log_viewer.py`
- [x] T038 [US7] Search for any `print()` statements in production code and replace with logger calls
- [x] T039 [P] [US7] Add verification test that log output includes timestamps in `tests/unit/test_logging.py`

**Checkpoint**: 100% of log messages include timestamps in consistent format

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and integration testing

- [ ] T040 [P] Create integration test file `tests/integration/test_crawl_stability.py`
- [ ] T041 Add integration test for pause/resume timer behavior in `tests/integration/test_crawl_stability.py`
- [ ] T042 Add integration test for stop button cleanup in `tests/integration/test_crawl_stability.py`
- [ ] T043 [P] Update README.md with any new configuration options
- [ ] T044 Run full test suite and verify no regressions
- [ ] T045 Manual verification using quickstart.md checklist

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: No blocking tasks (skip)
- **User Stories (Phase 3-9)**: Can proceed in parallel as they modify different files
  - P1 stories (US1, US2, US3) are highest priority
  - P2 stories (US4, US5) are medium priority
  - P3 stories (US6, US7) are lower priority
- **Polish (Phase 10)**: Depends on all user stories being complete

### User Story Dependencies

| Story | Depends On | Can Run In Parallel With |
|-------|-----------|-------------------------|
| US1 (MobSF timeout) | T001 (config) | US2, US7 (different files) |
| US2 (PCAPdroid) | None | US1, US3, US7 (different files) |
| US3 (Time mode) | None | US1, US2, US4, US5, US6, US7 |
| US4 (Graceful stop) | None | US1, US2 |
| US5 (Pause timer) | US3 (same file) | US1, US2 |
| US6 (OCR stats) | US3, US4, US5 (same file, logical order) | US1, US2, US7 |
| US7 (Timestamps) | None | US1, US2 (different files) |

### Within Each User Story

- Implementation tasks in order listed
- Unit test can run in parallel with implementation (different file)
- Complete story before moving to next priority

### Parallel Opportunities

**Maximum parallelism with 3 developers:**
```
Developer A: US1 (MobSF) → US4 (Graceful stop)
Developer B: US2 (PCAPdroid) → US7 (Timestamps)  
Developer C: US3 (Time mode) → US5 (Pause timer) → US6 (OCR stats)
```

---

## Parallel Example: User Story 1

```bash
# These tasks can run in parallel (different files):
Task T003: Update _make_api_request() in mobsf_manager.py
Task T007: Add unit test in tests/unit/test_mobsf_manager.py

# These must be sequential (same file, logical dependency):
Task T003 → T004 → T005 → T006
```

---

## Parallel Example: User Story 5

```bash
# Implementation tasks (sequential, same file):
Task T021 → T022 → T023 → T024 → T025 → T026 → T027

# Test can run in parallel with implementation:
Task T028: Add unit test (different file)
```

---

## Implementation Strategy

### MVP First (P1 Stories Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 3: User Story 1 - MobSF timeout (T003-T007)
3. Complete Phase 4: User Story 2 - PCAPdroid cleanup (T008-T011)
4. Complete Phase 5: User Story 3 - Time mode fix (T012-T015)
5. **STOP and VALIDATE**: Test all P1 stories
6. Deploy if critical fixes are needed

### Incremental Delivery

1. Complete P1 stories → Test → Deploy (critical bug fixes)
2. Add P2 stories (US4, US5) → Test → Deploy (user experience)
3. Add P3 stories (US6, US7) → Test → Deploy (observability)
4. Complete Polish phase → Final validation

### Recommended Order (Single Developer)

1. T001-T002 (Setup)
2. T003-T007 (US1 - MobSF) - Critical P1
3. T008-T011 (US2 - PCAPdroid) - Critical P1
4. T012-T015 (US3 - Time mode) - Critical P1
5. T016-T020 (US4 - Graceful stop) - P2
6. T021-T028 (US5 - Pause timer) - P2
7. T029-T035 (US6 - OCR stats) - P3
8. T036-T039 (US7 - Timestamps) - P3 (mostly verification)
9. T040-T045 (Polish)

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- US3, US4, US5, US6 all modify `crawler_loop.py` - implement in order to avoid conflicts
- US7 is mostly verification of existing functionality
- Commit after each completed user story
- Run existing tests after each story to verify no regressions
