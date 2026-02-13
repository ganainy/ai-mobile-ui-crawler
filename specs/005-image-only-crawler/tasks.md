---
description: "Tasks for Image-Only UI Crawler implementation"
---

# Tasks: Image-Only UI Crawler

**Input**: Design documents from `/specs/005-image-only-crawler/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Phase 1: Setup

**Purpose**: Verify and clean up project dependencies.

- [x] T001 [P] Verify and update `requirements.txt` to remove OCR and XML based dependencies (Tesseract, standard XML libs used for parsing)
- [x] T002 [P] Create regression test suite baseline to ensure current functionality (before refactoring)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core logic changes required for Image-Only operation.

- [x] T003 Implement `ADBInputHandler` in `src/mobile_crawler/infrastructure/adb_input_handler.py` to handle text input via ADB shell
- [x] T004 Refactor `ActionExecutor` in `src/mobile_crawler/domain/action_executor.py` to use `ADBInputHandler` instead of `send_keys`
- [x] T005 [P] Update `PromptBuilder` in `src/mobile_crawler/domain/prompt_builder.py` to explicitly request coordinate-based actions in prompts (if not already strictly enforced)

**Checkpoint**: Text input via ADB works reliably without XML access.

---

## Phase 3: User Story 1 - Pure Visual Navigation (Priority: P1)

**Goal**: Crawler navigates using only screenshots and VLM coordinates.

**Independent Test**: Run crawler on a sample flow; verify logs show no XML dump calls.

### Implementation

- [x] T006 [US1] Integration: Verify `AIInteractionService` correctly maps VLM coordinates to screen coordinates (existing logic check & refinement)
- [x] T007 [US1] Remove any fallback logic in `ActionExecutor` that might attempt to use `find_element` if coordinates fail
- [x] T008 [US1] Update `CrawlerLoop` in `src/mobile_crawler/core/crawler_loop.py` to ensure `step_log` records visual coordinates and does not attempt to store or reference XML source
- [x] T009 [US1] Verify `ElementFinder` (if it exists) is deprecated or removed if it relies on XML

---

## Phase 4: User Story 2 - Legacy Code Cleanup (Priority: P2)

**Goal**: Remove all traces of XML parsing and OCR from the codebase.

**Independent Test**: Static analysis grep for `page_source`, `xml.etree`, `ocr`.

### Implementation

- [x] T010 [P] [US2] Audit and remove `element_finder.py` if it uses XML strategy
- [x] T011 [P] [US2] Audit `appium_driver.py` for any lingering `page_source` usage
- [x] T012 [P] [US2] Remove any OCR utility files (e.g., in `infrastructure/ocr/`) if they exist
- [x] T013 [US2] Update `run_exporter.py` to ensure it exports visual data only, removing any legacy XML fields

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and documentation.

- [x] T014 [P] Update `README.md` to reflect "Image-Only" architecture
- [x] T015 Verify `quickstart.md` instructions work on a fresh checkout
- [x] T016 Run full regression test to ensure `Image-Only` mode completes the target app flow (Sign Up -> Login)

## Dependencies & Execution Order

1. **Phase 1 & 2** (Setup & Foundational) must run first. `ADBInputHandler` is critical.
2. **Phase 3** (US1) implements the core constraint check.
3. **Phase 4** (US2) can run in parallel with Phase 3 but is best done after US1 is stable to avoid breaking active development.

## Implementation Strategy

1. **Task T003/T004** (ADB Input) is the highest technical risk. Do this first.
2. **Task T007** (Remove find_element fallback) enforces the P1 rules.
3. **Task T010-T012** (Cleanup) ensures P2 compliance.
