# Implementation Plan: Debug Overlay & Step-by-Step Mode

**Branch**: `008-debug-overlay` | **Date**: 2026-01-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-debug-overlay/spec.md`

## Summary

This feature adds two debugging capabilities to the mobile crawler UI:
1. **Coordinate Overlay Visualization**: Draw bounding boxes from AI responses directly on screenshots displayed in the UI, with center points and action indices. Also save annotated screenshots to disk.
2. **Step-by-Step Debugging Mode**: A checkbox that pauses the crawler after each step, requiring a "Next Step" button press to continue.

The implementation leverages existing Qt/PySide6 infrastructure, the signal adapter pattern for event handling, and the existing pause/resume state machine.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: PySide6 (Qt bindings), Pillow (PIL for image manipulation)  
**Storage**: Screenshots saved to filesystem (`screenshots/run_{id}/`)  
**Testing**: pytest  
**Target Platform**: Windows desktop application  
**Project Type**: Single Python package with CLI and GUI  
**Performance Goals**: Overlay rendering < 50ms per step, no noticeable UI lag  
**Constraints**: Must work with existing crawler loop without breaking current functionality  
**Scale/Scope**: Single-user debugging tool, typically < 50 steps per crawl session

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution is not yet configured for this project (template placeholders remain). No specific gates to evaluate. Proceeding with standard best practices:

- ✅ Feature is modular and can be tested independently
- ✅ UI changes are isolated to UI layer (no core logic pollution)
- ✅ Follows existing event-driven patterns (signal/slot)
- ✅ Maintains backward compatibility (step-by-step mode is opt-in)

## Project Structure

### Documentation (this feature)

```text
specs/008-debug-overlay/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal interfaces)
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/mobile_crawler/
├── core/
│   ├── crawl_state_machine.py    # Add PAUSED_STEP state
│   └── crawler_loop.py           # Add step-by-step pause logic
├── domain/
│   └── overlay_renderer.py       # NEW: Coordinate overlay rendering
├── infrastructure/
│   └── screenshot_capture.py     # Add save_annotated() method
├── ui/
│   ├── signal_adapter.py         # Already has step signals
│   └── widgets/
│       ├── ai_monitor_panel.py   # Add overlay to StepDetailWidget
│       ├── crawl_control_panel.py # Add Step-by-Step checkbox, Next Step button
│       └── screenshot_overlay.py # NEW: Widget for screenshot with overlays

tests/
├── unit/
│   └── test_overlay_renderer.py  # NEW: Test overlay rendering logic
└── integration/
    └── test_step_by_step.py      # NEW: Test step-by-step mode
```

**Structure Decision**: Follows existing single-project structure. New logic is added as:
- A new domain module (`overlay_renderer.py`) for pure image manipulation (no Qt dependencies)
- A new UI widget (`screenshot_overlay.py`) for Qt-based rendering
- Modifications to existing `crawl_control_panel.py` for the checkbox and button
- Modifications to `crawl_state_machine.py` to add the new pause state

## Complexity Tracking

No constitution violations to justify.
