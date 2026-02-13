# Tasks: UI Monitor Improvements

**Input**: Design documents from `/specs/017-ui-monitor-improvements/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Tests**: Not explicitly requested - test tasks omitted per workflow rules.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/mobile_crawler/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new widget file and prepare for bug fixes

- [x] T001 Create new file `src/mobile_crawler/ui/widgets/json_tree_widget.py` with module docstring and imports (QTreeWidget, QTreeWidgetItem, json)
- [x] T002 [P] Add helper function `_is_full_response(response_data: dict) -> bool` in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py` to detect AIInteractionService vs CrawlerLoop responses

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core fixes that MUST be complete before enhancements

**⚠️ CRITICAL**: These bug fixes are blocking - they affect all user stories

- [x] T003 Add `_response_updated` flag handling in `AIMonitorPanel.add_response()` in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py` to skip duplicate response calls
- [x] T004 Update `_on_ai_response_received()` in `src/mobile_crawler/ui/main_window.py` to filter out CrawlerLoop summary responses (only forward full responses to `add_response()`)
- [x] T005 Fix success determination in `AIMonitorPanel.add_response()` in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py` - set success based on presence of parsed_response/actions and absence of error_message
- [x] T005a [HOTFIX] Fix `_update_list_item` to properly cleanup old widget and list item references before re-adding
- [x] T005b [HOTFIX] Improve `draw_ocr_overlays_on_pixmap` with robust bounds handling and distinct visual style (dashed, semi-transparent)

**Checkpoint**: Foundation ready - duplicates eliminated, success status correct, response data flows properly

---

## Phase 3: User Story 1 - Expandable JSON Fields (Priority: P1) 🎯 MVP

**Goal**: Display JSON data in Prompt Data and Response panels with expandable/collapsible tree controls

**Independent Test**: Open a Step Detail tab, verify Prompt Data shows collapsible tree with expand/collapse icons. Click to expand nested objects like `ocr_grounding`.

### Implementation for User Story 1

- [x] T006 [US1] Implement `JsonTreeWidget` class with `__init__(data: Union[dict, list, str])` constructor in `src/mobile_crawler/ui/widgets/json_tree_widget.py`
- [x] T007 [US1] Implement `_build_tree(data, parent_item, key)` recursive method in `src/mobile_crawler/ui/widgets/json_tree_widget.py` to create tree items from JSON
- [x] T008 [US1] Add collapsed preview text for arrays/objects (e.g., `"[15 items]"`, `"{3 keys}"`) in `_build_tree()` in `src/mobile_crawler/ui/widgets/json_tree_widget.py`
- [x] T009 [US1] Implement `collapse_to_root()` method to initially collapse all except root level in `src/mobile_crawler/ui/widgets/json_tree_widget.py`
- [x] T010 [US1] Add dark theme styling to match application in `JsonTreeWidget.__init__()` in `src/mobile_crawler/ui/widgets/json_tree_widget.py`
- [x] T011 [US1] Replace `QTextEdit` for Prompt Data with `JsonTreeWidget` in `StepDetailWidget._setup_ui()` in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T012 [US1] Add JSON detection and fallback to plain text for non-JSON prompts in `StepDetailWidget._setup_ui()` in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T013 [US1] Replace `QTextEdit` for Response panel with `JsonTreeWidget` when response contains JSON in `StepDetailWidget._setup_ui()` in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`

**Checkpoint**: User Story 1 complete - JSON data displays in collapsible tree format in Step Detail tabs

---

## Phase 4: User Story 2 - Fix Empty Response and Parsed Actions (Priority: P1)

**Goal**: Response and Parsed Actions panels display content correctly for all steps with valid AI responses

**Independent Test**: Run a crawl, open Step Detail, verify Response panel shows AI response text and Parsed Actions panel shows action details (type, description, target, reasoning).

### Implementation for User Story 2

- [x] T014 [US2] Fix response text extraction in `_add_list_item()` to check all possible keys (`response`, `raw_response`, `parsed_response`) in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T015 [US2] Fix parsed actions extraction in `_add_list_item()` to also check `actions` key directly (not just `parsed_response`) in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T016 [US2] Update `StepDetailWidget.__init__()` to accept `full_response` from correct response_data field in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T017 [US2] Fix `_on_show_details()` to extract response text from all possible response_data keys in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T018 [US2] Improve response preview generation in `_add_list_item()` to show meaningful summary when response exists in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`

**Checkpoint**: User Story 2 complete - Response and Parsed Actions panels show correct content

---

## Phase 5: User Story 3 - Fix Incorrect Failed Status (Priority: P2)

**Goal**: Action success/failure status indicators accurately reflect actual execution outcome

**Independent Test**: Run a crawl with successful actions, verify AI Monitor shows green checkmarks (✓) for successful steps, red X (✗) only for actual failures.

### Implementation for User Story 3

- [x] T019 [US3] Create `_determine_success(response_data: dict) -> bool` helper function in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T020 [US3] Update `add_response()` to use `_determine_success()` instead of `response_data.get("success", False)` in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T021 [US3] Update `_add_list_item()` success parameter to use determined success value in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`

**Checkpoint**: User Story 3 complete - Success/failure status matches actual outcomes

---

## Phase 6: User Story 4 - Fix Duplicate Actions (Priority: P2)

**Goal**: AI Monitor displays exactly one entry per crawl step (no duplicates)

**Independent Test**: Run a 5-step crawl, count items in AI Monitor list - should be exactly 5, not 10.

### Implementation for User Story 4

- [x] T022 [US4] Add `_response_updated` key to interaction dict in `add_request()` initialized to False in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T023 [US4] Add early return in `add_response()` if interaction already has `_response_updated=True` AND new response is summary-only in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T024 [US4] Verify `_update_list_item()` properly removes old item before adding new one - add debug logging if needed in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`

