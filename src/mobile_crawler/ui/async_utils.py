"""Utilities for asynchronous operations in the UI."""

import traceback
from typing import Any, Callable, Dict, Optional, Tuple

from PySide6.QtCore import QThread, Signal


class AsyncOperation(QThread):
    """Generic worker thread for running a target function in the background.

    This class moves heavy lifting (like ADB commands or network requests) 
    off the main UI thread to prevent interface freezing.

    Signals:
        started: Emitted when the operation starts
        finished: Emitted when the operation finishes (regardless of success/failure)
        result_ready: Emitted with the return value if the target succeeds
        error_occurred: Emitted with an error message string if an exception occurs
    """

    started_signal = Signal()
    finished_signal = Signal()
    result_ready = Signal(object)
    error_occurred = Signal(str)

    def __init__(
        self, 
        target: Callable, 
        args: Optional[Tuple[Any, ...]] = None, 
        kwargs: Optional[Dict[str, Any]] = None,
        parent=None
    ):
        """Initialize the async operation.

        Args:
            target: The function or method to execute in the background
            args: Positional arguments for the target
            kwargs: Keyword arguments for the target
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.target = target
        self.args = args or ()
        self.kwargs = kwargs or {}

    def run(self):
        """Execute the target function and emit appropriate signals."""
        self.started_signal.emit()
        try:
            result = self.target(*self.args, **self.kwargs)
            self.result_ready.emit(result)
        except Exception as e:
            error_msg = f"Error in background operation {self.target.__name__ if hasattr(self.target, '__name__') else str(self.target)}: {e}"
            print(error_msg)
            traceback.print_exc()
            self.error_occurred.emit(str(e))
        finally:
            self.finished_signal.emit()
