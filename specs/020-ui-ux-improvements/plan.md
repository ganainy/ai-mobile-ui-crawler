# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

## Summary

This feature implements critical UI/UX improvements to the Mobile Crawler application. The primary focus is eliminating UI freezes during long-running operations (device detection, app listing, model fetching) by moving them to background threads using a new `AsyncOperation` utility. Additionally, the `SettingsPanel` will be refactored into a tabbed layout to reduce scrolling, the Menu Bar will be cleaned up, and persistence will be added for the "Step-by-Step Mode" preference.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: PySide6 (Qt framework)
**Storage**: SQLite (`user_config.db`) via `UserConfigStore`
**Testing**: `pytest` for unit tests, manual verification for UI responsiveness
**Target Platform**: Windows (Desktop GUI)
**Performance Goals**: UI responsiveness <100ms lag; Background tasks show immediate feedback.
**Constraints**: Must use `QThread` / Signals & Slots for thread-safe UI updates.
**Scale/Scope**: Refactoring ~5 key UI widgets; introducing 1 new utility class.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Gates determined based on constitution file]

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/mobile_crawler/
├── ui/
│   ├── widgets/
│   │   ├── settings_panel.py    # REFACTOR: Convert to TabWidget
│   │   ├── device_selector.py   # REFACTOR: Use AsyncOperation
│   │   ├── app_selector.py      # REFACTOR: Use AsyncOperation
│   │   ├── ai_model_selector.py # REFACTOR: Use AsyncOperation
│   │   └── run_history_view.py  # REFACTOR: Min height
│   ├── main_window.py           # REFACTOR: Menu cleanup, layout usage
│   └── async_utils.py           # NEW: AsyncOperation class
```

**Structure Decision**: creating `src/mobile_crawler/ui/async_utils.py` to house the shared `AsyncOperation` class, keeping it close to the UI code that consumes it.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
