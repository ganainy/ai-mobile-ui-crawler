# Implementation Plan: Crawl Stability & Observability Fixes

**Branch**: `024-crawl-stability-fixes` | **Date**: 2026-01-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/024-crawl-stability-fixes/spec.md`

## Summary

This feature addresses 7 stability and observability issues in the mobile crawler:
1. **MobSF polling timeout** - Increase wait time for analysis completion (currently 60s, needs 10-15 minutes)
2. **PCAPdroid session cleanup** - Stop any running capture before starting a new one
3. **Time mode duration bug** - Fix crawl stopping at 200s instead of configured 300s
4. **Graceful stop** - Make Stop button trigger same cleanup as normal termination
5. **Pause-aware timer** - Stop elapsed time counter when crawl is paused
6. **OCR statistics** - Track and display average OCR operation time
7. **Timestamped logs** - Ensure all log messages include timestamps

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: PyQt6, Appium, requests, asyncio  
**Storage**: SQLite (via DatabaseManager)  
**Testing**: pytest  
**Target Platform**: Windows (primary), cross-platform compatible  
**Project Type**: Desktop application with mobile device integration  
**Performance Goals**: Responsive UI, real-time crawl feedback  
**Constraints**: Must not break existing crawl workflows  
**Scale/Scope**: Single-user desktop application

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution is a placeholder template. Applying general principles:
- ✅ **Test coverage**: Unit tests and integration tests required for changes
- ✅ **Observability**: Logging already uses structured approach with log sinks
- ✅ **Simplicity**: Bug fixes follow existing patterns
- ✅ **Backward compatibility**: No breaking API changes

## Project Structure

### Documentation (this feature)

```text
specs/024-crawl-stability-fixes/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A - internal refactoring)
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/mobile_crawler/
├── core/
│   ├── crawler_loop.py         # US3, US4, US5: Timer fixes, graceful stop, pause-aware timer
│   ├── log_sinks.py            # US7: Already has timestamps (verify)
│   └── logging_service.py      # US7: Logging infrastructure
├── domain/
│   ├── traffic_capture_manager.py  # US2: PCAPdroid stop-before-start
│   └── grounding/
│       └── manager.py          # US6: OCR timing tracking
├── infrastructure/
│   ├── mobsf_manager.py        # US1: Extended polling timeout
│   └── run_repository.py       # US6: Persist OCR stats
└── ui/
    └── widgets/
        └── statistics_panel.py  # US6: Display OCR average time

tests/
├── integration/
│   └── test_crawl_stability.py  # New integration tests
└── unit/
    ├── test_mobsf_manager.py    # Extended timeout tests
    ├── test_traffic_capture.py  # Stop-before-start tests
    └── test_crawler_loop.py     # Timer and pause tests
