# Tasks: Debug Overlay & Step-by-Step Mode

**Input**: Design documents from `/specs/008-debug-overlay/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Optional - not explicitly requested in spec. Test tasks included for core logic only.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## User Story Mapping

| Story | Title | Priority | Dependencies |
|-------|-------|----------|--------------|
| US1 | Coordinate Visualization on Screenshots | P1 | None (MVP) |
| US4 | Save Annotated Screenshots | P1 | US1 (uses same overlay renderer) |
| US2 | Step-by-Step Debugging Mode | P2 | None (independent) |
| US3 | Action Index Labels on Overlay | P3 | US1 (enhancement) |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create new module file `src/mobile_crawler/domain/overlay_renderer.py` with empty class scaffold
- [X] T002 [P] Create unit test file `tests/unit/test_overlay_renderer.py` with test class scaffold

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core state machine changes that MUST be complete before user stories

**⚠️ CRITICAL**: US2 depends on state machine changes; US1/US4 can start in parallel

- [X] T003 Add `PAUSED_STEP = "paused_step"` to CrawlState enum in `src/mobile_crawler/core/crawl_state_machine.py`
- [X] T004 Update `_is_valid_transition()` in `src/mobile_crawler/core/crawl_state_machine.py` to add PAUSED_STEP transitions (RUNNING→PAUSED_STEP, PAUSED_STEP→RUNNING/STOPPING/PAUSED_MANUAL/ERROR)
- [X] T005 Add `step_paused = Signal(int, int)` signal to QtSignalAdapter in `src/mobile_crawler/ui/signal_adapter.py`
- [X] T006 Add `on_step_paused()` event handler method to QtSignalAdapter in `src/mobile_crawler/ui/signal_adapter.py`

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 - Coordinate Visualization on Screenshots (Priority: P1) 🎯 MVP

**Goal**: Draw bounding box overlays on screenshots in the UI to visualize AI-predicted coordinates in real-time

**Independent Test**: Run a crawl, click "Show Details" on any step, verify colored rectangles appear on the screenshot matching AI target areas with center dots

### Implementation for User Story 1

- [X] T007 [P] [US1] Implement color palette constants (COLORS, ERROR_COLOR) in `src/mobile_crawler/domain/overlay_renderer.py`
- [X] T008 [P] [US1] Implement `_validate_bbox()` helper method to check if coordinates are within image bounds in `src/mobile_crawler/domain/overlay_renderer.py`
- [X] T009 [US1] Implement `render_overlays()` method using PIL ImageDraw in `src/mobile_crawler/domain/overlay_renderer.py` - draws rectangles, center dots
- [X] T010 [US1] Add Qt overlay drawing function `draw_overlays_on_pixmap()` in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py` using QPainter
- [X] T011 [US1] Modify `StepDetailWidget._setup_ui()` to call overlay drawing on screenshot QPixmap before display in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`
- [X] T012 [US1] Handle edge case: out-of-bounds coordinates drawn with red dashed border in both PIL and Qt implementations

**Checkpoint**: Coordinate overlays now visible in UI when viewing step details

---

## Phase 4: User Story 4 - Save Annotated Screenshots (Priority: P1)

**Goal**: Automatically save screenshots with bounding box overlays to disk alongside original screenshots

**Independent Test**: Run a crawl, navigate to `screenshots/run_{id}/`, verify both `screenshot_*.png` and `screenshot_*_annotated.png` files exist

### Implementation for User Story 4

- [X] T013 [US4] Implement `save_annotated()` method in `src/mobile_crawler/domain/overlay_renderer.py` - calls render_overlays() and saves to disk with `_annotated` suffix
- [X] T014 [US4] Import OverlayRenderer in `src/mobile_crawler/core/crawler_loop.py`
- [X] T015 [US4] Modify `_execute_step()` in `src/mobile_crawler/core/crawler_loop.py` to call `overlay_renderer.save_annotated()` after AI response is received
- [X] T016 [US4] Add error handling for save failures (log warning, continue crawl) in `src/mobile_crawler/core/crawler_loop.py`

**Checkpoint**: Both original and annotated screenshots saved for every step with actions

---

## Phase 5: User Story 2 - Step-by-Step Debugging Mode (Priority: P2)

**Goal**: Enable developers to pause after each step and manually advance using a "Next Step" button

**Independent Test**: Enable checkbox, start crawl, verify crawler pauses after step 1, click "Next Step" to advance, repeat until completion

### Implementation for User Story 2

- [X] T017 [US2] Add `_step_by_step_enabled: bool` and `_step_advance_event: threading.Event` attributes to CrawlerLoop in `src/mobile_crawler/core/crawler_loop.py`
- [X] T018 [US2] Implement `set_step_by_step_enabled()` method in `src/mobile_crawler/core/crawler_loop.py`
- [X] T019 [US2] Implement `is_step_by_step_enabled()` method in `src/mobile_crawler/core/crawler_loop.py`
- [X] T020 [US2] Implement `advance_step()` method in `src/mobile_crawler/core/crawler_loop.py` - sets event and validates state
- [X] T021 [US2] Modify `run()` loop in `src/mobile_crawler/core/crawler_loop.py` to check step-by-step flag after each step and transition to PAUSED_STEP, wait on event
- [X] T022 [US2] Add `step_by_step_toggled = Signal(bool)` and `next_step_requested = Signal()` signals to CrawlControlPanel in `src/mobile_crawler/ui/widgets/crawl_control_panel.py`
- [X] T023 [US2] Add "Step-by-Step Mode" QCheckBox to `_setup_ui()` in `src/mobile_crawler/ui/widgets/crawl_control_panel.py`
- [X] T024 [US2] Add "Next Step" QPushButton to `_setup_ui()` in `src/mobile_crawler/ui/widgets/crawl_control_panel.py` (initially hidden/disabled)
- [X] T025 [US2] Update `update_state()` in `src/mobile_crawler/ui/widgets/crawl_control_panel.py` to handle PAUSED_STEP state (show Next Step button, update status label)
- [X] T026 [US2] Connect control panel signals to crawler_loop methods in `src/mobile_crawler/ui/main_window.py` (step_by_step_toggled → set_step_by_step_enabled, next_step_requested → advance_step)
- [X] T027 [US2] Connect signal_adapter.step_paused to control panel state update in `src/mobile_crawler/ui/main_window.py`

**Checkpoint**: Step-by-step mode fully functional with checkbox and Next Step button

---

## Phase 6: User Story 3 - Action Index Labels on Overlay (Priority: P3)

**Goal**: Display action index numbers (1, 2, 3...) on each bounding box overlay

**Independent Test**: Trigger AI response with 2+ actions, verify each box shows numbered label matching action order

### Implementation for User Story 3

- [X] T028 [US3] Implement text rendering for labels (1, 2, 3...) in `src/mobile_crawler/domain/overlay_renderer.py` using `ImageFont`
- [X] T029 [US3] Add background contrast box for labels in `src/mobile_crawler/domain/overlay_renderer.py`
- [X] T030 [US3] Add label rendering to `draw_overlays_on_pixmap()` in `src/mobile_crawler/ui/widgets/ai_monitor_panel.py` using `painter.drawText()`

**Checkpoint**: All bounding boxes now show numbered labels (1, 2, 3...)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, documentation, and validation

- [X] T030 [P] Add unit tests for `render_overlays()` edge cases (empty actions, out-of-bounds, boundary coords) in `tests/unit/test_overlay_renderer.py`
- [X] T031 [P] Update quickstart.md with actual usage instructions if needed
- [X] T032 Run full crawl with step-by-step mode enabled and verify all acceptance criteria from spec.md
- [X] T033 Code cleanup: remove any debug print statements, add docstrings where missing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 - adds PAUSED_STEP state
- **Phase 3 (US1)**: Can start after Phase 1 (does not need PAUSED_STEP state)
- **Phase 4 (US4)**: Depends on Phase 3 (uses overlay_renderer from US1)
- **Phase 5 (US2)**: Depends on Phase 2 (needs PAUSED_STEP state)
- **Phase 6 (US3)**: Depends on Phase 3 (enhances overlay_renderer from US1)
- **Phase 7 (Polish)**: Depends on all previous phases

### User Story Dependencies

```
Phase 1 (Setup)
     │
     ├──────────────────────────────┐
     ▼                              ▼
