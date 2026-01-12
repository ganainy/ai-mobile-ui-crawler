# Implementation Plan: OCR + Set-of-Mark Grounding

**Branch**: `009-ocr-som-grounding` | **Date**: 2026-01-12 | **Spec**: [Link](spec.md)
**Input**: Feature specification from `/specs/009-ocr-som-grounding/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a robust Visual Grounding system using local OCR to overlay numeric markers on text elements ("Set-of-Mark"), enabling the VLM to interact with the UI via label selection instead of imprecise coordinate prediction. This also includes a hybrid fallback mechanism for non-text elements.

## Technical Context

**Language/Version**: Python 3.11+ (Project Standard)
**Primary Dependencies**: 
- `EasyOCR` for text detection (Selected: Superior local performance and ease of install)
- `Pillow` for image manipulation and drawing overlays
**Storage**: None (in-memory processing)
**Testing**: `pytest` for unit tests, existing Appium test harness for integration
**Target Platform**: Windows (Dev), Cross-platform (Runtime)
**Project Type**: Python CLI / Library
**Performance Goals**: < 2 seconds overhead per step for OCR + Overlay generation
**Constraints**: Must work locally without external API calls for OCR

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Library-First**: ✅ Core logic (OCR, Overlay, Coordinate Mapping) will be encapsulated in `src/mobile_crawler/domain/grounding` or similar.
- **CLI Interface**: ✅ Not directly applicable to internal logic, but the crawler itself is CLI-driven.
- **Test-First**: ✅ Unit tests will be written for the coordinate mapping and overlay generation before integration.
- **Integration Testing**: ✅ Will require updating the crawler loop to test the full flow.
- **Simplicity**: ✅ Adding OCR adds weight. Justification: Necessary for reliability (SC-001).

## Project Structure

### Documentation (this feature)

```text
specs/009-ocr-som-grounding/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/mobile_crawler/
├── domain/
│   ├── grounding/           # NEW: Module for visual grounding
│   │   ├── __init__.py
│   │   ├── ocr_engine.py    # Abstraction over EasyOCR/Tesseract
│   │   ├── overlay.py       # Drawing logic for Set-of-Mark
│   │   └── mapper.py        # Label to Coordinate mapping logic
│   └── ...
├── core/
│   ├── crawler_loop.py      # UPDATE: Integrate grounding step
│   └── ...
```

**Structure Decision**: A new `grounding` domain module keeps the OCR complexity isolated from the core crawler loop, adhering to the Single Responsibility Principle.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New Dependency (`EasyOCR`) | Essential for text grounding | Screen-reading APIs (Appium XML) break "Image-Only" philosophy |

