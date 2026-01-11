# Research: Live Statistics Dashboard Updates

**Feature**: Live Statistics Dashboard Updates  
**Phase**: 0 - Research & Discovery  
**Date**: January 11, 2026

## Overview

This document consolidates research findings for implementing real-time statistics updates in the mobile-crawler GUI. The research addresses unknowns from the Technical Context and evaluates patterns for event-driven UI updates, database aggregation strategies, and performance considerations.

## Research Questions Resolved

### 1. Event System Capabilities

**Question**: Can the existing event system support statistics-relevant events?

**Finding**: ✅ **YES - System is complete and ready**

The `QtSignalAdapter` class already implements the full `CrawlerEventListener` protocol with all necessary signals:
- `crawl_started(run_id, target_package)` - For initialization
- `step_started(run_id, step_number)` - For progress tracking
- `step_completed(run_id, step_number, actions_count, duration_ms)` - For step metrics
- `action_executed(run_id, step_number, action_index, result)` - For success/failure tracking
- `screenshot_captured(run_id, step_number, screenshot_path)` - For screen tracking
- `ai_request_sent(run_id, step_number, request_data)` - For AI call counting
- `ai_response_received(run_id, step_number, response_data)` - For response time tracking
- `crawl_completed(run_id, total_steps, total_duration_ms, reason)` - For finalization

**Decision**: Use existing signals without modification. All required events are already emitted by CrawlerLoop and bridged through QtSignalAdapter.

**Alternatives Considered**:
- Create new statistics-specific signals → Rejected: Existing signals provide all needed data
- Add batching mechanism → Deferred: Implement only if performance issues observed

---

### 2. Database Query Performance

**Question**: What aggregation strategies minimize database query overhead for real-time statistics?

**Finding**: **Hybrid approach - incremental tracking + periodic validation**

Current repository structure:
- `step_logs` table has all step data with `execution_success` field
- `screens` table tracks first-seen information (unique identification)
- `ai_interactions` table (inferred) likely tracks AI call metrics
- No pre-aggregated statistics views exist

**Decision**: 
1. **Incremental tracking** (in-memory): Maintain running totals in MainWindow during active crawl
2. **Event-driven updates**: Update counters immediately on each event signal
3. **Periodic validation**: Query database every 10-30 seconds to verify accuracy (optional, for long runs)
4. **Final reconciliation**: Query database on crawl completion for accurate final values

**Rationale**: 
- Minimizes database queries during active crawl (performance)
- Provides instant UI feedback (< 1 second requirement)
- Maintains accuracy through event-driven increments
- Database serves as source of truth for historical data

**Alternatives Considered**:
- Query database on every event → Rejected: Too slow, violates 1-second update requirement
- Purely in-memory with no validation → Rejected: Risk of drift from actual data
- Pre-aggregated materialized views → Rejected: Adds schema complexity for minimal benefit

---

### 3. Thread Safety Patterns

**Question**: How to ensure thread-safe statistics updates from worker thread to UI?

**Finding**: **Qt Signal/Slot mechanism provides built-in thread safety**

PySide6 documentation confirms:
- Signals emitted from non-UI threads are automatically queued
- Slots connected to signals execute on the receiver's thread (UI thread)
- Qt's event loop handles cross-thread message passing safely

**Decision**: Use existing Qt signal/slot pattern:
1. CrawlerLoop (worker thread) emits events to QtSignalAdapter
2. QtSignalAdapter emits Qt signals
3. MainWindow connects signals to slots that update StatsDashboard
4. StatsDashboard updates execute on UI thread automatically

**Best Practices**:
- Never call StatsDashboard methods directly from worker thread
- All updates go through signal connections
- Use `Qt.QueuedConnection` explicitly if automatic detection fails
- Avoid blocking operations in UI update slots

**Alternatives Considered**:
- Manual mutex locking → Rejected: Qt signals already thread-safe
- `QMetaObject.invokeMethod()` → Rejected: Less readable than signals
- Shared data structures with locks → Rejected: More complex, error-prone

---

### 4. Screen Discovery Logic

**Question**: How is screen "uniqueness" determined for discovery metrics?

**Finding**: **Perceptual hashing with composite hash as primary key**

