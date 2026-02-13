# Data Model: Responsive UI with Loading Indicators

**Feature**: 015-responsive-ui  
**Date**: 2025-01-27

## Overview

This feature introduces data structures for managing background operations, loading indicator state, and operation tracking. The data model is primarily in-memory (UI state) with minimal persistence requirements.

## Entities

### BackgroundOperation

Represents a long-running task executing in a background thread.

**Attributes**:
- `operation_id: str` - Unique identifier for this operation instance
- `operation_type: OperationType` - Type of operation (enum: RUN_HISTORY_LOAD, REPORT_GENERATION, MOBSF_ANALYSIS, RUN_DELETION, DEVICE_DETECTION, APP_LISTING)
- `status: OperationStatus` - Current status (enum: PENDING, IN_PROGRESS, COMPLETED, FAILED, CANCELLED)
- `run_id: Optional[int]` - Associated run ID (if applicable)
- `progress: float` - Progress percentage (0.0 to 100.0, or -1.0 for indeterminate)
- `status_message: str` - Current phase/status message (e.g., "Extracting APK...")
- `start_time: datetime` - When operation started
- `end_time: Optional[datetime]` - When operation completed/failed
- `error_message: Optional[str]` - Error message if operation failed
- `worker: Optional[QThread]` - Reference to worker thread (for cancellation)
- `cancellable: bool` - Whether operation can be cancelled

**State Transitions**:
```
PENDING → IN_PROGRESS → COMPLETED
                    ↓
                  FAILED
                    ↓
                 CANCELLED (if cancellable)
```

**Validation Rules**:
- `operation_id` must be unique within active operations
- `progress` must be between -1.0 and 100.0
- `end_time` must be None when status is PENDING or IN_PROGRESS
- `error_message` must be None when status is not FAILED
- `run_id` required for REPORT_GENERATION, MOBSF_ANALYSIS, RUN_DELETION

**Relationships**:
- One BackgroundOperation can be associated with one Run (via run_id)
- One BackgroundOperation has one QThread worker

---

### LoadingIndicatorState

Tracks the visual state of a loading indicator in the UI.

**Attributes**:
- `is_visible: bool` - Whether indicator is currently visible
- `indicator_type: IndicatorType` - Type of indicator (enum: SPINNER, PROGRESS_BAR, STATUS_LABEL)
- `progress_value: float` - Progress value (0.0 to 100.0, or -1.0 for indeterminate)
- `status_text: str` - Status message to display
- `associated_button: Optional[QPushButton]` - Button that triggered the operation (for disabling)

**State Transitions**:
```
HIDDEN → VISIBLE (when operation starts)
VISIBLE → HIDDEN (when operation completes/fails/cancels)
```

**Validation Rules**:
- `progress_value` must be between -1.0 and 100.0
- `status_text` should not be empty when `is_visible` is True
- `indicator_type` determines which UI elements are shown

**Relationships**:
- One LoadingIndicatorState is associated with one BackgroundOperation
- One LoadingIndicatorState may be associated with one QPushButton

---

### OperationQueue

Manages multiple concurrent background operations.

**Attributes**:
- `active_operations: Dict[str, BackgroundOperation]` - Dictionary of active operations by operation_id
- `max_concurrent: int` - Maximum concurrent operations (default: 5)
- `operation_history: List[BackgroundOperation]` - Recent completed operations (for notifications)

**Operations**:
- `add_operation(operation: BackgroundOperation) -> bool` - Add operation, returns False if duplicate
- `remove_operation(operation_id: str)` - Remove completed/failed operation
- `get_operation(operation_id: str) -> Optional[BackgroundOperation]` - Get operation by ID
- `get_operations_by_type(operation_type: OperationType) -> List[BackgroundOperation]` - Get all operations of a type
- `get_operations_by_run_id(run_id: int) -> List[BackgroundOperation]` - Get operations for a run
- `can_start_operation(operation_type: OperationType, run_id: Optional[int] = None) -> bool` - Check if operation can start (not duplicate, under max concurrent)

