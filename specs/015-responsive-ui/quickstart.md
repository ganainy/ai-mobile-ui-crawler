# Quickstart Guide: Responsive UI with Loading Indicators

**Feature**: 015-responsive-ui  
**Date**: 2025-01-27

This guide provides step-by-step instructions for implementing background operations with loading indicators in the mobile crawler UI.

---

## Overview

This feature makes the UI responsive by moving long-running operations to background threads and providing visual feedback through loading indicators. The implementation follows existing patterns (QThread workers, Qt signals) and extends them consistently across all blocking operations.

---

## Architecture

### Components

1. **BaseWorker**: Abstract base class for all background operation workers
2. **OperationManager**: Manages active operations and prevents duplicates
3. **LoadingIndicator**: Reusable UI component for loading feedback
4. **Operation-specific Workers**: One worker per operation type (RunHistoryWorker, ReportGenerationWorker, etc.)

### Flow

```
User Action → Widget
    ↓
Widget checks OperationManager.can_start_operation()
    ↓
Widget creates Worker + BackgroundOperation
    ↓
Widget shows LoadingIndicator
    ↓
Widget starts Worker thread
    ↓
Worker executes operation in background
    ↓ (emits progress signals)
Widget updates LoadingIndicator
    ↓ (emits completed/error signal)
Widget handles result/error
    ↓
Widget hides LoadingIndicator
```

---

## Step-by-Step Implementation

### Step 1: Create BaseWorker Class

**File**: `src/mobile_crawler/ui/workers/__init__.py`

```python
from PySide6.QtCore import QThread, Signal

class BaseWorker(QThread):
    """Base class for all background operation workers."""
    
    progress = Signal(float, str)  # progress_percentage, status_message
    completed = Signal(object)  # result
    error = Signal(str)  # error_message
    cancelled = Signal()  # cancellation
    
    def __init__(self, operation_id: str):
        super().__init__()
        self.operation_id = operation_id
        self._cancelled = False
    
    def run(self):
        """Must be implemented by subclasses."""
        raise NotImplementedError
    
    def cancel(self):
        """Request cancellation."""
        self._cancelled = True
        self.requestInterruption()
    
    def is_cancelled(self):
        return self._cancelled or self.isInterruptionRequested()
```

**Why**: Provides consistent interface for all workers, handles cancellation.

---

### Step 2: Create OperationManager

**File**: `src/mobile_crawler/core/operation_manager.py`

```python
from PySide6.QtCore import QObject, Signal
from typing import Dict, Optional
from enum import Enum

class OperationType(Enum):
    RUN_HISTORY_LOAD = "run_history_load"
    REPORT_GENERATION = "report_generation"
    MOBSF_ANALYSIS = "mobsf_analysis"
    # ... other types

class OperationManager(QObject):
    operation_started = Signal(str, OperationType)
    operation_completed = Signal(str, OperationType)
    operation_failed = Signal(str, OperationType, str)
    
    def __init__(self, max_concurrent: int = 5):
        super().__init__()
        self._active_operations: Dict[str, 'BackgroundOperation'] = {}
        self._max_concurrent = max_concurrent
    
    def can_start_operation(self, operation_type: OperationType, run_id: Optional[int] = None) -> bool:
        # Check for duplicates
        for op in self._active_operations.values():
            if op.operation_type == operation_type and op.run_id == run_id:
                return False
        
        # Check concurrent limit
        if len(self._active_operations) >= self._max_concurrent:
            return False
        
        return True
    
    def start_operation(self, operation: 'BackgroundOperation', worker: 'BaseWorker') -> bool:
        if not self.can_start_operation(operation.operation_type, operation.run_id):
            return False
        
        self._active_operations[operation.operation_id] = operation
        operation.worker = worker
        worker.start()
        self.operation_started.emit(operation.operation_id, operation.operation_type)
        return True
    
    def remove_operation(self, operation_id: str):
        if operation_id in self._active_operations:
            del self._active_operations[operation_id]
```

**Why**: Centralized operation tracking prevents duplicates and manages concurrency.

---

### Step 3: Create LoadingIndicator Widget

**File**: `src/mobile_crawler/ui/widgets/loading_indicator.py`

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt
from enum import Enum

class IndicatorType(Enum):
    SPINNER = "spinner"
    PROGRESS_BAR = "progress_bar"
    STATUS_LABEL = "status_label"

class LoadingIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.hide()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def show_loading(self, indicator_type: IndicatorType, status_message: str = "", progress: float = -1.0):
        self.status_label.setText(status_message)
        
        if indicator_type == IndicatorType.PROGRESS_BAR:
            if progress < 0:
                self.progress_bar.setRange(0, 0)  # Indeterminate
            else:
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(int(progress))
            self.progress_bar.show()
        else:
            self.progress_bar.hide()
        
        self.show()
    
    def update_progress(self, progress: float, status_message: str):
        if progress >= 0:
            self.progress_bar.setValue(int(progress))
        self.status_label.setText(status_message)
    
    def hide_loading(self):
        self.hide()
        self.status_label.clear()
        self.progress_bar.setValue(0)
```

**Why**: Reusable component ensures consistent loading UI across all operations.

---

### Step 4: Implement RunHistoryWorker

**File**: `src/mobile_crawler/ui/workers/run_history_worker.py`

```python
from .base_worker import BaseWorker
from mobile_crawler.infrastructure.run_repository import RunRepository

class RunHistoryWorker(BaseWorker):
    def __init__(self, operation_id: str, run_repository: RunRepository):
        super().__init__(operation_id)
        self.run_repository = run_repository
    
    def run(self):
        try:
            self.progress.emit(-1.0, "Loading run history...")
            
            if self.is_cancelled():
                self.cancelled.emit()
                return
            
            runs = self.run_repository.get_all_runs()
            
            if self.is_cancelled():
                self.cancelled.emit()
                return
            
            self.completed.emit(runs)
        except Exception as e:
            self.error.emit(f"Failed to load run history: {str(e)}")
```

**Why**: Moves database query to background thread, prevents UI blocking.

---

### Step 5: Update RunHistoryView Widget

**File**: `src/mobile_crawler/ui/widgets/run_history_view.py`

Add loading indicator and worker integration:

```python
from mobile_crawler.ui.widgets.loading_indicator import LoadingIndicator, IndicatorType
from mobile_crawler.ui.workers.run_history_worker import RunHistoryWorker
from mobile_crawler.core.operation_manager import OperationManager, OperationType

class RunHistoryView(QWidget):
    def __init__(self, ..., operation_manager: OperationManager):
        # ... existing code ...
        self.operation_manager = operation_manager
        
        # Add loading indicator
        self.loading_indicator = LoadingIndicator(self)
        layout.insertWidget(0, self.loading_indicator)  # At top of layout
    
    def _load_runs(self):
        # Check if operation can start
        if not self.operation_manager.can_start_operation(OperationType.RUN_HISTORY_LOAD):
            return  # Already loading or limit reached
        
        # Show loading indicator
        self.loading_indicator.show_loading(
            IndicatorType.PROGRESS_BAR,
            "Loading run history...",
            -1.0  # Indeterminate
        )
        self.refresh_button.setEnabled(False)
        
        # Create worker
        operation_id = f"run_history_{int(time.time())}"
        worker = RunHistoryWorker(operation_id, self._run_repository)
        
        # Connect signals
        worker.progress.connect(self._on_progress)
        worker.completed.connect(self._on_runs_loaded)
        worker.error.connect(self._on_error)
        worker.cancelled.connect(self._on_cancelled)
        
        # Create operation and start
        from mobile_crawler.core.operation_manager import BackgroundOperation, OperationStatus
        operation = BackgroundOperation(
            operation_id=operation_id,
            operation_type=OperationType.RUN_HISTORY_LOAD,
            status=OperationStatus.PENDING
        )
        
        self.operation_manager.start_operation(operation, worker)
    
    def _on_progress(self, progress: float, status_message: str):
        self.loading_indicator.update_progress(progress, status_message)
    
    def _on_runs_loaded(self, runs):
        # Update table with runs
        self._populate_table(runs)
        self._hide_loading()
    
    def _on_error(self, error_message: str):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Error", error_message)
        self._hide_loading()
    
    def _on_cancelled(self):
        self._hide_loading()
    
    def _hide_loading(self):
        self.loading_indicator.hide_loading()
        self.refresh_button.setEnabled(True)