From `ScreenRepository` analysis:
- `composite_hash` field: Perceptual hash for similarity comparison (primary identifier)
- `visual_hash` field: Alternative hash for exact matching
- `first_seen_run_id` and `first_seen_step`: Track discovery point
- Screens identified by hash comparison, not database ID

**Decision**: Screen discovery metrics implementation:
1. **Unique screens**: Query `COUNT(DISTINCT id) FROM screens WHERE first_seen_run_id = ?`
2. **Total visits**: Count total screen transitions in step_logs for run
3. **Discovery vs revisit**: Check if screen hash exists before considering it new

**Note**: Screen identification happens in core crawler logic. Statistics layer only counts results.

**Alternatives Considered**:
- Activity name as uniqueness key → Rejected: Same activity can have different states
- Track visit counts per screen → Deferred: Not required for MVP statistics

---

### 5. AI Response Time Tracking

**Question**: Is AI response time data already captured?

**Finding**: **YES - stored in step_logs.ai_response_time_ms**

From `StepLogRepository` schema:
- `ai_response_time_ms` field exists in step_logs table
- Populated during step logging by crawler
- Available for aggregation via repository queries

**Decision**: AI metrics calculation:
1. **AI call count**: Count events from `ai_response_received` signal (real-time)
2. **Average response time**: Maintain running average from signal data
3. **Validation**: Query `AVG(ai_response_time_ms) FROM step_logs WHERE run_id = ?` periodically

**Formula**: Running average = `(previous_avg * count + new_value) / (count + 1)`

**Alternatives Considered**:
- Store all response times in list → Rejected: Memory overhead for large runs
- Query database for every average calculation → Rejected: Too slow

---

### 6. Time Tracking Mechanism

**Question**: How to implement elapsed time counter updating every second?

**Finding**: **QTimer with 1-second interval**

PySide6 `QTimer` best practices:
- `QTimer.singleShot(milliseconds, callback)` for one-time delays
- `QTimer` instance with `timeout` signal for repeating timers
- Timers run on the thread they're created in (UI thread)
- Start/stop controlled by crawl lifecycle events

**Decision**: Implementation approach:
1. Create `QTimer` instance in MainWindow initialization
2. Set interval to 1000ms (1 second)
3. Connect `timeout` signal to `_update_elapsed_time` slot
4. Start timer on `crawl_started` signal
5. Stop timer on `crawl_completed` or `error_occurred` signals
6. Track start time as `datetime.now()` when crawl starts
7. Calculate elapsed seconds as `(now - start_time).total_seconds()`

**Alternatives Considered**:
- Poll every 100ms for smoother updates → Rejected: Unnecessary overhead, 1-second granularity sufficient
- Use separate QThread for timing → Rejected: Overcomplicated, QTimer is lightweight

---

### 7. Progress Bar Update Strategy

**Question**: How to handle progress exceeding configured max values?

**Finding**: **QProgressBar supports clamping behavior**

Qt QProgressBar properties:
- `setRange(min, max)` defines progress bounds
- `setValue(value)` accepts any integer
- Values outside range are clamped automatically (0-100%)
- Text format supports custom strings via `setFormat()`

**Decision**: Progress bar behavior:
1. Set max values from settings (max_steps, max_duration_seconds)
2. Call `setValue(min(current, max))` to ensure visual cap at 100%
3. Display actual values in labels separate from progress bars
4. Update format string when max values change dynamically

**Example**: Step progress shows "547 / 100 steps" (547% internally clamped to 100%)

**Alternatives Considered**:
- Hide progress bar when exceeded → Rejected: Loss of progress indicator
- Dynamically adjust max as values increase → Rejected: Confusing to users

---

## Technology Stack Decisions

### PySide6 (Qt) - UI Framework

**Chosen**: PySide6 6.6+ (already in use)

**Strengths**:
- Native cross-platform GUI support
- Built-in thread-safe signal/slot mechanism
- Rich widget library (QProgressBar, QLabel, QTimer)
- Excellent documentation and community support

**Weaknesses**:
- Large dependency size
- Learning curve for Qt paradigms

**Alternatives Considered**: N/A - Already project dependency

---

### SQLite - Statistics Data Source

**Chosen**: SQLite3 (built-in, already in use)

**Query Strategy**:
- Prepared statements for aggregation queries
- Indexed columns (run_id already indexed as foreign key)
- Keep queries simple (COUNT, AVG, SUM)

