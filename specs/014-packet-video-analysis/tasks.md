# Tasks: Packet Capture, Video Recording, and Security Analysis Integration

**Input**: Design documents from `/specs/014-packet-video-analysis/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included for critical components to ensure reliability.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below assume single project structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure validation

- [x] T001 Verify existing project structure matches plan.md requirements
- [x] T002 [P] Verify dependencies are installed: appium-python-client, requests, PySide6
- [x] T003 [P] Review reference project code in old-project-for-refrence/domain/ and old-project-for-refrence/infrastructure/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add feature configuration keys to src/mobile_crawler/config/defaults.py (ENABLE_TRAFFIC_CAPTURE, ENABLE_VIDEO_RECORDING, ENABLE_MOBSF_ANALYSIS, PCAPDROID_PACKAGE, PCAPDROID_ACTIVITY, PCAPDROID_API_KEY, TRAFFIC_CAPTURE_OUTPUT_DIR, MOBSF_API_URL, MOBSF_API_KEY, MOBSF_SCAN_TIMEOUT, MOBSF_POLL_INTERVAL)
- [x] T005 [P] Create ADB client wrapper in src/mobile_crawler/infrastructure/adb_client.py (if not exists) for async ADB command execution
- [x] T006 [P] Review existing SessionFolderManager to ensure it supports path template resolution for feature output directories

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Enable Network Traffic Capture During Crawl (Priority: P1) 🎯 MVP

**Goal**: Users can enable PCAPDroid traffic capture via CLI or UI, and the system automatically captures network traffic during crawl sessions, saving PCAP files to session directories.

**Independent Test**: Start a crawl with `--enable-traffic-capture` flag, verify PCAP file is created in session directory, confirm file contains network traffic data.

### Tests for User Story 1

- [ ] T007 [P] [US1] Create unit test for TrafficCaptureManager in tests/domain/test_traffic_capture_manager.py (test start/stop, error handling, configuration validation)
- [ ] T008 [P] [US1] Create integration test for traffic capture CLI workflow in tests/integration/test_traffic_capture_cli.py

### Implementation for User Story 1

- [x] T009 [US1] Enhance TrafficCaptureManager in src/mobile_crawler/domain/traffic_capture_manager.py with async ADB command execution pattern from reference project
- [x] T010 [US1] Implement async start_capture_async() method in src/mobile_crawler/domain/traffic_capture_manager.py with PCAPdroid intent API integration
- [x] T011 [US1] Implement async stop_capture_and_pull_async() method in src/mobile_crawler/domain/traffic_capture_manager.py with file pull and cleanup
- [x] T012 [US1] Implement async get_capture_status_async() method in src/mobile_crawler/domain/traffic_capture_manager.py for status queries
- [x] T013 [US1] Add error handling and graceful degradation in src/mobile_crawler/domain/traffic_capture_manager.py (PCAPdroid not installed, ADB failures)
- [x] T014 [US1] Add filename generation with run_id, step_num, timestamp, package in src/mobile_crawler/domain/traffic_capture_manager.py
- [x] T015 [US1] Add CLI flag --enable-traffic-capture to src/mobile_crawler/cli/commands/crawl.py
- [x] T016 [US1] Integrate TrafficCaptureManager initialization in src/mobile_crawler/cli/commands/crawl.py based on config flag
- [x] T017 [US1] Add traffic capture lifecycle hooks to src/mobile_crawler/core/crawler_loop.py (start at crawl start, stop at crawl completion)
- [x] T018 [US1] Add UI checkbox for traffic capture enable/disable in src/mobile_crawler/ui/widgets/settings_panel.py (or appropriate settings widget)
- [x] T019 [US1] Add traffic capture configuration fields to UI settings in src/mobile_crawler/ui/widgets/settings_panel.py (PCAPdroid package, API key, output directory)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Users can enable traffic capture via CLI or UI, and PCAP files are saved to session directories.

---

## Phase 4: User Story 2 - Record Video of Crawl Session (Priority: P1)

**Goal**: Users can enable video recording via CLI or UI, and the system automatically records the crawl session, saving MP4 files to session directories.

**Independent Test**: Start a crawl with `--enable-video-recording` flag, verify MP4 file is created in session directory, confirm video contains crawl session footage.

### Tests for User Story 2

- [ ] T020 [P] [US2] Create unit test for VideoRecordingManager in tests/domain/test_video_recording_manager.py (test start/stop, error handling, base64 decoding)
- [ ] T021 [P] [US2] Create integration test for video recording CLI workflow in tests/integration/test_video_recording_cli.py

### Implementation for User Story 2

- [x] T022 [US2] Enhance VideoRecordingManager in src/mobile_crawler/domain/video_recording_manager.py with Appium recording methods from reference project
- [x] T023 [US2] Implement start_recording() method in src/mobile_crawler/domain/video_recording_manager.py using Appium driver's start_recording_screen()
- [x] T024 [US2] Implement stop_recording_and_save() method in src/mobile_crawler/domain/video_recording_manager.py with base64 decoding and file saving
- [x] T025 [US2] Implement save_partial_on_crash() method in src/mobile_crawler/domain/video_recording_manager.py for error recovery
- [x] T026 [US2] Add error handling and graceful degradation in src/mobile_crawler/domain/video_recording_manager.py (device doesn't support recording)
- [x] T027 [US2] Add filename generation with run_id, step_num, timestamp, package in src/mobile_crawler/domain/video_recording_manager.py
- [x] T028 [US2] Add CLI flag --enable-video-recording to src/mobile_crawler/cli/commands/crawl.py
- [x] T029 [US2] Integrate VideoRecordingManager initialization in src/mobile_crawler/cli/commands/crawl.py based on config flag
- [x] T030 [US2] Add video recording lifecycle hooks to src/mobile_crawler/core/crawler_loop.py (start at crawl start, stop at crawl completion, partial save on error)
- [x] T031 [US2] Add UI checkbox for video recording enable/disable in src/mobile_crawler/ui/widgets/settings_panel.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Users can enable traffic capture and/or video recording, and artifacts are saved correctly.

---

## Phase 5: User Story 3 - Perform Static Security Analysis with MobSF (Priority: P2)

**Goal**: Users can enable MobSF analysis via CLI or UI, and the system automatically extracts APK, uploads to MobSF, runs scan, and saves PDF/JSON reports after crawl completion.

**Independent Test**: Start a crawl with `--enable-mobsf-analysis` flag (with MobSF server running), verify APK is extracted, scan completes, PDF/JSON reports are saved to session directory.

### Tests for User Story 3

- [ ] T033 [P] [US3] Enhance existing unit tests for MobSFManager in tests/infrastructure/test_mobsf_manager.py (test complete workflow, error handling, API integration)
- [ ] T034 [P] [US3] Create integration test for MobSF analysis CLI workflow in tests/integration/test_mobsf_analysis_cli.py

### Implementation for User Story 3

- [x] T035 [US3] Enhance MobSFManager in src/mobile_crawler/infrastructure/mobsf_manager.py with complete analysis workflow from reference project
- [x] T036 [US3] Implement extract_apk_from_device() method in src/mobile_crawler/infrastructure/mobsf_manager.py using ADB pm path and adb pull
- [x] T037 [US3] Implement upload_apk() method in src/mobile_crawler/infrastructure/mobsf_manager.py with MobSF REST API integration
- [x] T038 [US3] Implement scan_apk() method in src/mobile_crawler/infrastructure/mobsf_manager.py with scan initiation
- [x] T039 [US3] Implement get_scan_logs() method in src/mobile_crawler/infrastructure/mobsf_manager.py for progress monitoring
- [x] T040 [US3] Implement polling loop with timeout in src/mobile_crawler/infrastructure/mobsf_manager.py for scan completion with progress updates for CLI output/logs
- [x] T041 [US3] Implement get_pdf_report() and get_report_json() methods in src/mobile_crawler/infrastructure/mobsf_manager.py
- [x] T042 [US3] Implement save_pdf_report() and save_json_report() methods in src/mobile_crawler/infrastructure/mobsf_manager.py
- [x] T043 [US3] Implement get_security_score() method in src/mobile_crawler/infrastructure/mobsf_manager.py
- [x] T044 [US3] Implement perform_complete_scan() method in src/mobile_crawler/infrastructure/mobsf_manager.py orchestrating full workflow
- [x] T045 [US3] Add error handling and graceful degradation in src/mobile_crawler/infrastructure/mobsf_manager.py (server unreachable, API key invalid, timeout)
- [x] T046 [US3] Add CLI flag --enable-mobsf-analysis to src/mobile_crawler/cli/commands/crawl.py
- [x] T047 [US3] Integrate MobSFManager initialization in src/mobile_crawler/cli/commands/crawl.py based on config flag
- [x] T048 [US3] Add MobSF analysis lifecycle hook to src/mobile_crawler/core/crawler_loop.py (run after crawl completion)
- [x] T049 [US3] Update run repository to store MobSF security scores in src/mobile_crawler/infrastructure/run_repository.py (fields already exist in schema)
- [x] T050 [US3] Add UI checkbox for MobSF analysis enable/disable in src/mobile_crawler/ui/widgets/settings_panel.py
- [x] T051 [US3] Add MobSF configuration fields to UI settings in src/mobile_crawler/ui/widgets/settings_panel.py (API URL, API key)
- [ ] T052 [US3] Create MobSF connection test widget in src/mobile_crawler/ui/widgets/mobsf_widget.py for testing server connectivity
- [x] T053 [US3] Add MobSF status display to UI during analysis in appropriate UI widget (progress widget/status bar) and ensure CLI progress output is implemented in T040

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work independently. Users can enable any combination of features, and all artifacts are saved correctly.

---

## Phase 6: User Story 4 - Configure Features via Settings (Priority: P2)

**Goal**: Users can configure feature settings (API keys, output directories, server URLs) through CLI configuration files and UI settings panels, with validation and persistence.

**Independent Test**: Set configuration values via CLI config or UI, start a crawl, verify features use the configured settings, verify settings persist across sessions.

### Tests for User Story 4

- [ ] T054 [P] [US4] Create unit test for configuration validation in tests/config/test_feature_config.py
- [ ] T055 [P] [US4] Create integration test for configuration persistence in tests/integration/test_config_persistence.py

### Implementation for User Story 4

- [x] T056 [US4] Add configuration validation for feature settings in src/mobile_crawler/config/config_manager.py (URL validation, path template validation, required fields)
- [x] T057 [US4] Add UI validation for MobSF API URL format in src/mobile_crawler/ui/widgets/settings_panel.py
- [x] T058 [US4] Add UI validation for path templates in src/mobile_crawler/ui/widgets/settings_panel.py
- [x] T059 [US4] Add error messages for invalid configuration in src/mobile_crawler/ui/widgets/settings_panel.py
- [x] T060 [US4] Ensure configuration persistence works correctly for all feature settings in src/mobile_crawler/infrastructure/user_config_store.py
- [x] T061 [US4] Add configuration documentation/comments for feature settings in src/mobile_crawler/config/defaults.py

**Checkpoint**: At this point, all user stories should be independently functional with proper configuration support. Settings persist and validate correctly.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T062 [P] Add comprehensive logging for all feature operations in src/mobile_crawler/domain/traffic_capture_manager.py, src/mobile_crawler/domain/video_recording_manager.py, src/mobile_crawler/infrastructure/mobsf_manager.py
- [x] T063 [P] Add error message improvements with troubleshooting guidance in all manager classes
- [x] T064 [P] Add prerequisite validation before feature initialization (PCAPdroid installed, MobSF reachable, device video support) in src/mobile_crawler/core/pre_crawl_validator.py
- [x] T065 [P] Update documentation in README.md with feature usage instructions
- [ ] T066 [P] Run quickstart.md validation scenarios from specs/014-packet-video-analysis/quickstart.md
- [ ] T067 [P] Add integration tests for multiple features running simultaneously in tests/integration/test_feature_integration.py
- [ ] T068 [P] Add edge case handling tests (device storage full, network interruption, timeout scenarios) in tests/integration/test_feature_edge_cases.py
- [x] T069 Code cleanup and refactoring across all feature implementations
- [x] T070 Verify graceful degradation works correctly (crawl succeeds even if all features fail)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1) and User Story 2 (P1) can proceed in parallel after Foundational
  - User Story 3 (P2) can start after Foundational (may use managers from US1/US2 but independently testable)
  - User Story 4 (P2) can start after Foundational (supports all previous stories)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories (can run in parallel with US1)
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Uses MobSFManager independently, no dependencies on US1/US2
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Supports all features but independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Manager implementation before CLI/UI integration
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, User Stories 1 and 2 can start in parallel (both P1)
- All tests for a user story marked [P] can run in parallel
- Manager implementations within different stories can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Create unit test for TrafficCaptureManager in tests/domain/test_traffic_capture_manager.py"
Task: "Create integration test for traffic capture CLI workflow in tests/integration/test_traffic_capture_cli.py"

# After tests, implement manager methods (sequential within manager):
Task: "Enhance TrafficCaptureManager in src/mobile_crawler/domain/traffic_capture_manager.py"
Task: "Implement async start_capture_async() method..."
Task: "Implement async stop_capture_and_pull_async() method..."

# Then integrate (sequential):
Task: "Add CLI flag --enable-traffic-capture to src/mobile_crawler/cli/commands/crawl.py"
Task: "Add traffic capture lifecycle hooks to src/mobile_crawler/core/crawler_loop.py"
Task: "Add UI checkbox for traffic capture enable/disable..."
```

