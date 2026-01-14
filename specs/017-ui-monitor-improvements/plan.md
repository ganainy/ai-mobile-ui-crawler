# Implementation Plan: UI Monitor Improvements

**Branch**: `017-ui-monitor-improvements` | **Date**: 2026-01-14 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/017-ui-monitor-improvements/spec.md`

## Summary

This feature addresses several UI bugs and enhancements in the AI Monitor panel:

1. **JSON Expand/Collapse** (P1): Add collapsible tree view for JSON data in Prompt Data and Response panels
2. **Fix Empty Response/Parsed Actions** (P1): Fix data extraction to correctly display AI responses and parsed actions
3. **Fix Incorrect Failed Status** (P2): Correct the success/failure determination logic
4. **Fix Duplicate Actions** (P2): Prevent double-entries in the AI Monitor list
5. **Screenshot Toggle** (P3): Add toggle between Annotated and OCR screenshot views

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: PySide6 (Qt for Python), PIL/Pillow  
**Storage**: N/A (in-memory UI state, existing SQLite for persistence)  
**Testing**: pytest  
**Target Platform**: Windows (primary), Linux, macOS (desktop)  
**Project Type**: Single Python project with Qt UI  
**Performance Goals**: UI operations < 100ms, JSON rendering < 500ms for 1000 nodes  
**Constraints**: Must maintain current signal-based event architecture  
**Scale/Scope**: Single AI Monitor panel with Step Detail tabs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **All checks pass** - No constitution violations. This is a UI-only change with no new architectural patterns required.

## Project Structure

### Documentation (this feature)

```text
specs/017-ui-monitor-improvements/
├── plan.md              # This file
├── research.md          # Phase 0 output: Root cause analysis
├── data-model.md        # Phase 1 output: Data structures for JSON viewer
├── quickstart.md        # Phase 1 output: Developer guide
├── contracts/           # N/A - No API contracts (internal UI)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/mobile_crawler/ui/
├── widgets/
│   ├── ai_monitor_panel.py    # Main file: AIMonitorPanel, AIInteractionItem, StepDetailWidget
│   └── json_tree_widget.py    # NEW: Collapsible JSON tree widget
└── main_window.py             # Signal connections (may need minor updates)

tests/ui/
├── test_ai_monitor_panel.py   # Existing tests (update for new behavior)
└── test_json_tree_widget.py   # NEW: JSON tree widget tests
```

**Structure Decision**: Single project with existing `src/mobile_crawler/ui/widgets/` structure. Add one new widget file for JSON tree functionality.

## Complexity Tracking

> No violations to justify - standard UI enhancement pattern.
