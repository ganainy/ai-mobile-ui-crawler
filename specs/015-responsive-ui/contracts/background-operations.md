# API Contracts: Background Operations

**Feature**: 015-responsive-ui  
**Date**: 2025-01-27

## Overview

This document defines the contracts (interfaces, signals, methods) for background operations, worker threads, and operation management. These contracts ensure consistent implementation across all background operations.

---

## Worker Thread Contract

All background operation workers must implement this contract.

### BaseWorker (Abstract Base Class)

```python
class BaseWorker(QThread):
    """Base class for all background operation workers."""
    
    # Signals (must be defined in subclasses)
    progress = Signal(float, str)  # progress_percentage, status_message
    completed = Signal(object)  # result object (operation-specific)
    error = Signal(str)  # error_message
    cancelled = Signal()  # emitted when operation is cancelled
    
    def __init__(self, operation_id: str):
        """Initialize worker.
        
        Args:
            operation_id: Unique identifier for this operation
        """
        super().__init__()
        self.operation_id = operation_id
        self._cancelled = False
    
    def run(self) -> None:
        """Execute the background operation.
        
        Must be implemented by subclasses.
        Must check self.isInterruptionRequested() periodically.
        Must emit progress, completed/error signals.
        """
        raise NotImplementedError
    
    def cancel(self) -> None:
        """Request cancellation of the operation."""
        self._cancelled = True
        self.requestInterruption()
    
    def is_cancelled(self) -> bool:
        """Check if operation has been cancelled."""
        return self._cancelled or self.isInterruptionRequested()
```

### Signal Contracts

**progress Signal**:
- **Parameters**: `(float, str)`
  - `progress_percentage`: Float between 0.0 and 100.0, or -1.0 for indeterminate
  - `status_message`: Human-readable status message (e.g., "Extracting APK...")
- **When to emit**: Periodically during operation (at least every 2 seconds for long operations)
- **Thread safety**: Automatically handled by Qt (signals are thread-safe)

**completed Signal**:
- **Parameters**: `(object)` - Operation-specific result
  - RunHistoryWorker: `List[Run]`
  - ReportGenerationWorker: `str` (file path)
  - MobSFAnalysisWorker: `str` (results directory path)
  - RunDeletionWorker: `int` (deleted run_id)
  - DeviceDetectionWorker: `List[str]` (device IDs)
  - AppListingWorker: `List[str]` (package names)
- **When to emit**: When operation completes successfully
- **Thread safety**: Automatically handled by Qt

**error Signal**:
- **Parameters**: `(str)` - Error message (user-friendly, not raw exception)
- **When to emit**: When operation fails with an exception
- **Thread safety**: Automatically handled by Qt

**cancelled Signal**:
- **Parameters**: None
- **When to emit**: When operation is cancelled by user
- **Thread safety**: Automatically handled by Qt

---

## OperationManager Contract

Manages all background operations in the application.

### OperationManager Class

```python
class OperationManager(QObject):
    """Manages background operations and prevents duplicates."""
    
    # Signals
    operation_started = Signal(str, OperationType)  # operation_id, operation_type
    operation_completed = Signal(str, OperationType)  # operation_id, operation_type
    operation_failed = Signal(str, OperationType, str)  # operation_id, operation_type, error_message
    
    def __init__(self, max_concurrent: int = 5):
        """Initialize operation manager.
        
        Args:
            max_concurrent: Maximum concurrent operations allowed
        """
        super().__init__()
        self._active_operations: Dict[str, BackgroundOperation] = {}
        self._max_concurrent = max_concurrent
    
    def can_start_operation(
        self, 
        operation_type: OperationType, 
        run_id: Optional[int] = None
    ) -> bool:
        """Check if operation can be started (not duplicate, under limit).
        
        Args:
            operation_type: Type of operation
            run_id: Optional run ID for operation-specific checks
            
        Returns:
            True if operation can start, False if duplicate or limit reached
        """
        # Check for duplicate operation
        # Check concurrent operation limit
        # Return result
        pass
    
    def start_operation(
        self, 
        operation: BackgroundOperation, 
        worker: BaseWorker
    ) -> bool:
        """Start a background operation.
        
        Args:
            operation: BackgroundOperation instance
            worker: Worker thread instance
            
        Returns:
            True if started successfully, False if duplicate/limit reached
        """
        # Check can_start_operation()
        # Add to active_operations
        # Start worker thread
        # Connect signals
        # Emit operation_started signal
        pass
    
    def get_operation(self, operation_id: str) -> Optional[BackgroundOperation]:
        """Get active operation by ID."""
        pass
    
    def remove_operation(self, operation_id: str) -> None:
        """Remove completed/failed operation."""
        pass
    
    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel an active operation.
        
        Returns:
            True if cancellation requested, False if operation not found/not cancellable
        """
        pass
```

### Method Contracts

**can_start_operation**:
- **Preconditions**: 
  - `operation_type` is valid OperationType enum value
  - `run_id` is None or positive integer
- **Postconditions**:
  - Returns True only if no duplicate operation exists and concurrent limit not reached
  - Duplicate check: Same `operation_type` + `run_id` combination already active
- **Side effects**: None (read-only check)

**start_operation**:
- **Preconditions**:
  - `operation.status == OperationStatus.PENDING`
  - `can_start_operation()` returns True
  - `worker.operation_id == operation.operation_id`
