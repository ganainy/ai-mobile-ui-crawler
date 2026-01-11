# Event Contracts: Statistics Updates

**Feature**: Live Statistics Dashboard Updates  
**Purpose**: Define event payloads and handler contracts for statistics flow  
**Date**: January 11, 2026

## Overview

This document specifies the contracts between event emitters (CrawlerLoop/QtSignalAdapter) and consumers (MainWindow statistics handlers). All events follow Qt signal/slot patterns for thread-safe communication.

---

## Signal Definitions

### crawl_started

**Emitter**: `QtSignalAdapter`  
**Signature**: `crawl_started(run_id: int, target_package: str)`

**Payload**:
```python
{
    "run_id": int,           # Database identifier for this crawl run
    "target_package": str    # Android package name being explored
}
```

**Statistics Handler Responsibilities**:
1. Create new `CrawlStatistics` instance with `run_id`
2. Set `start_time = datetime.now()`
3. Reset all dashboard displays to zero
4. Start QTimer for elapsed time updates (1-second interval)
5. Retrieve max_steps and max_duration from settings
6. Initialize dashboard progress bar ranges

**Example Handler**:
```python
def _on_crawl_started_stats(self, run_id: int, target_package: str) -> None:
    # Create statistics accumulator
    self._current_stats = CrawlStatistics(run_id=run_id, start_time=datetime.now())
    
    # Reset dashboard
    self.stats_dashboard.reset()
    
    # Configure limits from settings
    max_steps = self.settings_panel.get_max_steps()
    max_duration = self.settings_panel.get_max_duration()
    self.stats_dashboard.set_max_steps(max_steps)
    self.stats_dashboard.set_max_duration(max_duration)
    
    # Start timer
    self._elapsed_timer.start(1000)  # 1 second interval
```

---

### step_completed

**Emitter**: `QtSignalAdapter`  
**Signature**: `step_completed(run_id: int, step_number: int, actions_count: int, duration_ms: float)`

**Payload**:
```python
{
    "run_id": int,          # Run identifier (for validation)
    "step_number": int,     # Sequential step number (1-indexed)
    "actions_count": int,   # Number of actions in this step
    "duration_ms": float    # Step execution time in milliseconds
}
```

**Statistics Handler Responsibilities**:
1. Increment `total_steps` by 1
2. Update dashboard total steps display
3. Update step progress bar value
4. (Success/failure incremented via action_executed events)

**Example Handler**:
```python
def _on_step_completed_stats(self, run_id: int, step_number: int, 
                             actions_count: int, duration_ms: float) -> None:
    if not self._current_stats or self._current_stats.run_id != run_id:
        return  # Not our run
    
    self._current_stats.total_steps += 1
    self._update_dashboard()
```

---

### action_executed

**Emitter**: `QtSignalAdapter`  
**Signature**: `action_executed(run_id: int, step_number: int, action_index: int, result: ActionResult)`

**Payload**:
```python
{
    "run_id": int,           # Run identifier
    "step_number": int,      # Step containing this action
    "action_index": int,     # Action index within step (0-indexed)
    "result": ActionResult   # Object with .success boolean and other fields
}
```

**ActionResult Attributes** (relevant for statistics):
- `success` (bool): Whether action executed successfully
- `action_type` (str): Type of action (click, input, scroll, etc.)
- `error_message` (Optional[str]): Error details if failed

**Statistics Handler Responsibilities**:
1. If `result.success == True`: increment `successful_steps`
2. If `result.success == False`: increment `failed_steps`
3. Update dashboard success/failure displays
4. Validate: `total_steps == successful_steps + failed_steps`

**Example Handler**:
```python
def _on_action_executed_stats(self, run_id: int, step_number: int, 
                               action_index: int, result: ActionResult) -> None:
    if not self._current_stats or self._current_stats.run_id != run_id:
        return
    
    if result.success:
        self._current_stats.successful_steps += 1
    else:
        self._current_stats.failed_steps += 1
    
    self._update_dashboard()
```

---

### screenshot_captured

**Emitter**: `QtSignalAdapter`  
**Signature**: `screenshot_captured(run_id: int, step_number: int, screenshot_path: str)`

**Payload**:
```python
{
    "run_id": int,              # Run identifier
    "step_number": int,         # Step number for this screenshot
    "screenshot_path": str      # File path to saved screenshot
}
```

**Statistics Handler Responsibilities**:
1. Query screen hash for this screenshot (if needed)
2. Add hash to `unique_screen_hashes` set (automatic deduplication)
3. Increment `total_screen_visits` by 1
4. Calculate `screens_per_minute` metric
5. Update dashboard screen discovery displays

**Note**: Screen hash lookup may require repository query or caching strategy

