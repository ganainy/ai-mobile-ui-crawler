# Data Model: Live Statistics Dashboard

**Feature**: Live Statistics Dashboard Updates  
**Phase**: 1 - Design  
**Date**: January 11, 2026

## Overview

This document defines the data structures and relationships for real-time statistics tracking in the mobile-crawler GUI. The design uses in-memory state management for real-time updates with database queries for validation and persistence.

## Entities

### CrawlStatistics

**Purpose**: In-memory accumulator for real-time statistics during an active crawl session

**Attributes**:
- `run_id` (int): Identifier for the current crawl run
- `start_time` (datetime): Timestamp when crawl started (for elapsed time calculation)
- `total_steps` (int): Count of all steps attempted (successful + failed)
- `successful_steps` (int): Count of steps that executed successfully
- `failed_steps` (int): Count of steps that failed during execution
- `unique_screen_hashes` (Set[str]): Set of screen composite_hash values seen (for uniqueness)
- `total_screen_visits` (int): Total count of screen visits including revisits
- `ai_call_count` (int): Total number of AI API calls made
- `ai_response_times_ms` (List[float]): List of response times in milliseconds (for averaging)
- `last_update` (datetime): Timestamp of most recent statistics update

**Relationships**:
- Created 1:1 with active crawl run
- Cleared/reset when new crawl starts
- Used to populate StatsDashboard display

**Lifecycle**:
1. Created on `crawl_started` event
2. Updated on each crawler event during execution
3. Validated against database periodically (optional)
4. Cleared on `crawl_completed` or when new crawl starts

**Validation Rules**:
- `total_steps` must equal `successful_steps + failed_steps`
- `ai_call_count` must equal length of `ai_response_times_ms` (if all calls complete)
- `unique_screen_hashes` count must be ≤ `total_screen_visits`

---

### StatisticsDashboardState

**Purpose**: UI display state for the statistics dashboard widget

**Attributes**:
- `total_steps_display` (int): Value shown in "Total Steps" label
- `successful_steps_display` (int): Value shown in "Successful" label
- `failed_steps_display` (int): Value shown in "Failed" label
- `unique_screens_display` (int): Value shown in "Unique Screens" label
- `total_visits_display` (int): Value shown in "Total Visits" label
- `screens_per_minute_display` (float): Calculated rate shown in "Screens/min" label
- `ai_calls_display` (int): Value shown in "AI Calls" label
- `avg_response_time_display` (float): Average shown in "Avg Response" label
- `elapsed_seconds_display` (int): Value shown in "Elapsed" label
- `step_progress_value` (int): Current value of step progress bar (0-max_steps)
- `time_progress_value` (int): Current value of time progress bar (0-max_duration)

**Relationships**:
- Populated from CrawlStatistics
- 1:1 mapping to StatsDashboard widget state
- Updated via `update_stats()` method calls

**Update Frequency**: 
- Real-time: Immediately on each crawler event
- Periodic: Every 1 second for elapsed time

---

## Data Flow

### Real-Time Update Path

```
[CrawlerLoop Worker Thread]
         |
         | emits events via listener
         v
[CrawlerEventListener] ← implemented by → [QtSignalAdapter]
         |
         | emits Qt signals (thread-safe)
         v
[MainWindow Slots] ← connected to signals
         |
         | updates accumulator
         v
[CrawlStatistics Object] ← in-memory state
         |
         | maps to display values
         v
[StatsDashboard.update_stats()] ← UI update
         |
         v
[StatisticsDashboardState] ← rendered in UI
```

### Database Validation Path (Optional)

```
[QTimer Periodic Trigger]
         |
         v
[MainWindow._validate_statistics()]
         |
         | queries database
         v
[Repository Methods] → RunRepository, StepLogRepository, ScreenRepository
         |
         | returns aggregated data
         v
[Compare with CrawlStatistics]
         |
         | if drift detected
         v
[Recalculate & Update Dashboard]
```

---

## Calculations

### Derived Metrics

**Screens Per Minute**:
```
screens_per_minute = unique_screens / (elapsed_seconds / 60.0)
```
- If elapsed_seconds ≤ 0: return 0.0
- Precision: 1 decimal place

**Average AI Response Time**:
```
avg_response_time = sum(ai_response_times_ms) / len(ai_response_times_ms)
```
- If no AI calls: return 0.0
- Precision: 0 decimal places (integer milliseconds)

**Elapsed Time**:
```
elapsed_seconds = (current_time - start_time).total_seconds()
```
- Updated every 1 second via QTimer
- Displayed as integer seconds

**Progress Percentages**:
```
step_progress_percent = (total_steps / max_steps) * 100
time_progress_percent = (elapsed_seconds / max_duration_seconds) * 100
```
- Values > 100% clamped to 100% for progress bar display
- Actual values shown in labels regardless of limit

---

## State Transitions

### Crawl Lifecycle

