# Data Model: Statistics Display and Crawl Stability

**Feature**: 025-stats-and-stability  
**Date**: 2026-01-16

## Overview

This feature extends existing data structures to track and display operation timing metrics. No new database tables are required; all changes are in-memory state tracking.

## Entities

### 1. CrawlStatistics (Extended)

**Location**: `src/mobile_crawler/ui/main_window.py` (lines 69-101)

**Current Fields**:
```python
@dataclass
class CrawlStatistics:
    run_id: int
    start_time: datetime
    total_steps: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    unique_screen_hashes: Set[str] = field(default_factory=set)
    total_screen_visits: int = 0
    ai_call_count: int = 0
    ai_response_times_ms: List[float] = field(default_factory=list)
    last_step_number: int = 0
```

**New Fields** (to be added):
```python
    # OCR timing (FR-001, FR-004)
    ocr_total_time_ms: float = 0.0
    ocr_operation_count: int = 0
    
    # Action execution timing (FR-002, FR-005)
    action_total_time_ms: float = 0.0
    action_count: int = 0
    
    # Screenshot capture timing (FR-003, FR-006)
    screenshot_total_time_ms: float = 0.0
    screenshot_count: int = 0
```

**New Methods**:
```python
    def avg_ocr_time_ms(self) -> float:
        """Average OCR processing time in milliseconds."""
        if self.ocr_operation_count == 0:
            return 0.0
        return self.ocr_total_time_ms / self.ocr_operation_count
    
    def avg_action_time_ms(self) -> float:
        """Average action execution time in milliseconds."""
        if self.action_count == 0:
            return 0.0
        return self.action_total_time_ms / self.action_count
    
    def avg_screenshot_time_ms(self) -> float:
        """Average screenshot capture time in milliseconds."""
        if self.screenshot_count == 0:
            return 0.0
        return self.screenshot_total_time_ms / self.screenshot_count
```

**Validation Rules**:
- All timing values must be non-negative
- All counts must be non-negative integers
- Averages return 0.0 when count is 0 (not NaN/error)

---

### 2. CrawlerEventListener (Extended Interface)

**Location**: `src/mobile_crawler/core/crawler_event_listener.py`

**Current Methods**:
- `on_crawl_started(run_id, app_package)`
- `on_step_started(run_id, step_number)`
- `on_action_executed(run_id, step, action_index, result)`
- `on_step_completed(run_id, step, actions_count, duration_ms)`
- `on_crawl_completed(run_id, steps, duration_ms, reason, ocr_avg_ms)`
- `on_screen_processed(run_id, step, screen_id, is_new, visit_count, total)`
- `on_ai_request_sent(run_id, step, request_data)`
- `on_ai_response_received(run_id, step, response_data)`
- `on_error(run_id, step, error)`
- `on_state_changed(run_id, old_state, new_state)`
- `on_screenshot_captured(run_id, step, path)`
- `on_step_paused(run_id, step)`
- `on_debug_log(run_id, step, msg)`
- `on_recovery_started/completed/exhausted(...)`

**New Methods** (to be added):
```python
    def on_ocr_completed(
        self,
        run_id: int,
        step_number: int,
        duration_ms: float,
        element_count: int
    ) -> None:
        """Called after OCR grounding completes.
        
        Args:
            run_id: Current run ID
            step_number: Current step number
            duration_ms: OCR processing time in milliseconds
            element_count: Number of text elements detected
        """
        pass
    
    def on_screenshot_timing(
        self,
        run_id: int,
        step_number: int,
        duration_ms: float
    ) -> None:
        """Called after screenshot capture completes.
        
        Args:
            run_id: Current run ID
            step_number: Current step number
            duration_ms: Screenshot capture time in milliseconds
        """
        pass
```

**Note**: Action timing is already available via `on_action_executed` result object's inferred duration.

---

### 3. QtSignalAdapter (Extended)

**Location**: `src/mobile_crawler/ui/signal_adapter.py`

**New Signals** (to be added):
```python
    # New timing signals
    ocr_completed = Signal(int, int, float, int)  # run_id, step, duration_ms, element_count
    screenshot_timing = Signal(int, int, float)   # run_id, step, duration_ms
```

**New Handler Methods**:
```python
    def on_ocr_completed(
        self, run_id: int, step_number: int, duration_ms: float, element_count: int
    ) -> None:
        self.ocr_completed.emit(run_id, step_number, duration_ms, element_count)
    
    def on_screenshot_timing(
        self, run_id: int, step_number: int, duration_ms: float
    ) -> None:
        self.screenshot_timing.emit(run_id, step_number, duration_ms)
```

---

### 4. StatsDashboard (Extended Widget)

**Location**: `src/mobile_crawler/ui/widgets/stats_dashboard.py`

**New UI Elements**:
```python
    # Operation Timing section (after AI Performance, before Duration)
    operation_timing_label: QLabel  # Section header
    ocr_avg_label: QLabel           # "OCR Avg: 0ms"
    action_avg_label: QLabel        # "Action Avg: 0ms"
    screenshot_avg_label: QLabel    # "Screenshot Avg: 0ms"
```

**Extended update_stats Method**:
```python
    def update_stats(
        self,
        # ...existing params...
        ocr_avg_ms: float = 0.0,
        action_avg_ms: float = 0.0,
        screenshot_avg_ms: float = 0.0,
    ):
```

---

## State Transitions

### Timing Accumulation Flow

```
[CrawlerLoop._execute_step]
        │
        ├── ScreenshotCapture.capture_full()
        │       └── _emit_event("on_screenshot_timing", duration_ms)
        │
        ├── GroundingManager.process_screenshot()
        │       └── _emit_event("on_ocr_completed", duration_ms, elements)
        │
        └── ActionExecutor.execute()
                └── (timing calculated from action result)
                    └── _emit_event("on_action_executed", result)
                        
        ↓
[QtSignalAdapter]
        │
        └── Emits Qt signals → Main thread
        
        ↓
[MainWindow event handlers]
        │
        └── Updates CrawlStatistics accumulator
        
        ↓
[StatsDashboard.update_stats()]
        │
        └── Displays averages in UI
```

---

## Validation Rules

| Field | Type | Validation |
|-------|------|------------|
| `duration_ms` | float | Must be >= 0 |
| `element_count` | int | Must be >= 0 |
| `*_count` | int | Must be >= 0 |
| `*_total_time_ms` | float | Must be >= 0 |

## Edge Cases

| Scenario | Handling |
|----------|----------|
| No OCR performed | Display "OCR Avg: N/A" or "0ms" |
| Operations < 1ms | Display "< 1ms" or actual value |
| Division by zero | Return 0.0 (handled in avg methods) |
| UI update during shutdown | Ignore signals after crawl stopped |
