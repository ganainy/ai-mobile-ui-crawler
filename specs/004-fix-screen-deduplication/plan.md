# Implementation Plan: Fix Screen Deduplication

**Branch**: `004-fix-screen-deduplication` | **Date**: 2026-01-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-fix-screen-deduplication/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature aims to fix the screen deduplication logic to prevent false positives caused by minor visual changes (carousel rotations, status bar updates). The technical approach involves refining the existing perceptual hashing (pHash) implementation, introducing a configurable similarity threshold, and implementing status bar masking/exclusion. We will use `imagehash` library but tune parameters (hash size vs. hamming distance) and ensure dynamic regions are excluded before hashing.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: 
- `ImageHash` (for pHash)
- `Pillow` (for image manipulation/cropping)
- `sqlite3` (via `DatabaseManager`)
**Storage**: SQLite (`crawler.db` - existing `screens` table)  
**Testing**: `pytest`  
**Target Platform**: Windows (Development), Android (Target App)  
**Project Type**: Python Application  
**Performance Goals**: Hash calculation < 50ms per screen  
**Constraints**: Must maintain backward compatibility with existing screen hashes in DB (or provide migration strategy if format changes drastically)  
**Scale/Scope**: Affects core `ScreenTracker` logic; touched ~4 files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Library-First
- **Pass**: The core logic will exist in `domain/screen_tracker.py` and `infrastructure/screen_repository.py`. These are part of the core library structure.

### II. CLI Interface
- **Pass**: N/A for this specific internal logic fix, but the crawler itself is CLI-driven.

### III. Test-First (NON-NEGOTIABLE)
- **Pass**: We will define tests for `ScreenTracker` with sample images (carousel variations) before modifying the implementation.

### IV. Integration Testing
- **Pass**: Will include integration tests verifying the repository correctly retrieves similar screens.

### V. Observability
- **Pass**: We will add logging (FR-007) for similarity scores to aid debugging.

## Project Structure

### Documentation (this feature)

```text
specs/004-fix-screen-deduplication/
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
│   ├── screen_tracker.py       # MAIN TARGET: Update hash generation and comparison logic
│   └── models.py               # Update configuration models
├── infrastructure/
│   └── screen_repository.py    # Update query logic for similarity
└── config/
    └── config_manager.py       # Add new configuration options

tests/
├── unit/
│   └── domain/
│       └── test_screen_tracker.py  # New tests for deduplication
└── integration/
    └── infrastructure/
        └── test_screen_repository.py # Verify persistence and lookup
```

**Structure Decision**: Modifying existing `domain` and `infrastructure` modules. No new top-level packages needed.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | | |
