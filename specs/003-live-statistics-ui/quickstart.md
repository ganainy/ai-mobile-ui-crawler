# Quickstart: Live Statistics Dashboard Implementation

**Feature**: Live Statistics Dashboard Updates  
**Audience**: Developers implementing real-time statistics  
**Date**: January 11, 2026

## Overview

This guide walks through implementing live statistics updates for the mobile-crawler GUI. The implementation connects existing crawler events to the StatsDashboard widget using Qt signals for thread-safe updates.

---

## Prerequisites

**Knowledge Required**:
- Python 3.9+ syntax and type hints
- PySide6 (Qt) basics: signals, slots, QTimer
- SQLite query fundamentals
- Understanding of threading (for signal/slot thread safety)

**Files You'll Modify**:
- `src/mobile_crawler/ui/main_window.py` - Add event handlers
- `src/mobile_crawler/infrastructure/step_log_repository.py` - Add statistics queries
- `src/mobile_crawler/infrastructure/screen_repository.py` - Add count methods

**Files Already Complete** (no changes needed):
- `src/mobile_crawler/ui/widgets/stats_dashboard.py` - UI + update_stats() ready
- `src/mobile_crawler/ui/signal_adapter.py` - All signals defined
- `src/mobile_crawler/core/crawler_loop.py` - Events already emitted

---

## Step 1: Add CrawlStatistics Data Class

**File**: `src/mobile_crawler/ui/main_window.py`

**Location**: Top of file, after imports

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set, List