```

**Why**: Integrates worker with widget, provides user feedback.

---

### Step 6: Initialize OperationManager in MainWindow

**File**: `src/mobile_crawler/ui/main_window.py`

```python
from mobile_crawler.core.operation_manager import OperationManager

class MainWindow(QMainWindow):
    def __init__(self):
        # ... existing code ...
        
        # Create operation manager
        self.operation_manager = OperationManager(max_concurrent=5)
        
        # Pass to widgets that need it
        self.run_history_view = RunHistoryView(
            ...,
            operation_manager=self.operation_manager
        )
```

**Why**: Centralized operation management, shared across widgets.

---

### Step 7: Repeat for Other Operations

Follow the same pattern for:
1. **ReportGenerationWorker**: PDF report generation
2. **MobSFAnalysisWorker**: MobSF static analysis
3. **RunDeletionWorker**: Run deletion with file cleanup
4. **DeviceDetectionWorker**: Device detection via ADB
5. **AppListingWorker**: App package listing

Each follows the same pattern:
- Create worker class extending BaseWorker
- Update widget to use worker
- Add loading indicator
- Connect signals
- Handle completion/error

---

## Testing

### Unit Test Example

```python
def test_run_history_worker_completes():
    """Test RunHistoryWorker loads runs successfully."""
    from unittest.mock import Mock
    
    mock_repo = Mock()
    mock_repo.get_all_runs.return_value = [Run(...), Run(...)]
    
    worker = RunHistoryWorker("test_1", mock_repo)
    result = []
    
    def on_completed(runs):
        result.append(runs)
    
    worker.completed.connect(on_completed)
    worker.start()
    worker.wait(5000)  # Wait max 5 seconds
    
    assert len(result) == 1
    assert len(result[0]) == 2
```

### Integration Test Example

```python
def test_run_history_loading_indicator(qtbot):
    """Test loading indicator appears during run history load."""
    from mobile_crawler.ui.widgets.run_history_view import RunHistoryView
    
    view = RunHistoryView(...)
    qtbot.addWidget(view)
    
    # Trigger load
    view._load_runs()
    
    # Check loading indicator is visible
    assert view.loading_indicator.isVisible()
    
    # Wait for completion
    qtbot.waitUntil(lambda: not view.loading_indicator.isVisible(), timeout=5000)
    
    # Check table populated
    assert view.table.rowCount() > 0
```

---

## Common Patterns

### Pattern 1: Short Operation (<2 seconds)

Use spinner indicator:

```python
self.loading_indicator.show_loading(
    IndicatorType.SPINNER,
    "Detecting devices...",
    -1.0
)
```

### Pattern 2: Medium Operation (2-10 seconds)

Use progress bar (indeterminate):

```python
self.loading_indicator.show_loading(
    IndicatorType.PROGRESS_BAR,
    "Generating report...",
    -1.0
)
```

### Pattern 3: Long Operation (>10 seconds)

Use progress bar with status updates:

```python
# In worker
self.progress.emit(0.0, "Extracting APK...")
# ... work ...
self.progress.emit(33.0, "Uploading to MobSF...")
# ... work ...
self.progress.emit(66.0, "Waiting for analysis...")
# ... work ...
self.progress.emit(100.0, "Complete")
```

---

## Troubleshooting

### Issue: UI Still Freezes

**Cause**: Operation not moved to worker thread  
**Fix**: Ensure all blocking code is in `worker.run()`, not in widget methods

### Issue: Loading Indicator Doesn't Appear

**Cause**: Indicator hidden or not added to layout  
**Fix**: Check `show_loading()` is called, indicator is in widget layout

### Issue: Duplicate Operations

**Cause**: `can_start_operation()` not checked  
**Fix**: Always check before creating worker

### Issue: Worker Not Cleaning Up

**Cause**: Worker thread not properly finished  
**Fix**: Call `worker.wait()` or connect to `finished` signal for cleanup

---

## Next Steps

After implementing all workers:
1. Add operation cancellation UI (cancel buttons)
2. Add system notifications for long operations
3. Add operation history/status panel
4. Optimize worker cleanup and memory management

---

## References

- [PySide6 QThread Documentation](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html)
- [Qt Signals and Slots](https://doc.qt.io/qtforpython-6/overviews/signalsandslots.html)
- [Contract Documentation](./contracts/background-operations.md)
- [Data Model Documentation](./data-model.md)
