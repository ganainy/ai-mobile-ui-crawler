# Research: Crawl Stability & Observability Fixes

**Branch**: `024-crawl-stability-fixes` | **Date**: 2026-01-15

## Overview

This document consolidates research findings for the 7 bug fixes in this feature. Since these are internal bug fixes within an existing codebase, research is primarily code analysis rather than external technology investigation.

---

## Issue 1: MobSF Polling Timeout

### Problem Analysis

**Symptom**: MobSF analysis times out after 60 seconds, even though the scan takes 3+ minutes.

**Root Cause Investigation**:
1. `mobsf_manager.py` line 132, 135: Individual HTTP requests have a hardcoded 60-second timeout
2. The polling loop uses `mobsf_scan_timeout` (default 900s) but each request can fail individually
3. When fetching large reports (PDF/JSON), the request may exceed 60 seconds

**Evidence from User Logs**:
```
Request timeout for http://localhost:8000/api/v1/scan: HTTPConnectionPool(host='localhost', port=8000): Read timed out. (read timeout=60)
MobSF analysis failed: Failed to scan APK: Timeout Error: Request to MobSF server timed out after 60 seconds
```

### Decision

**Solution**: Make request timeout configurable and increase default for report downloads.

**Rationale**: 
- The `/api/v1/scan` endpoint triggers async analysis; shouldn't take long
- The `/api/v1/download_pdf` and `/api/v1/report_json` endpoints return large files that can take minutes
- Need different timeouts for different operations

**Alternatives Considered**:
| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Increase global timeout to 10 mins | Simple | Wastes time on genuine failures | Rejected |
| Per-endpoint timeout config | Flexible | Complex configuration | Adopted |
| Streaming downloads | Memory efficient | Complex implementation | Deferred |

---

## Issue 2: PCAPdroid Session Conflicts

### Problem Analysis

**Symptom**: PCAP file not found errors when starting new crawl after previous one was interrupted.

**Root Cause Investigation**:
1. `traffic_capture_manager.py` line 102-103: Early return if `_is_currently_capturing` is True
2. If app crashes or is force-closed, internal state becomes stale
3. PCAPdroid on device may still be running from previous session
4. New capture starts with new filename, but PCAPdroid may be writing to old file

**Evidence from User Logs**:
```
PCAP file not found at expected location: /sdcard/Download/PCAPdroid/shop.shop_apotheke.com.shopapotheke_run50_step1_20260115_125807.pcap
[DEBUG] No exact match found, using first available: /sdcard/Download/PCAPdroid/captive_portal_analyzer.pcap
Traffic capture stopped but PCAP file not saved
```

### Decision

**Solution**: Always send stop command before starting, regardless of internal state.

**Rationale**:
- Safe operation: stopping a non-running capture is a no-op
- Clears any orphaned captures from previous sessions
- Minimal overhead (one quick ADB command)

**Alternatives Considered**:
| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Query PCAPdroid status first | Accurate | Adds latency, status API unreliable | Rejected |
| Always stop before start | Simple, reliable | Slight overhead | Adopted |
| Kill PCAPdroid process | Thorough | Too aggressive | Rejected |

---

## Issue 3: Time Mode Duration Bug

### Problem Analysis

**Symptom**: Crawl stops at 200 seconds when configured for 300 seconds.

**Root Cause Investigation**:
1. `crawler_loop.py` line 113-114: Config read at constructor time
2. `main_window.py` line 412: UI sets config before creating CrawlerLoop... OR after?
3. If UI creates CrawlerLoop first, then applies settings, the CrawlerLoop has stale values

**Hypothesis**: Config timing issue between UI and CrawlerLoop initialization.

### Decision

**Solution**: Re-read configuration at the start of `run()` method.

**Rationale**:
- Ensures config reflects current UI state when crawl actually starts
- Safe change: just moves read timing
- Easy to debug with logging

**Alternatives Considered**:
| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Re-read config in run() | Simple, reliable | None significant | Adopted |
| Pass config as run() parameter | Explicit | Breaking API change | Rejected |
| Use config observer pattern | Reactive | Over-engineering | Rejected |

---

## Issue 4: Graceful Stop

### Problem Analysis

**Symptom**: Stop button may leave session incomplete or resources not cleaned up.

**Root Cause Investigation**:
1. `stop()` sets state to STOPPING (line 152-153)
2. Main loop checks STOPPING and breaks (line 244-245)
3. Cleanup code runs after loop (lines 277-284)
4. This appears correct - but verify behavior with manual testing