@dataclass
class CrawlStatistics:
    """Real-time statistics accumulator for active crawl."""
    run_id: int
    start_time: datetime
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    unique_screen_hashes: Set[str] = field(default_factory=set)
    total_screen_visits: int = 0
    ai_call_count: int = 0
    ai_response_times_ms: List[float] = field(default_factory=list)
    
    def avg_ai_response_time(self) -> float:
        """Calculate average AI response time."""
        if not self.ai_response_times_ms:
            return 0.0
        return sum(self.ai_response_times_ms) / len(self.ai_response_times_ms)
    
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time since start."""
        return (datetime.now() - self.start_time).total_seconds()
    
    def screens_per_minute(self) -> float:
        """Calculate screen discovery rate."""
        minutes = self.elapsed_seconds() / 60.0
        if minutes <= 0:
            return 0.0
        return len(self.unique_screen_hashes) / minutes
```

**Why**: Provides in-memory state for fast real-time updates without database queries

---

## Step 2: Add Instance Variables to MainWindow

**File**: `src/mobile_crawler/ui/main_window.py`

**Location**: In `MainWindow.__init__()`, after existing instance variables

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... existing initialization ...
        
        # Statistics tracking
        self._current_stats: Optional[CrawlStatistics] = None
        self._elapsed_timer: QTimer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._update_elapsed_time)
```

**Why**: 
- `_current_stats` holds active crawl statistics
- `_elapsed_timer` triggers elapsed time updates every second

---

## Step 3: Connect Signal Handlers

**File**: `src/mobile_crawler/ui/main_window.py`

**Location**: In `_setup_central_widget()` or dedicated method, after existing signal connections

```python
def _connect_statistics_signals(self):
    """Connect crawler events to statistics handlers."""
    self.signal_adapter.crawl_started.connect(self._on_crawl_started_stats)
    self.signal_adapter.step_completed.connect(self._on_step_completed_stats)
    self.signal_adapter.action_executed.connect(self._on_action_executed_stats)
    self.signal_adapter.screenshot_captured.connect(self._on_screenshot_captured_stats)
    self.signal_adapter.ai_response_received.connect(self._on_ai_response_stats)
    self.signal_adapter.crawl_completed.connect(self._on_crawl_completed_stats)

# Call in __init__() after widgets are created:
# self._connect_statistics_signals()
```

**Why**: Qt signals provide thread-safe event delivery from worker thread to UI thread

---

## Step 4: Implement crawl_started Handler

**File**: `src/mobile_crawler/ui/main_window.py`

```python
def _on_crawl_started_stats(self, run_id: int, target_package: str) -> None:
    """Initialize statistics tracking when crawl starts."""
    # Create new statistics object
    self._current_stats = CrawlStatistics(
        run_id=run_id,
        start_time=datetime.now()
    )
    
    # Reset dashboard display
    if self.stats_dashboard:
        self.stats_dashboard.reset()
        
        # Set max values from settings
        max_steps = self.settings_panel.get_max_steps() if self.settings_panel else 100
        max_duration = self.settings_panel.get_max_duration() if self.settings_panel else 300
        self.stats_dashboard.set_max_steps(max_steps)
        self.stats_dashboard.set_max_duration(max_duration)
    
    # Start elapsed time timer (1-second interval)
    self._elapsed_timer.start(1000)
```

**Why**: Sets up clean state for new crawl, resets UI, starts timer

---

## Step 5: Implement step_completed Handler

**File**: `src/mobile_crawler/ui/main_window.py`

```python
def _on_step_completed_stats(self, run_id: int, step_number: int, 
                             actions_count: int, duration_ms: float) -> None:
    """Update statistics when a step completes."""
    if not self._current_stats or self._current_stats.run_id != run_id:
        return  # Not our run or no active stats
    
    # Increment total steps
    self._current_stats.total_steps += 1
    
    # Update dashboard
    self._update_dashboard_stats()
```

**Why**: Tracks total step count (success/failure tracked separately via actions)

---

## Step 6: Implement action_executed Handler

**File**: `src/mobile_crawler/ui/main_window.py`

```python
def _on_action_executed_stats(self, run_id: int, step_number: int, 
                               action_index: int, result: ActionResult) -> None:
    """Update success/failure counts when action executes."""
    if not self._current_stats or self._current_stats.run_id != run_id:
        return
    
    # Track success vs failure
    if result.success:
        self._current_stats.successful_steps += 1
    else:
        self._current_stats.failed_steps += 1
    
    # Update dashboard
    self._update_dashboard_stats()
```

**Why**: Differentiates successful steps from failures

---

## Step 7: Implement screenshot_captured Handler

**File**: `src/mobile_crawler/ui/main_window.py`

```python
def _on_screenshot_captured_stats(self, run_id: int, step_number: int, 
                                   screenshot_path: str) -> None:
    """Update screen discovery metrics when screenshot captured."""
    if not self._current_stats or self._current_stats.run_id != run_id:
        return
    
    # Increment total visits
    self._current_stats.total_screen_visits += 1
    
    # Get screen hash to track uniqueness
    # Note: Screen may not be saved to DB yet, so query might fail
    # Alternative: Track hashes separately or query later
    try:
        screen = self._services['screen_repository'].get_latest_screen_for_run(run_id)
        if screen:
            self._current_stats.unique_screen_hashes.add(screen.composite_hash)
    except Exception:
        pass  # Screen not yet saved, will be counted on next event
    
    # Update dashboard
    self._update_dashboard_stats()
```

**Why**: Tracks screen discovery (unique vs revisits)

---

## Step 8: Implement ai_response_received Handler

**File**: `src/mobile_crawler/ui/main_window.py`

```python
def _on_ai_response_stats(self, run_id: int, step_number: int, 
                          response_data: Dict[str, Any]) -> None:
    """Update AI performance metrics when response received."""
    if not self._current_stats or self._current_stats.run_id != run_id:
        return
    
    # Extract response time
    response_time = response_data.get('response_time_ms', 0.0)
    
    # Track AI calls
    self._current_stats.ai_call_count += 1
    self._current_stats.ai_response_times_ms.append(response_time)
    
    # Update dashboard
    self._update_dashboard_stats()
```

**Why**: Monitors AI API performance and costs

---

## Step 9: Implement Dashboard Update Method

**File**: `src/mobile_crawler/ui/main_window.py`

```python
def _update_dashboard_stats(self) -> None:
    """Update dashboard display from current statistics."""
    if not self._current_stats or not self.stats_dashboard:
        return
    
    stats = self._current_stats
    
    self.stats_dashboard.update_stats(
        total_steps=stats.total_steps,
        successful_steps=stats.successful_steps,
        failed_steps=stats.failed_steps,
        unique_screens=len(stats.unique_screen_hashes),
        total_visits=stats.total_screen_visits,
        screens_per_minute=stats.screens_per_minute(),
        ai_calls=stats.ai_call_count,
        avg_ai_response_time_ms=stats.avg_ai_response_time(),
        duration_seconds=stats.elapsed_seconds()
    )
```

**Why**: Central method to refresh dashboard from statistics object

---

## Step 10: Implement Elapsed Time Timer

**File**: `src/mobile_crawler/ui/main_window.py`

```python
def _update_elapsed_time(self) -> None:
    """Timer callback to update elapsed time (called every 1 second)."""
    if not self._current_stats:
        return
    
    # Full dashboard update includes elapsed time
    self._update_dashboard_stats()
```

**Why**: Periodic updates for time-based displays

---

## Step 11: Implement crawl_completed Handler

**File**: `src/mobile_crawler/ui/main_window.py`

```python
def _on_crawl_completed_stats(self, run_id: int, total_steps: int, 
                               total_duration_ms: float, reason: str) -> None:
    """Finalize statistics when crawl completes."""
    # Stop timer
    self._elapsed_timer.stop()
    
    # Query database for final accurate values
    try:
        final_stats = self._query_final_statistics(run_id)
        
        if self.stats_dashboard:
            self.stats_dashboard.update_stats(**final_stats)
    except Exception as e:
        # Fallback to in-memory values
        self._update_dashboard_stats()
    
    # Clear statistics object
    self._current_stats = None
```

**Why**: Ensures final values are accurate from database, stops timer

---

## Step 12: Add Database Query Methods

**File**: `src/mobile_crawler/ui/main_window.py`

```python
def _query_final_statistics(self, run_id: int) -> Dict[str, Any]:
    """Query database for accurate final statistics.
    
    Returns:
        Dictionary with all statistics fields for update_stats()
    """
    step_repo = self._services.get('step_log_repository')
    screen_repo = self._services.get('screen_repository')
    
    # Query step statistics
    step_stats = step_repo.get_step_statistics(run_id) if step_repo else {}
    
    # Query screen counts
    unique_screens = screen_repo.count_unique_screens_for_run(run_id) if screen_repo else 0
    total_visits = step_repo.count_screen_visits_for_run(run_id) if step_repo else 0
    
    # Query AI metrics
    ai_stats = step_repo.get_ai_statistics(run_id) if step_repo else {}
    
    # Calculate derived metrics
    duration = (datetime.now() - self._current_stats.start_time).total_seconds() if self._current_stats else 0
    screens_per_min = (unique_screens / (duration / 60.0)) if duration > 0 else 0.0
    
    return {
        'total_steps': step_stats.get('total_steps', 0),
        'successful_steps': step_stats.get('successful_steps', 0),
        'failed_steps': step_stats.get('failed_steps', 0),
        'unique_screens': unique_screens,
        'total_visits': total_visits,
        'screens_per_minute': screens_per_min,
        'ai_calls': ai_stats.get('ai_calls', 0),
        'avg_ai_response_time_ms': ai_stats.get('avg_response_time_ms', 0.0),
        'duration_seconds': duration
    }
```

**Why**: Provides database-backed final statistics for accuracy

---

## Step 13: Extend StepLogRepository

**File**: `src/mobile_crawler/infrastructure/step_log_repository.py`

```python
def get_step_statistics(self, run_id: int) -> Dict[str, int]:
    """Get aggregated step statistics for a run."""
    conn = self.db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_steps,
            SUM(CASE WHEN execution_success = 1 THEN 1 ELSE 0 END) as successful,
            SUM(CASE WHEN execution_success = 0 THEN 1 ELSE 0 END) as failed
        FROM step_logs 
        WHERE run_id = ?
    """, (run_id,))
    
    row = cursor.fetchone()
    if not row:
        return {'total_steps': 0, 'successful_steps': 0, 'failed_steps': 0}
    
    return {
        'total_steps': row[0] or 0,
        'successful_steps': row[1] or 0,
        'failed_steps': row[2] or 0
    }