**Validation Rules**:
- `active_operations` size must not exceed `max_concurrent`
- Operation IDs must be unique within `active_operations`
- `operation_history` should be limited to recent N operations (e.g., last 20)

**Relationships**:
- OperationQueue contains multiple BackgroundOperation instances
- OperationQueue is a singleton (one instance per application)

---

## Enumerations

### OperationType

```python
class OperationType(Enum):
    RUN_HISTORY_LOAD = "run_history_load"
    REPORT_GENERATION = "report_generation"
    MOBSF_ANALYSIS = "mobsf_analysis"
    RUN_DELETION = "run_deletion"
    DEVICE_DETECTION = "device_detection"
    APP_LISTING = "app_listing"
    STARTUP_CLEANUP = "startup_cleanup"
```

### OperationStatus

```python
class OperationStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### IndicatorType

```python
class IndicatorType(Enum):
    SPINNER = "spinner"  # For short operations (<2s)
    PROGRESS_BAR = "progress_bar"  # For medium/long operations
    STATUS_LABEL = "status_label"  # Text-only status
```

---

## Data Flow

### Operation Lifecycle

```
User Action
    ↓
OperationManager.can_start_operation() check
    ↓
Create BackgroundOperation (status: PENDING)
    ↓
Create Worker Thread
    ↓
Start Worker → BackgroundOperation (status: IN_PROGRESS)
    ↓
Worker emits progress signals → Update LoadingIndicatorState
    ↓
Worker completes → BackgroundOperation (status: COMPLETED/FAILED)
    ↓
Remove from OperationQueue
    ↓
Hide LoadingIndicatorState
    ↓
Show notification (if operation was long-running)
```

### Signal Flow

```
Worker Thread (Background)
    ↓ emits progress signal
QtSignalAdapter (Thread-safe bridge)
    ↓ emits Qt signal
UI Thread (Main)
    ↓ connects to slot
LoadingIndicatorState.update()
    ↓
UI Widget updates (QProgressBar, QLabel, etc.)
```

---

## Persistence

**No persistence required** - All state is in-memory UI state. Operations are transient:
- Active operations exist only while running
- Operation history is kept in memory for recent notifications
- No need to persist operation state across application restarts

**Exception**: If operation is in progress when application closes:
- Application should attempt graceful shutdown (wait for operations to complete or cancel)
- No persistence needed - operations can be restarted on next launch

---

## Validation and Constraints

### Operation ID Generation

- Format: `{operation_type}_{run_id}_{timestamp}` or `{operation_type}_{timestamp}` if no run_id
- Must be unique within active operations
- Used as key in OperationQueue.active_operations

### Progress Tracking

- Indeterminate progress: `progress = -1.0` (spinner, no percentage)
- Determinate progress: `progress = 0.0 to 100.0` (progress bar with percentage)
- Status messages should update at least every 2 seconds for long operations

### Concurrent Operation Limits

- Default `max_concurrent = 5` operations
- Prevents resource exhaustion
- Users can still interact with UI even if limit reached (just can't start new operations)

---

## Integration Points

### With Existing Code

- **RunRepository**: Used by RunHistoryWorker for loading runs
- **ReportGenerator**: Used by ReportGenerationWorker for PDF creation
- **MobSFManager**: Used by MobSFAnalysisWorker for static analysis
- **DeviceDetection**: Used by DeviceDetectionWorker for device listing
- **AppiumDriver**: Used by AppListingWorker for app package listing
- **DatabaseManager**: Provides connections to worker threads

### Widget Integration

- **RunHistoryView**: Uses RunHistoryWorker, shows loading indicator in table area
- **DeviceSelector**: Uses DeviceDetectionWorker, shows loading on refresh button
- **AppSelector**: Uses AppListingWorker, shows loading on refresh button
- **MainWindow**: Hosts OperationManager, coordinates notifications

---

## Future Extensions

Potential enhancements (not in current scope):
- Operation persistence (save/restore operations across restarts)
- Operation scheduling (queue operations for later execution)
- Operation prioritization (high-priority operations run first)
- Operation retry logic (automatic retry on failure)
- Operation analytics (track operation durations, success rates)