**IDLE → ACTIVE**:
- Trigger: `crawl_started` signal received
- Action: 
  - Create new CrawlStatistics instance
  - Set `start_time = datetime.now()`
  - Start QTimer for elapsed time updates
  - Reset dashboard to zero values

**ACTIVE → ACTIVE** (during crawl):
- Triggers: Various crawler event signals
- Actions: Update CrawlStatistics incrementally, refresh dashboard

**ACTIVE → COMPLETED**:
- Trigger: `crawl_completed` signal received
- Actions:
  - Stop QTimer
  - Query database for final accurate values
  - Update dashboard with final statistics
  - Preserve CrawlStatistics for viewing

**COMPLETED → IDLE**:
- Trigger: New crawl starts or explicit reset
- Action: Clear CrawlStatistics object

---

## Database Queries

### Statistics Aggregation Queries

**Total Steps by Success/Failure**:
```sql
SELECT 
    COUNT(*) as total_steps,
    SUM(CASE WHEN execution_success = 1 THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN execution_success = 0 THEN 1 ELSE 0 END) as failed
FROM step_logs 
WHERE run_id = ?
```

**Unique Screens for Run**:
```sql
SELECT COUNT(DISTINCT id) 
FROM screens 
WHERE first_seen_run_id = ?
```

**Total Screen Visits**:
```sql
SELECT COUNT(*) 
FROM step_logs 
WHERE run_id = ? 
    AND (from_screen_id IS NOT NULL OR to_screen_id IS NOT NULL)
```

**AI Performance Metrics**:
```sql
SELECT 
    COUNT(*) as ai_calls,
    AVG(ai_response_time_ms) as avg_response_time
FROM step_logs 
WHERE run_id = ? 
    AND ai_response_time_ms IS NOT NULL
```

**Run Duration**:
```sql
SELECT 
    MIN(timestamp) as start_time,
    MAX(timestamp) as end_time
FROM step_logs 
WHERE run_id = ?
```

---

## Repository Extensions

### StepLogRepository

**New Methods**:

```python
def get_step_statistics(self, run_id: int) -> Dict[str, Any]:
    """Get aggregated step statistics for a run.
    
    Returns:
        {
            'total_steps': int,
            'successful_steps': int,
            'failed_steps': int
        }
    """
```

```python
def get_ai_statistics(self, run_id: int) -> Dict[str, Any]:
    """Get AI performance statistics for a run.
    
    Returns:
        {
            'ai_calls': int,
            'avg_response_time_ms': float
        }
    """
```

---

### ScreenRepository

**New Methods**:

```python
def count_unique_screens_for_run(self, run_id: int) -> int:
    """Count unique screens discovered in a specific run."""
```

```python
def count_total_visits_for_run(self, run_id: int) -> int:
    """Count total screen visits (including revisits) for a run."""
```

---

### RunRepository

**New Methods** (if needed):

```python
def get_run_duration(self, run_id: int) -> Optional[float]:
    """Get the duration of a run in seconds.
    
    Returns None if run not started/completed.
    """
```

---

## Data Integrity

### Consistency Guarantees

**Real-Time Tracking**:
- Counters increment atomically (single-threaded UI updates)
- No race conditions (Qt signal queue serializes events)
- Set operations guarantee uniqueness (Python set behavior)

**Database Validation**:
- Periodic queries ensure real-time values match persistent data
- Drift detection triggers recalculation
- Final statistics sourced from database (source of truth)

**Edge Cases**:
- Division by zero: All calculations check denominators
- Null values: Database queries filter NULL response times
- Empty sets: Length checks before averaging
- Timer precision: 1-second granularity acceptable for elapsed time

---

## Testing Considerations

### Unit Tests

**CrawlStatistics Class**:
- Test increment operations
- Validate calculated metrics (averages, rates)
- Edge cases (zero values, empty lists)
- Validation rule checks

**Repository Methods**:
- Mock database responses
- Test query correctness
- Verify aggregation logic

### Integration Tests

**Event Flow**:
- Emit mock signals → verify dashboard updates
- Simulate full crawl lifecycle
- Test timer start/stop behavior

**Database Integration**:
- Use test database with known data
- Query methods return expected aggregations
- Compare real-time vs database values

---

## Performance Metrics

**Expected Data Sizes**:
- CrawlStatistics object: < 1 KB (mostly counters)
- Screen hash set: ~100-1000 entries, ~1-10 KB
- AI response times list: ~100-1000 entries, ~1-10 KB

**Update Latency Targets**:
- Event to display update: < 100 milliseconds
- Database query execution: < 50 milliseconds
- Full dashboard refresh: < 200 milliseconds

**Memory Constraints**:
- Total in-memory state: < 100 KB per active crawl
- Cleared after crawl completion

---

## Summary

The data model uses a lightweight in-memory accumulator (`CrawlStatistics`) for real-time tracking with optional database validation. All statistics flow through Qt signals for thread safety, with calculations performed in the UI thread. The design minimizes database access during active crawls while maintaining accuracy through event-driven incremental updates.