Phase 2 (Foundation)          Phase 3 (US1: Coordinate Viz) 🎯 MVP
     │                              │
     │                              ├───────────────┐
     ▼                              ▼               ▼
Phase 5 (US2: Step-by-Step)   Phase 4 (US4)   Phase 6 (US3)
     │                              │               │
     └──────────────┬───────────────┴───────────────┘
                    ▼
              Phase 7 (Polish)
```

### Parallel Opportunities

**Phase 1**: T001 and T002 can run in parallel (different files)

**Phase 2**: T005 and T006 can run in parallel (same file but different edits)

**Phase 3 (US1)**: 
- T007 and T008 can run in parallel (same file, different methods)
- T010 and T011 must be sequential (T10 creates function, T11 uses it)

**Phase 5 (US2)**: 
- T022, T023, T024 can be done together in one edit session
- T026 and T027 can run in parallel (different signal connections)

---

## Parallel Example: User Story 1 Implementation

```bash
# Phase 3 parallel execution:
# Batch 1 (parallel):
Task T007: "Implement color palette constants (COLORS, ERROR_COLOR) in overlay_renderer.py"
Task T008: "Implement _validate_bbox() helper method in overlay_renderer.py"

# Batch 2 (sequential, depends on T007+T008):
Task T009: "Implement render_overlays() method in overlay_renderer.py"

# Batch 3 (parallel with T009, different file):
Task T010: "Add Qt overlay drawing function in ai_monitor_panel.py"

# Batch 4 (depends on T010):
Task T011: "Modify StepDetailWidget to call overlay drawing"
Task T012: "Handle out-of-bounds edge case"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 3: User Story 1 (Coordinate Visualization)
3. **STOP and VALIDATE**: Test overlays appear in UI
4. Can deploy/demo with just coordinate visualization

### Recommended Delivery Order

1. **Phase 1 + Phase 3**: Get overlays working in UI (MVP)
2. **Phase 4**: Save annotated screenshots (completes P1 stories)
3. **Phase 2 + Phase 5**: Add step-by-step mode (P2)
4. **Phase 6**: Add action labels (P3 enhancement)
5. **Phase 7**: Polish and finalize

### Time Estimates (Rough)

| Phase | Estimated Time |
|-------|----------------|
| Phase 1: Setup | 15 min |
| Phase 2: Foundational | 30 min |
| Phase 3: US1 (MVP) | 1-2 hours |
| Phase 4: US4 | 30 min |
| Phase 5: US2 | 1-2 hours |
| Phase 6: US3 | 15 min |
| Phase 7: Polish | 30 min |
| **Total** | **4-6 hours** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- US1 + US4 share the overlay_renderer module (US4 uses US1's implementation)
- US2 is completely independent from US1/US4 (different subsystem)
- US3 is a small enhancement to US1's overlay drawing
- Commit after each phase or logical task group
- Stop at any checkpoint to validate story independently
