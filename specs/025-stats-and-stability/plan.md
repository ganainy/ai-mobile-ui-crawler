# Implementation Plan: Statistics Display and Crawl Stability Improvements

**Branch**: `025-stats-and-stability` | **Date**: 2026-01-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/025-stats-and-stability/spec.md`

## Summary

This feature extends the Statistics panel to display real-time timing metrics (OCR average, action execution average, screenshot capture average) that are currently only available in logs. Additionally, it addresses crawl stability issues including duration limit enforcement, PCAPdroid permission dialogs, and video recording initialization failures.

**Technical Approach**:
1. Extend `CrawlStatistics` dataclass and `StatsDashboard` widget to include new timing metrics
2. Add new event signals for operation timing through the existing `CrawlerEventListener` infrastructure
3. Fix duration enforcement by auditing the `_should_continue` logic in `CrawlerLoop`
4. Improve PCAPdroid capture to ensure API key is properly passed and no permission dialogs appear
5. Add graceful handling for video recording failures with stale process cleanup

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: PySide6 (Qt), Appium, Pillow, easyocr  
**Storage**: SQLite (via DatabaseManager)  
**Testing**: pytest  
**Target Platform**: Windows desktop (controlling Android devices)
**Project Type**: Single project (desktop GUI application)  
**Performance Goals**: UI updates within 1 second of operation completion  
**Constraints**: Must not block main crawl loop for UI updates (use event-based approach)  
**Scale/Scope**: Single-user desktop application

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Modular Design | ✅ PASS | Extends existing event-based architecture |
| Single Responsibility | ✅ PASS | Stats tracking separate from crawl logic |
| Thread Safety | ✅ PASS | Uses Qt signals for thread-safe UI updates |
| Graceful Degradation | ✅ PASS | Video/PCAP failures don't block crawl |

## Project Structure

### Documentation (this feature)

```text
specs/025-stats-and-stability/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/mobile_crawler/
├── core/
│   ├── crawler_loop.py           # FR-007: Fix duration enforcement
│   └── crawler_event_listener.py # FR-004,05,06: Extend with timing events
├── domain/
│   ├── traffic_capture_manager.py # FR-009,10: PCAPdroid improvements
│   └── video_recording_manager.py # FR-011,12: Video recording robustness
└── ui/
    ├── main_window.py             # Statistics accumulation
    ├── signal_adapter.py          # Timing event signals
    └── widgets/
        └── stats_dashboard.py     # FR-001,02,03,13: Extended UI

tests/
├── unit/
│   ├── test_stats_dashboard.py       # New timing metrics display
│   ├── test_crawler_loop_duration.py # Duration limit enforcement
│   └── test_timing_events.py         # Event emission tests
└── integration/
    └── test_stats_flow.py            # End-to-end timing flow
```

**Structure Decision**: Single project structure - this is a desktop GUI application with a clear domain/infrastructure/UI separation already established.

## Complexity Tracking

No constitution violations requiring justification.