**Sample Queries**:
```sql
-- Total steps
SELECT COUNT(*) FROM step_logs WHERE run_id = ?

-- Success/failure counts
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN execution_success = 1 THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN execution_success = 0 THEN 1 ELSE 0 END) as failed
FROM step_logs WHERE run_id = ?

-- Unique screens
SELECT COUNT(DISTINCT id) FROM screens WHERE first_seen_run_id = ?

-- AI metrics
SELECT 
    COUNT(*) as call_count,
    AVG(ai_response_time_ms) as avg_response_time
FROM step_logs 
WHERE run_id = ? AND ai_response_time_ms IS NOT NULL
```

**Performance**: Queries expected to complete in <50ms for typical run sizes (hundreds of steps)

---

## Patterns & Best Practices

### Event-Driven Architecture

**Pattern**: Observer pattern via Qt signals/slots

**Benefits**:
- Decoupling between crawler core and UI
- Thread-safe by design
- Easy to add new statistics consumers
- Testable (can mock signal emissions)

**Implementation**:
```python
# In MainWindow.__init__()
self.signal_adapter.step_completed.connect(self._on_step_completed_stats)
self.signal_adapter.action_executed.connect(self._on_action_executed_stats)
self.signal_adapter.ai_response_received.connect(self._on_ai_response_stats)
```

---

### Incremental State Management

**Pattern**: Maintain statistics state object in MainWindow

**Structure**:
```python
@dataclass
class CrawlStatistics:
    """Real-time statistics accumulator."""
    run_id: int
    start_time: datetime
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    unique_screens: Set[str] = field(default_factory=set)
    total_visits: int = 0
    ai_calls: int = 0
    ai_response_times: List[float] = field(default_factory=list)
    
    def avg_ai_response_time(self) -> float:
        return sum(self.ai_response_times) / len(self.ai_response_times) if self.ai_response_times else 0.0
    
    def elapsed_seconds(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()
    
    def screens_per_minute(self) -> float:
        minutes = self.elapsed_seconds() / 60.0
        return len(self.unique_screens) / minutes if minutes > 0 else 0.0
```

**Benefits**:
- Fast updates (no I/O)
- Easy to test
- Single source of truth during active crawl
- Can be reset/recreated per run

---

### Testing Strategy

**Unit Tests**:
- Statistics calculation methods (averages, rates)
- Edge cases (zero values, division by zero)
- Data structure behavior (set uniqueness, list operations)

**Integration Tests**:
- Mock signal emissions → verify UI updates
- Full event flow from crawler to dashboard
- Timer behavior (start/stop/elapsed calculation)

**Test Tools**:
- `pytest` (already configured)
- `pytest-qt` for Qt-specific testing
- `unittest.mock` for signal mocking

---

## Performance Considerations

### Update Frequency

**Expected Load**: 1-10 updates per second during active crawl

**Mitigation**: Qt's event queue naturally batches rapid signals

**Throttling**: Not needed initially - implement only if UI lag observed

---

### Memory Usage

**In-Memory Data**: < 1 KB per run (counters, timestamps, small lists)

**Screen Hash Set**: Worst case ~10 KB (1000 screens * 10 bytes per hash)

**Mitigation**: Clear statistics object when crawl completes

---

### Database Query Optimization

**Query Frequency**: 
- Real-time: 0 queries (use signals)
- Periodic validation: 1 query per 30 seconds (optional)
- Final: 3-4 queries on completion

**Index Usage**: Existing foreign key indexes on run_id sufficient

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Signal not emitted | Low | High | Add integration tests, verify in logs |
| UI freezes on rapid updates | Low | Medium | Use QTimer for batching if needed |
| Statistics drift from DB | Medium | Low | Periodic validation queries |
| Thread safety issues | Low | High | Follow Qt signal/slot patterns strictly |
| Large memory usage (long runs) | Low | Low | Clear intermediate data structures |

---

## Conclusion

All research questions have been resolved. The existing codebase provides complete infrastructure for real-time statistics:

✅ Event system is fully implemented  
✅ Database schema supports all required queries  
✅ Thread safety handled by Qt framework  
✅ UI components ready (StatsDashboard.update_stats)  
✅ Performance requirements achievable  

**Next Phase**: Design data models and contracts for statistics data flow (Phase 1).