**Checkpoint**: User Story 4 complete - Exactly one item per step in AI Monitor

---

## Phase 7: User Story 5 - Screenshot Viewer Toggle (Priority: P3)

**Goal**: Users can switch between Annotated (action overlays) and OCR (text element labels) screenshot views

**Independent Test**: Open Step Detail, see radio buttons for "Annotated" / "OCR", click OCR to see labeled text elements on screenshot.

### Implementation for User Story 5

- [x] T025 [P] [US5] Create `draw_ocr_overlays_on_pixmap(pixmap: QPixmap, ocr_elements: List[dict]) -> QPixmap` function in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T026 [US5] Add `_annotated_pixmap`, `_ocr_pixmap`, `_ocr_grounding`, `_current_view` instance variables to `StepDetailWidget.__init__()` in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T027 [US5] Extract `ocr_grounding` from prompt JSON in `StepDetailWidget._setup_ui()` and store in `self._ocr_grounding` in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T028 [US5] Add radio buttons (QRadioButton + QButtonGroup) above screenshot in `StepDetailWidget._setup_ui()` in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T029 [US5] Connect radio button toggle signal to view switching method in `StepDetailWidget` in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T030 [US5] Implement `_on_view_toggle(view: str)` method to swap between annotated and OCR pixmaps in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T031 [US5] Generate OCR pixmap lazily on first toggle to OCR view using `draw_ocr_overlays_on_pixmap()` in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T032 [US5] Disable/hide OCR toggle when `_ocr_grounding` is empty or None in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`

**Checkpoint**: User Story 5 complete - Screenshot toggle works between Annotated and OCR views

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T033 [P] Add module docstring and type hints to `json_tree_widget.py` in `src/mobile_crawler/ui/widgets/json_tree_widget.py`
- [x] T034 [P] Update quickstart.md validation - run through all manual testing steps in `specs/017-ui-monitor-improvements/quickstart.md`
- [x] T035 Code cleanup - remove any debug logging added during implementation in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [x] T036 Verify all edge cases from spec are handled (invalid JSON, no screenshot, no actions, empty OCR)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on T002 from Setup - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1 - JSON)**: No dependencies on other stories - NEW widget file
- **User Story 2 (P1 - Empty Response)**: No dependencies on other stories - fixes extraction logic
- **User Story 3 (P2 - Failed Status)**: No dependencies - fixes success determination
- **User Story 4 (P2 - Duplicates)**: Partially addressed by Foundational phase - completes the fix
- **User Story 5 (P3 - Screenshot Toggle)**: No dependencies - adds new UI feature

### Within Each User Story

- Models/helpers before integration
- Core implementation before UI integration
- Story complete before moving to next priority

### Parallel Opportunities

- T001, T002 can run in parallel (Setup phase)
- T025 can run in parallel with other US5 tasks (separate function)
- T033, T034 can run in parallel (Polish phase)
- Different user stories can be worked on in parallel by different developers

---

## Parallel Example: User Story 1 (JSON Tree)

```bash
# These US1 tasks can be parallelized in two tracks:

# Track A: Build JsonTreeWidget (T006-T010)
# Track B: Prepare AI Monitor Panel integration (wait for Track A, then T011-T013)

# Within Track A, implementation is sequential:
T006 → T007 → T008 → T009 → T010
```

## Parallel Example: User Story 5 (Screenshot Toggle)

```bash
# T025 is independent (creates new function), can start immediately:
Task T025: Create draw_ocr_overlays_on_pixmap() function

# All other US5 tasks are sequential after T025:
T026 → T027 → T028 → T029 → T030 → T031 → T032
```

---

## Implementation Strategy

### MVP First (Foundational + User Story 1 + User Story 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - fixes core bugs)
3. Complete Phase 3: User Story 1 (JSON tree for better debugging)
4. Complete Phase 4: User Story 2 (Display response/actions correctly)
5. **STOP and VALIDATE**: Test that Step Details shows JSON tree + content

### Incremental Delivery

1. Complete Setup + Foundational → Core bugs fixed (duplicates, status)
2. Add User Story 1 (JSON) → JSON tree view working
3. Add User Story 2 (Empty Response) → Response/Actions panels show content
4. Add User Story 3 (Failed Status) → Status indicators accurate
5. Add User Story 4 (Duplicates) → Zero duplicates guaranteed
6. Add User Story 5 (Screenshot Toggle) → OCR view available
7. Each story adds value without breaking previous stories

### Single Developer Strategy

Complete in priority order:
1. Setup + Foundational (30 min)
2. User Story 1 - JSON (45 min)
3. User Story 2 - Empty Response (30 min)
4. User Story 3 - Failed Status (15 min)
5. User Story 4 - Duplicates (15 min)
6. User Story 5 - Screenshot Toggle (45 min)
7. Polish (15 min)

**Estimated Total**: ~3 hours

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All changes are in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py` + new `json_tree_widget.py`
