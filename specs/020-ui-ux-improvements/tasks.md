---
description: "Task list for UI/UX improvements including threading, layout, and persistence"
---

# Tasks: UI/UX Improvements

**Input**: Design documents from `/specs/020-ui-ux-improvements/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel
- **[Story]**: [US1]..[US7]
- Desciption includes file paths

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Check dependencies for PySide6 in requirements.txt (implied present)

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure for threading that MUST be complete before US1.

- [X] T002 Create `AsyncOperation` class in `src/mobile_crawler/ui/async_utils.py` following data-model.md

**Checkpoint**: `AsyncOperation` is available for import.

---

## Phase 3: User Story 1 - Responsive UI During Long Operations (Priority: P1) 🎯 MVP

**Goal**: Prevent UI freezes during device/app/model loading.

**Independent Test**: Click Refresh on Device/App/Model selectors; UI should remain responsive (spinner shows, no freeze).

### Implementation for User Story 1

- [X] T003 [US1] Refactor `DeviceSelector` to use `AsyncOperation` for `get_available_devices` in `src/mobile_crawler/ui/widgets/device_selector.py`
- [X] T004 [US1] Add loading state (spinner/text) to `DeviceSelector` during refresh in `src/mobile_crawler/ui/widgets/device_selector.py`
- [X] T005 [P] [US1] Refactor `AppSelector` to use `AsyncOperation` for `list_packages` in `src/mobile_crawler/ui/widgets/app_selector.py`
- [X] T006 [P] [US1] Add loading state to `AppSelector` during app fetch in `src/mobile_crawler/ui/widgets/app_selector.py`
- [X] T007 [P] [US1] Refactor `AIModelSelector` to use `AsyncOperation` for `get_vision_models` in `src/mobile_crawler/ui/widgets/ai_model_selector.py`
- [X] T008 [P] [US1] Update `AIModelSelector` to show loading status during model fetch in `src/mobile_crawler/ui/widgets/ai_model_selector.py`

**Checkpoint**: US1 fully functional.

---

## Phase 4: User Story 2 - Improved UI Layout Organization (Priority: P2)

**Goal**: Organize settings into tabs to reduce scrolling.

**Independent Test**: Open Settings panel; verify 4 tabs exist and settings are grouped logically.

### Implementation for User Story 2

- [X] T009 [US2] Initialize `QTabWidget` structure in `src/mobile_crawler/ui/widgets/settings_panel.py` replacing the main `QVBoxLayout`
- [X] T010 [US2] Move "Crawl Limits" and "Screen Configuration" to "General" tab in `src/mobile_crawler/ui/widgets/settings_panel.py`
- [X] T011 [US2] Move "API Keys" and "System Prompt" to "AI Settings" tab in `src/mobile_crawler/ui/widgets/settings_panel.py`
- [X] T012 [US2] Move "Traffic Capture", "Video Recording", "MobSF" to "Integrations" tab in `src/mobile_crawler/ui/widgets/settings_panel.py`
- [X] T013 [US2] Move "Test Credentials" to "Credentials" tab in `src/mobile_crawler/ui/widgets/settings_panel.py`
- [X] T014 [US2] Ensure "Save Settings" button remains visible outside tabs (bottom area) in `src/mobile_crawler/ui/widgets/settings_panel.py`

**Checkpoint**: US2 functional (settings in tabs).

---

## Phase 5: User Story 3 - Streamlined Menu Bar (Priority: P2)

**Goal**: Remove useless menus.

**Independent Test**: Launch app; verify Menu Bar only has useful items.

### Implementation for User Story 3

- [X] T015 [US3] Remove empty/useless File menu items in `src/mobile_crawler/ui/main_window.py`
- [X] T016 [US3] Add "Open Session Folder" action to File menu in `src/mobile_crawler/ui/main_window.py`
- [X] T017 [US3] Cleanup Help menu items in `src/mobile_crawler/ui/main_window.py`

**Checkpoint**: US3 functional.

---

## Phase 6: User Story 4 - Optimized Space Usage (Priority: P2)

**Goal**: Minimize gaps in center panel.

**Independent Test**: Visual check of center panel spacing.

### Implementation for User Story 4

- [X] T018 [US4] Adjust layout margins and stretch factors for center panel in `src/mobile_crawler/ui/main_window.py`
- [X] T019 [US4] Remove excessive `addStretch` calls in `src/mobile_crawler/ui/widgets/crawl_control_panel.py` if present
- [X] T020 [US4] Ensure `StatsDashboard` expands to fill vertical space in `src/mobile_crawler/ui/widgets/stats_dashboard.py` or parent layout

**Checkpoint**: US4 functional.

---

## Phase 7: User Story 5 - Expanded Test Credentials (Priority: P3)

**Goal**: Fix compressed inputs in credentials form.

**Independent Test**: View Credentials tab; verify fields are well-spaced and fully visible.

### Implementation for User Story 5

- [X] T021 [US5] Increase vertical spacing/margins in Credentials tab layout in `src/mobile_crawler/ui/widgets/settings_panel.py`
- [X] T022 [US5] Verify input field minimum widths/heights in `src/mobile_crawler/ui/widgets/settings_panel.py`

**Checkpoint**: US5 functional.

---

## Phase 8: User Story 6 - Increased Run History Visibility (Priority: P3)

**Goal**: Show more runs by default.

**Independent Test**: Launch app; verify Run History shows >3 rows.

### Implementation for User Story 6

- [X] T023 [US6] Set `minimumHeight` for `RunHistoryView` in `src/mobile_crawler/ui/widgets/run_history_view.py`
- [X] T024 [US6] Adjust `QSplitter` initial sizes in `src/mobile_crawler/ui/main_window.py` to prioritize bottom panel height

**Checkpoint**: US6 functional.

---

## Phase 9: User Story 7 - Persistent Step-by-Step Mode (Priority: P3)

**Goal**: Save Step-by-Step preference.

**Independent Test**: Enable step-by-step, restart app, verify it's still enabled.

### Implementation for User Story 7

- [X] T025 [US7] Update `UserConfigStore` to support `ui_step_by_step_enabled` (if schema migration needed, otherwise just usage) - *Note: SQLite store is key-value based so no schema change needed usually*
- [X] T026 [US7] Load step-by-step preference in `MainWindow` or `CrawlControlPanel` init in `src/mobile_crawler/ui/main_window.py`
- [X] T027 [US7] Save preference when checkbox toggled in `src/mobile_crawler/ui/widgets/crawl_control_panel.py` (via signal to MainWindow)

**Checkpoint**: US7 functional.

---

## Phase 10: Polish

- [X] T028 Update `quickstart.md` with any final UI changes
- [X] T029 manual verification of tab focus order in SettingsPanel

## Dependencies

- Phase 2 (AsyncUtils) BLOCKS Phase 3 (US1)
- Phase 3 (US1) is independent of layout changes (Phases 4-9)
- Phase 4 (US2) BLOCKS Phase 7 (US5) as US5 tweaks the layout created in US2
