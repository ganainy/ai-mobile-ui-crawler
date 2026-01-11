# Implementation Plan: Image-Only UI Crawler

**Branch**: `005-image-only-crawler` | **Date**: 2026-01-11 | **Spec**: [Spec](./spec.md)
**Input**: Feature specification from `specs/005-image-only-crawler/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

The goal is to modify the crawler to operate strictly on visual feedback (screenshots), removing all dependencies on XML View Hierarchy (`page_source`) and OCR libraries. The system will leverage a Visual Language Model (VLM) for screen understanding and coordinate generation.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: Appium-Python-Client, Pillow, ADB (via subprocess), VLM Provider (Gemini/OpenAI/etc.)
**Storage**: SQLite (existing)
**Testing**: pytest
**Target Platform**: Android (via Appium)
**Project Type**: Mobile Automation (Python)
**Performance Goals**: < 5s per step (including VLM latency), reliable text input without DOM access.
**Constraints**: **Strictly NO XML/PageSource access**. **Strictly NO OCR libraries**.
**Scale/Scope**: Crawler logic and Action Executor updates.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Library-First**: N/A (Feature modification, not new library)
- [x] **CLI Interface**: N/A
- [x] **Test-First**: Will follow TDD for new helper logic.
- [x] **Integration Testing**: End-to-end crawler tests required.
- [x] **Simplicity**: Removing XML/OCR simplifies the architecture.

## Project Structure

### Documentation (this feature)

```text
specs/005-image-only-crawler/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── mobile_crawler/
│   ├── core/           # Crawler loop logic
│   ├── domain/         # Action executor, model adapters
│   └── infrastructure/ # Appium driver, AI service
tests/
├── unit/
└── integration/
```

**Structure Decision**: Standard Python src layout.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | | |
