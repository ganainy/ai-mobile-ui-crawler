# Implementation Plan: Live Statistics Dashboard Updates

**Branch**: `003-live-statistics-ui` | **Date**: January 11, 2026 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-live-statistics-ui/spec.md`

## Summary

Enable real-time statistics updates in the GUI dashboard during active crawl sessions. Currently, the statistics panel displays static zero values despite having a complete UI structure and update methods. The feature will wire existing crawler events to the StatsDashboard widget, add periodic timers for elapsed time tracking, and query database repositories for accurate aggregated statistics including steps (total/successful/failed), screen discovery metrics, AI performance data, and progress indicators.

## Technical Context

**Language/Version**: Python 3.9+  
**Primary Dependencies**: PySide6 6.6+ (Qt GUI framework), Appium Python Client 3.0+, SQLite3 (built-in)  
**Storage**: SQLite databases (crawler.db for run data, user_config.db for preferences)  
**Testing**: pytest with coverage, integration tests for event flow  
**Target Platform**: Windows/Linux/macOS desktop (GUI application)  
**Project Type**: Single project (desktop GUI with database backend)  
**Performance Goals**: Statistics updates within 1 second of events, UI remains responsive with 10+ updates/second  
**Constraints**: Thread-safe updates via Qt signals, non-blocking database queries, graceful handling of rapid events  
**Scale/Scope**: Single-run monitoring (1 active crawl), hundreds to thousands of steps per session, real-time update frequency

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Initial Check** (Before Phase 0):
Constitution template not yet populated for this project. Proceeding with standard software engineering best practices:
- ✅ No new libraries required (all dependencies exist)
- ✅ Integration tests required for event flow verification
- ✅ Unit tests for statistics calculation logic
- ✅ Observability via existing logging infrastructure
- ✅ Maintains existing architecture patterns (repository, event listener, Qt signals)

**Post-Design Check** (After Phase 1):
- ✅ Design maintains architectural consistency (event-driven, repository pattern)
- ✅ No new external dependencies introduced
- ✅ Thread safety preserved via Qt signal/slot mechanism
- ✅ Database queries remain simple and indexed
- ✅ Testing strategy covers unit and integration levels
- ✅ Implementation complexity justified (wiring existing components vs creating new infrastructure)

**Verdict**: ✅ **APPROVED** - Feature ready for implementation (Phase 2 tasks)

## Project Structure

## Project Structure

### Documentation (this feature)

```text
specs/003-live-statistics-ui/
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 output (research findings)
├── data-model.md        # Phase 1 output (statistics data structures)
├── quickstart.md        # Phase 1 output (developer guide)
├── contracts/           # Phase 1 output (event contracts)
│   └── statistics-events.md
└── checklists/
    └── requirements.md  # Quality validation (already created)
```

### Source Code (repository root)

```text
src/mobile_crawler/
├── ui/
│   ├── main_window.py              # [MODIFY] Wire statistics event handlers
│   ├── signal_adapter.py           # [EXISTING] Already has all required signals
│   └── widgets/
│       └── stats_dashboard.py      # [EXISTING] Already has complete UI + update_stats()
├── core/
│   ├── crawler_loop.py             # [EXISTING] Emits events via listener
│   └── crawler_event_listener.py   # [EXISTING] Protocol definition
└── infrastructure/
    ├── run_repository.py           # [EXTEND] Add statistics query methods
    ├── screen_repository.py        # [EXTEND] Add count methods for unique/total
    ├── step_log_repository.py      # [EXTEND] Add aggregation methods
    └── ai_interaction_repository.py # [EXISTING] May need stat query methods

tests/
├── unit/
│   └── test_stats_calculations.py  # [NEW] Unit tests for stat aggregation
└── integration/
    └── test_stats_updates.py       # [NEW] Integration test for event flow
