# Implementation Plan: Fix Settings Persistence

**Branch**: `001-fix-settings-persistence` | **Date**: 2026-01-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-fix-settings-persistence/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Fix settings persistence so that all user configuration (device selection, app package, AI provider/model, and Settings panel values) is automatically saved and restored across application restarts. The existing `UserConfigStore` infrastructure will be extended to support selector widgets.

## Technical Context

**Language/Version**: Python 3.9+ (compatible with 3.9, 3.10, 3.11, 3.12)  
**Primary Dependencies**: PySide6 >=6.6.0, cryptography >=42.0.0, sqlite3 (stdlib)  
**Storage**: SQLite (user_config.db in platform-specific app data directory)  
**Testing**: pytest >=7.0.0, pytest-qt >=4.0.0 for Qt widget testing  
**Target Platform**: Windows, macOS, Linux desktop  
**Project Type**: single (src/mobile_crawler structure with tests/)  
**Performance Goals**: Settings load/save must complete in <100ms  
**Constraints**: Sensitive data (API keys, passwords) must be encrypted at rest  
**Scale/Scope**: Single-user desktop application

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution template is not yet customized for this project. Using default best practices:

| Principle | Status | Notes |
|-----------|--------|-------|
| Test-First | ✅ PASS | Will write tests for persistence behavior |
| Simplicity | ✅ PASS | Extending existing UserConfigStore, no new patterns |
| Observability | ✅ PASS | Existing logging infrastructure available |

**Pre-Research Gate**: PASSED - No violations, proceeding to Phase 0.

### Post-Design Re-Check (Phase 1 Complete)

| Principle | Status | Notes |
|-----------|--------|-------|
| Test-First | ✅ PASS | Test patterns defined in quickstart.md |
| Simplicity | ✅ PASS | Reuses existing SettingsPanel pattern, 4 new config keys only |
| Observability | ✅ PASS | No new logging needed - SQLite operations are synchronous |
| No New Abstractions | ✅ PASS | No new classes, only parameter additions to constructors |
| Backwards Compatibility | ⚠️ NOTE | Constructor signatures change, tests must be updated |

**Post-Design Gate**: PASSED - Design follows existing patterns, no new complexity.

## Project Structure

### Documentation (this feature)

```text
specs/001-fix-settings-persistence/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A - no external APIs)
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/mobile_crawler/
├── config/
│   └── paths.py                    # App data directory paths
├── infrastructure/
│   └── user_config_store.py        # SQLite config storage (MODIFY)
├── ui/
│   ├── main_window.py              # Main window orchestration (MODIFY)
│   └── widgets/
│       ├── settings_panel.py       # Already has persistence (VERIFY)
│       ├── device_selector.py      # Add persistence (MODIFY)
│       ├── app_selector.py         # Add persistence (MODIFY)
│       └── ai_model_selector.py    # Add persistence (MODIFY)

tests/
├── infrastructure/
│   └── test_user_config_store.py   # Config store tests (EXISTS)
└── ui/
    ├── test_settings_panel.py      # Settings tests (EXISTS)
    ├── test_device_selector.py     # Device selector tests (MODIFY)
    ├── test_app_selector.py        # App selector tests (MODIFY)
    └── test_ai_model_selector.py   # AI selector tests (MODIFY)
```

**Structure Decision**: Single project structure. All changes are modifications to existing files within the established `src/mobile_crawler/` and `tests/` layout. No new directories or patterns required.

## Complexity Tracking

> No violations to justify. Feature uses existing patterns and infrastructure.