```

**Structure Decision**: Using existing single-project structure. All changes are bug fixes within existing modules.

## Complexity Tracking

No violations requiring justification - this is a bug-fix feature that follows existing patterns.

---

## Phase 0: Research Summary

All technical details are already known from codebase analysis. No external research required.

### Key Findings

| Issue | Root Cause Analysis | Solution |
|-------|-------------------|----------|
| MobSF timeout | `_make_api_request` uses 60s timeout. `perform_complete_scan` polls but timeout is per-request, not total wait time. Large APKs take 3-10+ minutes for full static analysis | Increase default scan timeout config and implement proper polling with extended timeout |
| PCAPdroid conflicts | `start_capture_async` checks `_is_currently_capturing` but doesn't clean up orphaned captures from previous sessions | Add explicit stop command at crawl start, regardless of internal state |
| Time mode bug | Likely issue: `max_crawl_duration_seconds` read from config at init but config may be updated afterwards by UI; OR elapsed time calculation issue | Ensure config is read just before crawl starts, not at CrawlerLoop init |
| Graceful stop | `stop()` just sets state to STOPPING, but cleanup only runs at end of normal loop. Manual stop during pause doesn't trigger cleanup | Unify cleanup path for both normal completion and Stop button |
| Pause-aware timer | `_should_continue` uses wall-clock time (`time.time() - start_time`) which includes paused time | Track actual running time separately from paused time |
| OCR stats | `GroundingManager.process_screenshot` measures time internally but doesn't expose it | Return timing data from grounding, accumulate in crawler, display in UI |
| Log timestamps | LoggingService with sinks already includes timestamps. Need to verify all log paths use it | Audit logging to ensure all paths go through LoggingService or Python logging with formatter |

---

## Phase 1: Design & Implementation Details

### 1. MobSF Polling Timeout (US1, FR-001, FR-002)

**Current State**: 
- `mobsf_manager.py` line 524-526: Uses `mobsf_scan_timeout` (default 900s = 15min) and `mobsf_poll_interval` (default 2s)
- But `_make_api_request` has hardcoded 60s timeout on individual HTTP requests (lines 132, 135)

**Changes**:
1. Add configurable request timeout separate from overall scan timeout
2. Increase default request timeout for large file operations
3. Add progress feedback during long polls

**Files to Modify**:
- `infrastructure/mobsf_manager.py`:
  - Add `mobsf_request_timeout` config (default: 300s for report downloads)
  - Update `_make_api_request` to use configurable timeout
  - Update `perform_complete_scan` to use extended timeouts for PDF/JSON download

**Config Changes**:
- `config/defaults.py`: Add `mobsf_request_timeout: 300`

### 2. PCAPdroid Stop-Before-Start (US2, FR-003, FR-004)

**Current State**:
- `traffic_capture_manager.py` line 102-103: Returns early if `_is_currently_capturing` is True
- But if app crashed, this flag may be wrong while device still has orphaned capture

**Changes**:
1. Always send stop command before starting new capture (precautionary)
2. Wait briefly for stop to complete before starting new capture

**Files to Modify**:
- `domain/traffic_capture_manager.py`:
  - Add `_stop_any_existing_capture_async()` helper method
  - Call it at the start of `start_capture_async()` regardless of `_is_currently_capturing`

### 3. Time Mode Duration Bug (US3, FR-005, FR-006)

**Current State**:
- `crawler_loop.py` line 114: `max_crawl_duration_seconds` read at `__init__` time
- UI may update config after CrawlerLoop is created but before crawl starts

**Changes**:
1. Re-read config at start of `run()` method, not constructor
2. Log the actual configured duration for debugging

**Files to Modify**:
- `core/crawler_loop.py`:
  - Move config reads from `__init__` to `run()` method (lines 113-114)
  - Add debug log showing configured duration

### 4. Graceful Stop (US4, FR-007)

**Current State**:
- `stop()` method (line 150-153) sets state to STOPPING
- Main loop checks for STOPPING and breaks
- Cleanup code at end of `run()` (lines 277-284) handles feature managers

**Changes**:
1. Ensure cleanup path is consistent whether triggered by Stop button or natural termination
2. Current code appears correct - verify behavior and add test

**Files to Modify**:
- `core/crawler_loop.py`: 
  - Add explicit cleanup method `_cleanup_crawl_session()`
  - Call from both normal completion and Stop handling
  - Ensure MobSF analysis gracefully skips if stopped early

### 5. Pause-Aware Timer (US5, FR-008, FR-009)

**Current State**:
- `_should_continue` uses `time.time() - start_time` (line 347)
- Paused time is counted toward duration

**Changes**:
1. Track cumulative `_paused_duration` separately
2. Subtract paused time from elapsed calculation
3. Track pause start/end transitions

**Files to Modify**:
- `core/crawler_loop.py`:
  - Add `_paused_duration: float` and `_pause_start_time: Optional[float]` fields
  - Update `pause()` to record pause start time
  - Update `resume()` to accumulate paused duration
  - Update `_should_continue()` to subtract paused time
  - Update step-by-step wait loop to also track paused time

### 6. OCR Performance Statistics (US6, FR-010, FR-011)

**Current State**:
- `crawler_loop.py` lines 626-633: OCR timing measured but only emitted as debug log
- No persistent storage or UI display

**Changes**:
1. Accumulate OCR timings in CrawlerLoop
2. Calculate average at crawl end
3. Store in run stats
4. Display in statistics panel

**Files to Modify**:
- `core/crawler_loop.py`:
  - Add `_ocr_total_time: float` and `_ocr_operation_count: int` fields
  - Accumulate timing in `_execute_step()`
  - Calculate average and include in completion stats
- `infrastructure/run_repository.py`:
  - Add `ocr_avg_time_ms` column (if schema supports) OR include in JSON export
- `ui/widgets/statistics_panel.py` (or equivalent):
  - Display average OCR time

### 7. Timestamped Logs (US7, FR-012, FR-013)

**Current State**:
- `log_sinks.py` already includes timestamps in all sinks (line 52, 63, 90)
- Python logging configured with timestamp formatter

**Changes**:
1. Audit code to ensure all logging goes through proper channels
2. Verify UI log viewer shows timestamps
3. No major changes expected - this is mostly verification

**Files to Verify**:
- `core/log_sinks.py`: ✅ Already includes timestamps
- `ui/widgets/log_viewer.py`: Verify timestamp display
- All calls to `logger.info`, `logger.error`, etc.: Verify Python logging formatter is applied

---

## Data Model Changes

### Run Statistics Extension

Add OCR timing statistics to crawl run data:

```python
# In run completion event or run_repository
run_stats = {
    # Existing fields...
    "ocr_avg_time_ms": Optional[float],  # Average OCR operation time in milliseconds
    "ocr_total_operations": Optional[int],  # Number of OCR operations performed
}
```

No database schema changes required - can use existing JSON export or extend run_stats.

---

## Testing Strategy

### Unit Tests

1. **MobSF Timeout Tests** (`test_mobsf_manager.py`):
   - Test configurable timeout is applied to requests
   - Test polling continues for extended duration
   - Test proper timeout error message

2. **PCAPdroid Stop-Before-Start Tests** (`test_traffic_capture.py`):
   - Test stop is sent before start regardless of internal state
   - Test multiple starts in succession work correctly

3. **Timer Tests** (`test_crawler_loop.py`):
   - Test paused time not counted toward duration
   - Test step-by-step pause doesn't count time
   - Test config is re-read at run start

4. **OCR Stats Tests**:
   - Test accumulation of OCR timings
   - Test average calculation

### Integration Tests

1. **Full Crawl with Pauses** (`test_crawl_stability.py`):
   - Start crawl, pause, resume, verify correct duration
   
2. **Stop Button Cleanup**:
   - Start crawl, click stop, verify all artifacts saved

---

## Quickstart

See `quickstart.md` for step-by-step implementation guide.
