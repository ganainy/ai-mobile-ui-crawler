# Implementation Plan: UiAutomator2 Crash Detection and Recovery

**Branch**: `023-uiautomator-crash-recovery` | **Date**: 2026-01-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/023-uiautomator-crash-recovery/spec.md`

## Summary

Implement automatic detection and recovery from UiAutomator2 crashes during crawl execution. When the UiAutomator2 instrumentation process crashes (identified by specific error patterns like "instrumentation process is not running"), the system will automatically restart the Appium session and retry the failed action. This prevents crawl session failures due to UiAutomator2 instability.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Appium Python Client, Selenium WebDriver, PyQt6  
**Storage**: SQLite (existing crawler.db)  
**Testing**: pytest with mocking for integration tests  
**Target Platform**: Windows (development), Android devices (runtime)  
**Project Type**: Single desktop application with Appium/ADB integration  
**Performance Goals**: Recovery within 30 seconds of crash detection  
**Constraints**: Must not require manual intervention; must preserve crawl state during recovery  
**Scale/Scope**: Single-device crawling sessions (1 device per run)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution file contains placeholder values. No specific constraints or gates are defined.
Proceeding with standard software engineering best practices:
- ✅ Feature is testable with unit and integration tests
- ✅ Error handling follows existing patterns in codebase
- ✅ No new external dependencies required
- ✅ Minimal changes to existing interfaces (follows existing AppiumDriver patterns)

## Project Structure

### Documentation (this feature)

```text
specs/023-uiautomator-crash-recovery/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A for this feature)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/mobile_crawler/
├── core/
│   ├── crawler_loop.py           # MODIFY: Add crash detection and retry logic
│   └── uiautomator_recovery.py   # NEW: Recovery manager class
├── domain/
│   ├── action_executor.py        # MODIFY: Integrate recovery into execution
│   └── models.py                 # MODIFY: Add recovery-related result types
├── infrastructure/
│   ├── appium_driver.py          # MODIFY: Add restart_uiautomator2() method
│   └── gesture_handler.py        # MODIFY: Propagate crash errors properly

tests/
├── unit/
│   └── core/
│       └── test_uiautomator_recovery.py  # NEW: Unit tests for recovery logic
└── integration/
    └── test_crash_recovery.py    # NEW: Integration tests with mocked crashes
```

**Structure Decision**: Single project structure following existing patterns. New `uiautomator_recovery.py` module encapsulates recovery logic, minimizing changes to existing classes.

## Complexity Tracking

> No constitution violations to justify.

| Component | Complexity | Rationale |
|-----------|------------|-----------|
| UiAutomatorRecoveryManager | Medium | New class, but follows existing patterns from TrafficCaptureManager |
| AppiumDriver.restart_uiautomator2() | Low | Wraps existing reconnect() with UiAutomator2-specific handling |
| CrawlerLoop integration | Medium | Retry loop around action execution, event emission |