---

## Parallel Example: User Stories 1 and 2

```bash
# After Foundational phase, both P1 stories can run in parallel:

# Developer A: User Story 1 (Traffic Capture)
Task: "Enhance TrafficCaptureManager..."
Task: "Implement async start_capture_async()..."
Task: "Add CLI flag --enable-traffic-capture..."

# Developer B: User Story 2 (Video Recording)
Task: "Enhance VideoRecordingManager..."
Task: "Implement start_recording()..."
Task: "Add CLI flag --enable-video-recording..."

# Both integrate into crawler_loop.py (coordinate merge):
Task: "Add traffic capture lifecycle hooks to src/mobile_crawler/core/crawler_loop.py"
Task: "Add video recording lifecycle hooks to src/mobile_crawler/core/crawler_loop.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Traffic Capture)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (Traffic Capture) → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 (Video Recording) → Test independently → Deploy/Demo
4. Add User Story 3 (MobSF Analysis) → Test independently → Deploy/Demo
5. Add User Story 4 (Configuration) → Test independently → Deploy/Demo
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Traffic Capture)
   - Developer B: User Story 2 (Video Recording)
   - Developer C: User Story 3 (MobSF Analysis) - can start after US1/US2 or in parallel
3. Stories complete and integrate independently
4. Developer D: User Story 4 (Configuration) - supports all features

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Reference project code is in `old-project-for-refrence/domain/` and `old-project-for-refrence/infrastructure/`
- All features must fail gracefully without stopping crawl execution
- Configuration keys follow UPPER_SNAKE_CASE convention
- Session directory structure uses path templates that resolve at runtime

---

## Task Summary

- **Total Tasks**: 69
- **Phase 1 (Setup)**: 3 tasks
- **Phase 2 (Foundational)**: 3 tasks
- **Phase 3 (User Story 1 - Traffic Capture)**: 13 tasks
- **Phase 4 (User Story 2 - Video Recording)**: 12 tasks (removed video output directory config task)
- **Phase 5 (User Story 3 - MobSF Analysis)**: 21 tasks
- **Phase 6 (User Story 4 - Configuration)**: 8 tasks
- **Phase 7 (Polish)**: 9 tasks

**Parallel Opportunities**: 
- Setup and Foundational phases have parallel tasks
- User Stories 1 and 2 can run in parallel (both P1)
- User Story 3 can run in parallel with US1/US2
- Tests within each story can run in parallel
- Polish phase tasks can mostly run in parallel

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1 - Traffic Capture) = 19 tasks