def get_ai_statistics(self, run_id: int) -> Dict[str, Any]:
    """Get AI performance statistics for a run."""
    conn = self.db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as ai_calls,
            AVG(ai_response_time_ms) as avg_response_time
        FROM step_logs 
        WHERE run_id = ? AND ai_response_time_ms IS NOT NULL
    """, (run_id,))
    
    row = cursor.fetchone()
    if not row:
        return {'ai_calls': 0, 'avg_response_time_ms': 0.0}
    
    return {
        'ai_calls': row[0] or 0,
        'avg_response_time_ms': row[1] or 0.0
    }

def count_screen_visits_for_run(self, run_id: int) -> int:
    """Count total screen visits (including revisits) for a run."""
    conn = self.db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM step_logs 
        WHERE run_id = ? 
            AND (from_screen_id IS NOT NULL OR to_screen_id IS NOT NULL)
    """, (run_id,))
    
    row = cursor.fetchone()
    return row[0] if row else 0
```

**Why**: Provides database aggregation methods for validation and final stats

---

## Step 14: Extend ScreenRepository

**File**: `src/mobile_crawler/infrastructure/screen_repository.py`

```python
def count_unique_screens_for_run(self, run_id: int) -> int:
    """Count unique screens discovered in a specific run."""
    conn = self.db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(DISTINCT id) 
        FROM screens 
        WHERE first_seen_run_id = ?
    """, (run_id,))
    
    row = cursor.fetchone()
    return row[0] if row else 0

def get_latest_screen_for_run(self, run_id: int) -> Optional[Screen]:
    """Get the most recently discovered screen for a run."""
    conn = self.db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM screens 
        WHERE first_seen_run_id = ? 
        ORDER BY first_seen_step DESC 
        LIMIT 1
    """, (run_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
    
    return self._row_to_screen(row)
```

**Why**: Enables screen uniqueness tracking for discovery metrics

---

## Step 15: Test the Implementation

**Manual Testing**:
1. Start the GUI: `python run_ui.py`
2. Configure device, app, AI model
3. Start a crawl
4. Observe statistics dashboard updating in real-time:
   - Total steps incrementing
   - Success/failure counts updating
   - Elapsed time ticking every second
   - Progress bars advancing
5. Stop or complete the crawl
6. Verify final statistics are accurate

**Automated Testing** (create `tests/integration/test_stats_updates.py`):
```python
def test_statistics_update_on_step_completed():
    """Test that step completion updates statistics."""
    # Setup
    main_window = MainWindow()
    main_window._current_stats = CrawlStatistics(run_id=1, start_time=datetime.now())
    
    # Emit signal
    main_window.signal_adapter.step_completed.emit(1, 1, 2, 150.0)
    
    # Verify
    assert main_window._current_stats.total_steps == 1
    assert main_window.stats_dashboard.get_total_steps() == 1
```

---

## Common Pitfalls

### 1. Calling Dashboard Methods from Worker Thread

**❌ Wrong**:
```python
# In crawler_loop.py (worker thread)
self.main_window.stats_dashboard.update_stats(...)  # CRASH: Not UI thread
```

**✅ Correct**:
```python
# Always use signals
self.listener.on_step_completed(run_id, step, actions, duration)  # Emits signal
```

---

### 2. Forgetting Defensive Checks

**❌ Wrong**:
```python
def _on_step_completed_stats(self, run_id, step_number, actions_count, duration_ms):
    self._current_stats.total_steps += 1  # Crashes if None
```

**✅ Correct**:
```python
def _on_step_completed_stats(self, run_id, step_number, actions_count, duration_ms):
    if not self._current_stats or self._current_stats.run_id != run_id:
        return
    self._current_stats.total_steps += 1
```

---

### 3. Division by Zero

**❌ Wrong**:
```python
screens_per_minute = unique_screens / (elapsed_seconds / 60)  # Crash if elapsed = 0
```

**✅ Correct**:
```python
minutes = elapsed_seconds / 60.0
screens_per_minute = unique_screens / minutes if minutes > 0 else 0.0
```

---

## Performance Tips

1. **Batch Updates**: If multiple events arrive rapidly, consider batching dashboard updates
2. **Limit List Growth**: Cap AI response time list at reasonable size (e.g., 1000 entries)
3. **Avoid Blocking**: Never do slow I/O in signal handlers (use QThreadPool if needed)
4. **Profile First**: Only optimize if actual performance issues observed

---

## Next Steps

After implementation:
1. Run integration tests
2. Test with real devices and apps
3. Monitor performance during long crawls
4. Add logging for debugging event flow
5. Consider adding statistics export feature (future enhancement)

---

## Resources

- **PySide6 Signals/Slots**: https://doc.qt.io/qtforpython-6/overviews/signalsandslots.html
- **Qt Threading**: https://doc.qt.io/qt-6/thread-basics.html
- **SQLite Aggregation**: https://www.sqlite.org/lang_aggfunc.html
- **Project Spec**: `specs/003-live-statistics-ui/spec.md`
- **Data Model**: `specs/003-live-statistics-ui/data-model.md`
- **Event Contracts**: `specs/003-live-statistics-ui/contracts/statistics-events.md`

---

## Summary

This implementation connects existing infrastructure (signals, repositories, UI widgets) to enable real-time statistics. The key is using Qt signals for thread safety and maintaining lightweight in-memory state for fast updates. Database queries provide validation and final accurate values.
