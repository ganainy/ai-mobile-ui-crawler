---
description: "Tasks for Fix Run History UI & Add Directory Access"
---

# Tasks: Fix Run History UI & Add Directory Access

**Input**: Design documents from `/specs/010-fix-run-history-ui/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure (None required for this feature as it modifies existing code)

- [ ] T001 Verify project environment is ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure logic for run management and session folders

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 [P] Update `StaleRunCleaner` logic in `src/mobile_crawler/core/stale_run_cleaner.py` to unconditionally mark RUNNING sessions as INTERRUPTED
- [x] T003 [P] Add `get_session_path` method to `SessionFolderManager` in `src/mobile_crawler/infrastructure/session_folder_manager.py` using timestamp heuristics
- [x] T004 Create unit tests for `get_session_path` in `tests/infrastructure/test_session_folder_manager.py` (if test file exists or new file)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Clear Status for Incomplete Runs (Priority: P1) 🎯 MVP

**Goal**: Ensure "zombie" runs are marked correctly on startup and displayed properly in the UI.

**Independent Test**: Kill the app while a run is active, restart, and verify the run shows "INTERRUPTED" instead of "RUNNING".

### Implementation for User Story 1

- [x] T005 [US1] Instantiate and invoke `StaleRunCleaner` in `src/mobile_crawler/ui/main_window.py` (or `app_context_manager.py`) on application startup
- [x] T006 [US1] Update `RunHistoryView` in `src/mobile_crawler/ui/widgets/run_history_view.py` to handle `INTERRUPTED` status presentation (colors/text)
- [x] T007 [US1] Update `RunHistoryView` in `src/mobile_crawler/ui/widgets/run_history_view.py` to display "N/A" or "-" for missing end times in the End Time column

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Open Run Directory (Priority: P2)

**Goal**: Allow users to open the artifact folder for any run directly from the history view.

**Independent Test**: Click "Open Folder" on a run and verify Explorer opens to the correct location.

### Implementation for User Story 2

- [x] T008 [US2] Update `RunHistoryView` in `src/mobile_crawler/ui/widgets/run_history_view.py` to add "Open Folder" button/action column
- [x] T009 [US2] Implement button click handler in `src/mobile_crawler/ui/widgets/run_history_view.py` to resolve path via `SessionFolderManager`
- [x] T010 [US2] Connect click handler to `QDesktopServices.openUrl` in `src/mobile_crawler/ui/widgets/run_history_view.py` with error handling

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T011 Verify error handling when session folder is missing (User Story 2)
- [x] T012 Manual testing: Verify that `RUNNING` status is cleared on startup with multiple "crashed" runs
- [x] T013 Manual testing: Verify that clicking "Open Folder" opens the correct directory and handles missing folders gracefully

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish**: Depends on all user stories

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational
- **User Story 2 (P2)**: Can start after Foundational

### Parallel Opportunities

- T002 and T003 in Phase 2 can run in parallel
- Phase 3 and Phase 4 can run in parallel (different areas of UI/logic)

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 & 2
2. Complete Phase 3: User Story 1 (fix the weird status)
3. **STOP and VALIDATE**: Test that crashed runs are fixed on startup.

### Incremental Delivery

1. Foundation ready
2. deliver US1 (Status fix)
3. deliver US2 (Open Folder)