**Example Handler**:
```python
def _on_screenshot_captured_stats(self, run_id: int, step_number: int, 
                                   screenshot_path: str) -> None:
    if not self._current_stats or self._current_stats.run_id != run_id:
        return
    
    # Option 1: Assume screen already saved with hash
    # Query screen repository for latest screen by this run/step
    screen = self._screen_repo.get_screen_for_step(run_id, step_number)
    if screen:
        self._current_stats.unique_screen_hashes.add(screen.composite_hash)
    
    self._current_stats.total_screen_visits += 1
    self._update_dashboard()
```

---

### ai_response_received

**Emitter**: `QtSignalAdapter`  
**Signature**: `ai_response_received(run_id: int, step_number: int, response_data: Dict[str, Any])`

**Payload**:
```python
{
    "run_id": int,                  # Run identifier
    "step_number": int,             # Step number for this AI call
    "response_data": {              # AI response details
        "response_time_ms": float,  # Time taken for AI call
        "model": str,               # AI model used
        "actions": List[Dict],      # Suggested actions
        # ... other response fields
    }
}
```

**Required Fields in response_data**:
- `response_time_ms` (float): AI API call duration in milliseconds

**Statistics Handler Responsibilities**:
1. Increment `ai_call_count` by 1
2. Append `response_time_ms` to `ai_response_times_ms` list
3. Calculate new running average
4. Update dashboard AI performance displays

**Example Handler**:
```python
def _on_ai_response_stats(self, run_id: int, step_number: int, 
                          response_data: Dict[str, Any]) -> None:
    if not self._current_stats or self._current_stats.run_id != run_id:
        return
    
    response_time = response_data.get("response_time_ms", 0.0)
    self._current_stats.ai_call_count += 1
    self._current_stats.ai_response_times_ms.append(response_time)
    
    self._update_dashboard()
```

---

### crawl_completed

**Emitter**: `QtSignalAdapter`  
**Signature**: `crawl_completed(run_id: int, total_steps: int, total_duration_ms: float, reason: str)`

**Payload**:
```python
{
    "run_id": int,              # Run identifier
    "total_steps": int,         # Final step count from crawler
    "total_duration_ms": float, # Total crawl duration
    "reason": str               # Completion reason (success, max_steps, error, etc.)
}
```

**Statistics Handler Responsibilities**:
1. Stop QTimer for elapsed time updates
2. Query database for final accurate statistics (validation)
3. Update dashboard with final values from database
4. Mark statistics as "completed" (optional state tracking)
5. Preserve final statistics for viewing

**Example Handler**:
```python
def _on_crawl_completed_stats(self, run_id: int, total_steps: int, 
                               total_duration_ms: float, reason: str) -> None:
    # Stop timer
    self._elapsed_timer.stop()
    
    # Query database for accurate final values
    final_stats = self._get_final_statistics_from_db(run_id)
    
    # Update dashboard with authoritative data
    self.stats_dashboard.update_stats(
        total_steps=final_stats['total_steps'],
        successful_steps=final_stats['successful_steps'],
        failed_steps=final_stats['failed_steps'],
        unique_screens=final_stats['unique_screens'],
        total_visits=final_stats['total_visits'],
        screens_per_minute=final_stats['screens_per_minute'],
        ai_calls=final_stats['ai_calls'],
        avg_ai_response_time_ms=final_stats['avg_response_time_ms'],
        duration_seconds=total_duration_ms / 1000.0
    )
    
    # Clear in-memory accumulator
    self._current_stats = None
```

---

### QTimer Timeout (Periodic)

**Emitter**: `QTimer` instance in MainWindow  
**Signature**: `timeout()` (parameterless signal)

**Purpose**: Update elapsed time counter every second

**Handler Responsibilities**:
1. Calculate elapsed seconds: `(now - start_time).total_seconds()`
2. Update dashboard elapsed time display
3. Update time progress bar value
4. Recalculate time-dependent metrics (screens per minute)

**Example Handler**:
```python
def _update_elapsed_time(self) -> None:
    if not self._current_stats:
        return
    
    elapsed = (datetime.now() - self._current_stats.start_time).total_seconds()
    
    # Update only time-related displays
    self.stats_dashboard.duration_label.setText(f"Elapsed: {int(elapsed)}s")
    self.stats_dashboard.time_progress_bar.setValue(min(int(elapsed), max_duration))
    
    # Recalculate time-dependent metrics
    if elapsed > 0:
        screens_per_min = (len(self._current_stats.unique_screen_hashes) / elapsed) * 60
        self.stats_dashboard.screens_per_minute_label.setText(f"Screens/min: {screens_per_min:.1f}")
```

---

## Dashboard Update Contract

### update_stats() Method