- **Postconditions**:
  - Operation added to `_active_operations`
  - Worker thread started
  - `operation_started` signal emitted
  - Operation status updated to IN_PROGRESS
- **Side effects**: 
  - Worker thread created and started
  - Signals connected

**cancel_operation**:
- **Preconditions**:
  - `operation_id` exists in `_active_operations`
  - Operation status is IN_PROGRESS
  - Operation is cancellable
- **Postconditions**:
  - Worker `cancel()` method called
  - Operation status updated to CANCELLED
  - `cancelled` signal emitted by worker
- **Side effects**: Worker thread interruption requested

---

## Widget Integration Contract

Widgets that trigger background operations must follow this contract.

### Required Methods

```python
class OperationTriggeringWidget(QWidget):
    """Widget that triggers background operations."""
    
    def _show_loading_indicator(self, operation_type: OperationType) -> None:
        """Show loading indicator for operation.
        
        Must:
        - Display loading indicator within 200ms
        - Disable trigger button
        - Show status message
        """
        pass
    
    def _hide_loading_indicator(self) -> None:
        """Hide loading indicator.
        
        Must:
        - Hide loading indicator
        - Re-enable trigger button
        - Clear status message
        """
        pass
    
    def _handle_operation_completed(self, result: object) -> None:
        """Handle operation completion.
        
        Must:
        - Update UI with result
        - Hide loading indicator
        - Show success message (if applicable)
        """
        pass
    
    def _handle_operation_error(self, error_message: str) -> None:
        """Handle operation error.
        
        Must:
        - Hide loading indicator
        - Show error message (QMessageBox or status label)
        - Re-enable trigger button
        """
        pass
```

### Signal Connections

Widgets must connect worker signals:

```python
# In widget initialization or operation start
worker.progress.connect(self._update_progress)
worker.completed.connect(self._handle_operation_completed)
worker.error.connect(self._handle_operation_error)
worker.cancelled.connect(self._handle_operation_cancelled)
```

---

## Loading Indicator Contract

Loading indicators must follow this contract for consistency.

### LoadingIndicator Widget

```python
class LoadingIndicator(QWidget):
    """Reusable loading indicator component."""
    
    def __init__(self, parent=None):
        """Initialize loading indicator."""
        super().__init__(parent)
        self._setup_ui()
    
    def show_loading(
        self, 
        indicator_type: IndicatorType,
        status_message: str = "",
        progress: float = -1.0
    ) -> None:
        """Show loading indicator.
        
        Args:
            indicator_type: Type of indicator (SPINNER, PROGRESS_BAR, STATUS_LABEL)
            status_message: Status message to display
            progress: Progress value (0.0-100.0 or -1.0 for indeterminate)
        """
        pass
    
    def update_progress(self, progress: float, status_message: str) -> None:
        """Update progress and status message."""
        pass
    
    def hide_loading(self) -> None:
        """Hide loading indicator."""
        pass
```

### Indicator Types

**SPINNER**:
- Shows animated spinner (QProgressBar with indeterminate mode)
- Status message (optional)
- For operations <2 seconds

**PROGRESS_BAR**:
- Shows QProgressBar (determinate or indeterminate)
- Status message
- Progress percentage (if determinate)
- For operations >2 seconds

**STATUS_LABEL**:
- Shows text status message only
- For very short operations or when space is limited

---

## Error Handling Contract

All workers must follow this error handling contract.

### Error Signal Requirements

1. **Error messages must be user-friendly**:
   - No raw exception tracebacks
   - No technical jargon
   - Clear action items when possible

2. **Error handling in run() method**:
   ```python
   def run(self):
       try:
           # Operation logic
           self.completed.emit(result)
       except Exception as e:
           error_msg = self._format_error(e)
           self.error.emit(error_msg)
       finally:
           # Cleanup
   ```

3. **Error formatting**:
   - Database errors: "Failed to load data. Please try again."
   - Network errors: "Connection failed. Please check your network."
   - File errors: "Failed to save file. Please check permissions."
   - Generic: "An error occurred. Please try again."

---

## Testing Contracts

### Worker Testing

Workers must be testable in isolation:

```python
def test_worker_completes_successfully():
    """Test worker completes and emits completed signal."""
    worker = SomeWorker(operation_id="test_1")
    result_received = []
    
    def on_completed(result):
        result_received.append(result)
    
    worker.completed.connect(on_completed)
    worker.start()
    worker.wait()  # Wait for completion
    
    assert len(result_received) == 1
    assert result_received[0] is not None
```

### OperationManager Testing

OperationManager must be testable:

```python
def test_prevents_duplicate_operations():
    """Test duplicate operations are prevented."""
    manager = OperationManager()
    operation1 = BackgroundOperation(...)
    operation2 = BackgroundOperation(...)  # Same type + run_id
    
    assert manager.can_start_operation(OperationType.REPORT_GENERATION, run_id=1)
    manager.start_operation(operation1, worker1)
    assert not manager.can_start_operation(OperationType.REPORT_GENERATION, run_id=1)
```

---

## Compliance

All implementations must:
- ✅ Implement BaseWorker contract for all workers
- ✅ Use OperationManager for operation tracking
- ✅ Emit signals according to contracts
- ✅ Handle errors according to error handling contract
- ✅ Show/hide loading indicators according to widget contract
- ✅ Be testable according to testing contracts

Non-compliance will result in inconsistent behavior and poor user experience.