**Finding**: Code appears correct. May need additional verification that all cleanup paths are exercised.

### Decision

**Solution**: Refactor cleanup into explicit method, ensure it's called consistently.

**Rationale**:
- Makes cleanup logic more explicit and testable
- Ensures same cleanup runs regardless of how crawl ends

**Alternatives Considered**:
| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Extract _cleanup_session() | Clean, testable | Refactoring effort | Adopted |
| Add try/finally | Ensures cleanup | Less explicit | Alternative |
| Status quo | No work | Harder to verify | Rejected |

---

## Issue 5: Pause-Aware Timer

### Problem Analysis

**Symptom**: Paused time counts toward duration limit in time-based mode.

**Root Cause Investigation**:
1. `_should_continue()` line 347: `elapsed_seconds = time.time() - start_time`
2. This is wall-clock time, includes paused periods
3. Pause wait loops (lines 237-241, 258-261) just sleep without tracking pause duration

### Decision

**Solution**: Track cumulative paused time separately, subtract from elapsed calculation.

**Rationale**:
- Standard approach for pause-aware timers
- Minimal overhead (just timestamp tracking)
- Users expect paused time to not count

**Implementation Details**:
```python
# In __init__:
self._paused_duration = 0.0
self._pause_start_time: Optional[float] = None

# In pause():
self._pause_start_time = time.time()

# In resume():
if self._pause_start_time:
    self._paused_duration += time.time() - self._pause_start_time
    self._pause_start_time = None

# In _should_continue():
elapsed_seconds = time.time() - start_time - self._paused_duration
```

**Alternatives Considered**:
| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Track paused duration | Simple, accurate | Must handle all pause states | Adopted |
| Use running time counter | Thread-safe | More complex | Rejected |
| Extend deadline on resume | Conceptually simple | Edge cases | Rejected |

---

## Issue 6: OCR Performance Statistics

### Problem Analysis

**Symptom**: No visibility into OCR performance.

**Root Cause Investigation**:
1. `crawler_loop.py` lines 626-633: OCR timing is measured and logged
2. But not accumulated or displayed in statistics
3. `GroundingManager.process_screenshot` returns overlay but not timing

### Decision

**Solution**: Accumulate timings in CrawlerLoop, calculate average, display in UI.

**Rationale**:
- Timing is already being measured
- Just need to accumulate and expose it
- Matches existing statistics display patterns

**Data Flow**:
```
GroundingManager.process_screenshot() 
  → CrawlerLoop._execute_step() measures time
  → Accumulate in _ocr_total_time, _ocr_count
  → Calculate average at crawl end
  → Emit in on_crawl_completed event
  → Display in statistics panel
```

**Alternatives Considered**:
| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Accumulate in CrawlerLoop | Uses existing timing | None | Adopted |
| GroundingManager returns timing | Cleaner API | API change | Deferred |
| Store in database | Persistent | Schema change | Future |

---

## Issue 7: Timestamped Logs

### Problem Analysis

**Symptom**: Some logs may not have timestamps.

**Root Cause Investigation**:
1. `log_sinks.py`: All sinks include timestamps (ConsoleSink line 52, JSONEventSink line 63, FileSink line 90)
2. Standard Python logging uses formatter with timestamp (line 89-91)
3. UI LogViewer may or may not show timestamps

**Finding**: Core logging infrastructure already includes timestamps. This is primarily a verification issue.

### Decision

**Solution**: Audit and verify, make minor fixes if found.

**Rationale**:
- Infrastructure already supports timestamps
- May just need UI verification

**Verification Checklist**:
- [ ] LogViewer widget displays timestamps
- [ ] All log calls use logger.info/error/etc (not print)
- [ ] No direct print statements in production code

---

## Summary

| Issue | Root Cause | Solution Complexity |
|-------|-----------|---------------------|
| MobSF timeout | Hardcoded 60s HTTP timeout | Low - config change |
| PCAPdroid conflicts | No precautionary stop | Low - add stop call |
| Time mode bug | Config read at init | Low - move read |
| Graceful stop | Unclear cleanup flow | Medium - refactor |
| Pause-aware timer | Wall-clock timing | Medium - track pauses |
| OCR stats | Timing not accumulated | Low - accumulate & display |
| Timestamped logs | Already working | Low - verification |

All solutions use existing patterns and require no external dependencies or breaking changes.