**Interface** (existing in StatsDashboard):
```python
def update_stats(
    self,
    total_steps: int = 0,
    successful_steps: int = 0,
    failed_steps: int = 0,
    unique_screens: int = 0,
    total_visits: int = 0,
    screens_per_minute: float = 0.0,
    ai_calls: int = 0,
    avg_ai_response_time_ms: float = 0.0,
    duration_seconds: float = 0.0,
) -> None:
    """Update all statistics displays."""
```

**Thread Safety**: MUST be called from UI thread only (via Qt signal connections)

**Call Sites**:
1. After each event handler updates `CrawlStatistics`
2. Every 1 second from QTimer timeout
3. On crawl completion with database query results

**Optimization**: Can batch multiple small updates to reduce rendering calls

---

## Repository Query Contracts

### StepLogRepository.get_step_statistics()

**Purpose**: Aggregate step success/failure counts

**Signature**:
```python
def get_step_statistics(self, run_id: int) -> Dict[str, int]:
    """Get step statistics for a run.
    
    Returns:
        {
            'total_steps': int,
            'successful_steps': int,
            'failed_steps': int
        }
    """
```

**Query**: See data-model.md "Total Steps by Success/Failure"

**Performance**: < 50ms for typical run sizes

---

### ScreenRepository.count_unique_screens_for_run()

**Purpose**: Count unique screens discovered

**Signature**:
```python
def count_unique_screens_for_run(self, run_id: int) -> int:
    """Count unique screens for a run."""
```

**Query**: See data-model.md "Unique Screens for Run"

**Performance**: < 50ms with index on first_seen_run_id

---

### StepLogRepository.get_ai_statistics()

**Purpose**: Aggregate AI performance metrics

**Signature**:
```python
def get_ai_statistics(self, run_id: int) -> Dict[str, float]:
    """Get AI statistics for a run.
    
    Returns:
        {
            'ai_calls': int,
            'avg_response_time_ms': float  # 0.0 if no calls
        }
    """
```

**Query**: See data-model.md "AI Performance Metrics"

**Performance**: < 50ms

---

## Error Handling

### Invalid run_id

**Scenario**: Event received for different run_id than current

**Handling**: Ignore event silently (defensive check in all handlers)

```python
if not self._current_stats or self._current_stats.run_id != run_id:
    return
```

---

### Missing Statistics Object

**Scenario**: Event received before crawl_started or after crawl_completed

**Handling**: Ignore event (statistics object is None)

```python
if not self._current_stats:
    return
```

---

### Database Query Failure

**Scenario**: Repository query throws exception

**Handling**: Log error, use in-memory values as fallback

```python
try:
    final_stats = self._get_final_statistics_from_db(run_id)
except Exception as e:
    logger.error(f"Failed to query final statistics: {e}")
    final_stats = self._current_stats_to_dict()  # Use in-memory values
```

---

### Division by Zero

**Scenario**: Calculate screens_per_minute with elapsed time = 0

**Handling**: Check denominator before division

```python
screens_per_minute = (unique_screens / elapsed_seconds * 60) if elapsed_seconds > 0 else 0.0
```

---

## Testing Contracts

### Mock Signal Emissions

**Unit Test Pattern**:
```python
def test_step_completed_increments_total():
    # Setup
    main_window = MainWindow()
    main_window._current_stats = CrawlStatistics(run_id=1, start_time=datetime.now())
    
    # Emit signal
    main_window.signal_adapter.step_completed.emit(1, 1, 2, 150.0)
    
    # Assert
    assert main_window._current_stats.total_steps == 1
    assert main_window.stats_dashboard.get_total_steps() == 1
```

---

### Integration Test Pattern

**Full Event Flow**:
```python
def test_full_crawl_statistics_flow():
    # Setup
    main_window = MainWindow()
    
    # Simulate crawl lifecycle
    main_window.signal_adapter.crawl_started.emit(1, "com.example.app")
    main_window.signal_adapter.step_completed.emit(1, 1, 2, 150.0)
    main_window.signal_adapter.action_executed.emit(1, 1, 0, ActionResult(success=True))
    main_window.signal_adapter.ai_response_received.emit(1, 1, {"response_time_ms": 250.0})
    main_window.signal_adapter.crawl_completed.emit(1, 1, 1000.0, "max_steps")
    
    # Assert final state
    assert main_window.stats_dashboard.get_total_steps() == 1
    assert main_window.stats_dashboard.get_ai_calls() == 1
```

---

## Summary

All event contracts follow Qt signal/slot patterns for thread safety. Handlers update in-memory `CrawlStatistics` object and refresh dashboard displays. Database queries used only for validation and final statistics. Each handler includes defensive checks for null statistics and mismatched run_ids.
