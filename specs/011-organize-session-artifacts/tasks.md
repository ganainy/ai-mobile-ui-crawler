# Tasks: Organize Session Artifacts

**Input**: Design documents from `/specs/011-organize-session-artifacts/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included to verify folder structure and component integration.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initial database changes and path definitions

- [X] T001 Update `src/mobile_crawler/infrastructure/database.py` to include `session_path` in `runs` table
- [X] T002 Update `src/mobile_crawler/infrastructure/migrations/011_add_session_path.sql` with `ALTER TABLE` logic
- [X] T003 Update `src/mobile_crawler/infrastructure/run_repository.py` to handle the new `session_path` field in `Run` dataclass and queries

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core path logic that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Update `src/mobile_crawler/infrastructure/session_folder_manager.py` to implement `create_session_folder` with standard subdirs
- [X] T005 Update `src/mobile_crawler/infrastructure/session_folder_manager.py` to implement `get_subfolder(run_id, subdir)`
- [X] T006 Update `src/mobile_crawler/infrastructure/session_folder_manager.py` to refine `get_session_path` to check DB first, then fallback to heuristics

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 2 - Automated Artifact Grouping (Priority: P1) 🎯 MVP

**Goal**: Automatically save all generated artifacts into session-specific folders during a run.

**Independent Test**: Trigger a crawl and verify that screenshots and logs appear in `output_data/run_{ID}_{TIMESTAMP}/` subfolders.

### Implementation for User Story 2

- [X] T007 Update `src/mobile_crawler/core/crawler_loop.py` to call `create_session_folder` at start of `run()` and persist path to DB
- [X] T008 Update `src/mobile_crawler/infrastructure/screenshot_capture.py` to resolve save path via `SessionFolderManager`
- [X] T009 Update `src/mobile_crawler/domain/report_generator.py` to save PDF reports into the session's `reports/` folder
- [X] T010 Update `src/mobile_crawler/infrastructure/mobsf_manager.py` to save/move analysis reports into the session's `reports/` folder
- [X] T011 [US2] Integration test for artifact grouping in `tests/integration/test_artifact_grouping.py`

**Checkpoint**: User Story 2 is functional - artifacts are now saved in organized folders.

---

## Phase 4: User Story 1 - Centralized Session Folder Access (Priority: P1)

**Goal**: Provide a single button to open the consolidated session folder from the UI.

**Independent Test**: Click "Open" on a completed run and verify the correct directory opens in the OS file explorer.

### Implementation for User Story 1

- [X] T012 Update `src/mobile_crawler/ui/widgets/run_history_view.py` to use `SessionFolderManager.get_session_path()` for the "Open Folder" button logic
- [X] T013 Update `src/mobile_crawler/ui/widgets/run_history_view.py` to ensure the button is enabled for any run with a valid `session_path` or heuristic match
- [X] T014 [US1] Integration test for UI folder opening in `tests/ui/test_run_history_folder_open.py`

**Checkpoint**: User Story 1 is functional - users can access the organized folders directly from the UI.

---

## Phase 5: User Story 3 - Run Export Consolidation (Priority: P2)

**Goal**: Consolidate JSON exports and DB snippets into the session folder.

**Independent Test**: Verify `run_export.json` exists in `output_data/run_{ID}_{TIMESTAMP}/data/` after a run.

### Implementation for User Story 3

- [X] T015 Update `src/mobile_crawler/infrastructure/run_exporter.py` to save JSON exports into the session's `data/` folder by default
- [X] T016 [US3] Integration test for export consolidation in `tests/integration/test_export_consolidation.py`

**Checkpoint**: User Story 3 is functional - session data is now portable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanups and validation

- [X] T017 [P] Clean up any dead code in `SessionFolderManager` heuristic logic
- [X] T018 [P] Update project `README.md` (if applicable) documentation regarding storage structure
- [X] T019 Run `quickstart.md` validation on a fresh run

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001-T003) - BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational completion.
  - Phase 3 (US2) should ideally come before US1 and US3 implementation on the crawler side.

### Parallel Opportunities

- T017, T018 can run in parallel.
- Integration tests (T011, T014, T016) can be written in parallel once the foundation is in place.

---

## Implementation Strategy

### MVP First (Artifact Grouping + UI Access)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 2 (Grouping)
4. Complete Phase 4: User Story 1 (UI)
5. **STOP and VALIDATE**: Verify that a new run creates a folder and the UI button opens it correctly.

### Incremental Delivery

1. Foundation ready.
2. Artifacts grouped → Data is organized on disk.
3. UI Access added → User value delivered (MVP).
4. Export consolidated → Portable sessions delivered.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify integration tests pass after each phase
