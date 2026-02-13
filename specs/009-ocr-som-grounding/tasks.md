---
description: "Implementation tasks for OCR + Set-of-Mark Grounding"
---

# Tasks: OCR + Set-of-Mark Grounding

**Input**: Design documents from `/specs/009-ocr-som-grounding/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL but included for core logic verification as per Constitution.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Install EasyOCR and Pillow dependencies
- [x] T002 Create domain module structure in `src/mobile_crawler/domain/grounding/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Create `OCRResult` and `GroundingOverlay` data models in `src/mobile_crawler/domain/grounding/dtos.py`
- [x] T004 Create `GroundingService` protocol definition in `src/mobile_crawler/domain/grounding/interfaces.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Robust Text Interaction (Priority: P1) 🎯 MVP

**Goal**: Enable reliable text interaction via OCR and Set-of-Mark overlays

**Independent Test**: Verify text on a sample image is detected, labeled, and mapped back to coordinates.

### Tests for User Story 1 (OPTIONAL)

- [x] T005 [P] [US1] Create unit test for Label Mapping logic in `tests/domain/grounding/test_mapper.py`
- [x] T006 [P] [US1] Create unit test for Overlay Drawing logic in `tests/domain/grounding/test_overlay.py`

### Implementation for User Story 1

- [x] T007 [P] [US1] Implement `OCREngine` wrapper for EasyOCR in `src/mobile_crawler/domain/grounding/ocr_engine.py` (Must implement error handling for slow operations)
- [x] T008 [US1] Implement `LabelMapper` logic (Label ID generation & Coordinate retrieval) in `src/mobile_crawler/domain/grounding/mapper.py`
- [x] T009 [US1] Implement `OverlayDrawer` using Pillow (Draw boxes + IDs) in `src/mobile_crawler/domain/grounding/overlay.py`
- [x] T010 [US1] Implement `GroundingManager` main class weaving OCR->Map->Overlay in `src/mobile_crawler/domain/grounding/manager.py`
- [x] T011 [US1] Integrate GroundingManager into `src/mobile_crawler/core/crawler_loop.py` to annotate screenshots before VLM call
- [x] T012 [US1] Update VLM prompt to interpret Set-of-Mark labels in `src/mobile_crawler/core/prompts.py` (or equivalent)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Hybrid Fallback for Non-Text Elements (Priority: P2)

**Goal**: Ensure icon-only elements are still clickable via raw coordinates when no label exists

**Independent Test**: Verify click action works on coordinate inputs even when grounding is active.

### Implementation for User Story 2

- [x] T013 [US2] Update `GroundingManager` to handle non-text areas gracefully (no-op or fallback) in `src/mobile_crawler/domain/grounding/manager.py`
- [x] T014 [US2] Update `crawler_loop.py` to handle hybrid action outputs (Label ID OR Coordinates) in `src/mobile_crawler/core/crawler_loop.py`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T015 [P] Add performance logging to measure OCR overhead in `src/mobile_crawler/domain/grounding/manager.py`
- [ ] T016 Run quickstart.md validation script

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User Story 1 (P1) is the core MVP
  - User Story 2 (P2) is an enhancement to logic in US1

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2)
- **User Story 2 (P2)**: Best implemented after US1 is working, as it modifies the interaction loop.

### Parallel Opportunities

- T005, T006 (Tests) and T007, T008, T009 (Model/Service components) can run in parallel by different agents/devs.

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (OCR -> Label -> Click)
4. **STOP and VALIDATE**: Verify accuracy improvement on text buttons.
5. Deploy/demo if ready

### Incremental Delivery

1. Foundation ready.
2. US1 adds text interaction capability.
3. US2 ensures we don't regress on icon interaction.