```

**Structure Decision**: Single project structure maintained. All required infrastructure exists - this feature primarily involves wiring existing components together. Signal adapter already has all necessary events defined. StatsDashboard widget has complete UI and update methods. Main work is connecting event handlers in MainWindow and adding repository query methods for statistics aggregation.

## Complexity Tracking

> No constitution violations - all work uses existing patterns and dependencies.

N/A - Feature follows established architecture patterns (repository pattern for data access, Qt signals for thread-safe UI updates, event listener protocol for crawler events).

---

## Phase Outputs

### Phase 0: Research ✅ COMPLETE

**File**: [research.md](research.md)

**Key Findings**:
- Event system fully implemented with all required signals
- Database schema supports all statistic queries
- Thread safety handled by Qt framework automatically
- In-memory incremental tracking strategy validated
- Screen uniqueness via perceptual hashing confirmed
- AI response times stored in step_logs table
- QTimer pattern for elapsed time updates

**Decisions Made**:
- Hybrid approach: incremental in-memory + periodic database validation
- Qt signal/slot for thread-safe updates (no manual locking)
- CrawlStatistics dataclass for real-time accumulation
- Database queries only for validation and final statistics

---

### Phase 1: Design ✅ COMPLETE

**Files**: 
- [data-model.md](data-model.md) - Data structures and calculations
- [contracts/statistics-events.md](contracts/statistics-events.md) - Event payloads and handler contracts
- [quickstart.md](quickstart.md) - Developer implementation guide

**Design Outputs**:

**Data Model**:
- `CrawlStatistics` in-memory accumulator with 9 tracked metrics
- Derived calculations: avg AI response time, screens per minute, elapsed time
- State lifecycle: IDLE → ACTIVE → COMPLETED
- Repository extension methods for database aggregation

**Event Contracts**:
- 7 signal handlers defined (crawl_started, step_completed, action_executed, etc.)
- Thread safety via Qt signal/slot automatic queuing
- Defensive null checks in all handlers
- QTimer for 1-second periodic updates

**Implementation Guide**:
- 15-step walkthrough with code examples
- Repository query implementations (SQL)
- Common pitfalls and solutions
- Testing strategies (unit + integration)

---

## Next Steps

### Phase 2: Task Breakdown (Use `/speckit.tasks`)

The implementation plan is complete. Next phase will break down the work into specific development tasks:

1. **Core Implementation Tasks**:
   - Add CrawlStatistics dataclass to main_window.py
   - Implement 7 signal handler methods
   - Add QTimer for elapsed time
   - Create central dashboard update method

2. **Repository Extension Tasks**:
   - Extend StepLogRepository with 3 new aggregation methods
   - Extend ScreenRepository with 2 count methods
   - Add database query for final statistics

3. **Testing Tasks**:
   - Unit tests for CrawlStatistics calculations
   - Unit tests for repository aggregation queries
   - Integration test for full event flow
   - Manual testing with real devices

4. **Documentation Tasks**:
   - Update main_window.py docstrings
   - Add inline comments for signal handlers
   - Update README with statistics features

**Estimated Effort**: 8-12 hours (small to medium feature)

**Risk Level**: Low - wiring existing infrastructure, well-defined interfaces

---

## Summary

This implementation plan enables real-time statistics updates by connecting existing mobile-crawler infrastructure:

**What Exists**:
- ✅ Complete StatsDashboard UI with update_stats() method
- ✅ QtSignalAdapter with all required event signals
- ✅ CrawlerLoop emitting events via listener protocol
- ✅ Database schema with statistics data in step_logs, screens tables

**What's Needed**:
- Connect signal handlers in MainWindow (7 methods)
- Create CrawlStatistics accumulator class
- Add QTimer for elapsed time updates
- Extend repositories with aggregation queries (5 new methods)
- Write tests for event flow and calculations

**Architecture**: Event-driven with in-memory state management, thread-safe via Qt signals, database validation for accuracy.

**Performance**: Sub-second update latency, minimal database queries during active crawl, efficient O(1) counter increments.

**Quality Gates**: All constitution checks passed, unit + integration test coverage, manual testing with real devices required.

The design leverages existing patterns and infrastructure, requiring primarily glue code to connect components. Implementation complexity is justified by the need for thread-safe real-time updates with database accuracy guarantees.
