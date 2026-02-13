"""Qt signal adapter for bridging core events to GUI."""

from typing import TYPE_CHECKING, Any, Dict, Optional

from PySide6.QtCore import QObject, Signal

from mobile_crawler.core.crawler_event_listener import CrawlerEventListener
from mobile_crawler.domain.models import ActionResult

if TYPE_CHECKING:
    pass


class QtSignalAdapter(QObject):
    """Adapter that implements CrawlerEventListener protocol and emits Qt signals.
    
    This adapter bridges core crawler events to the GUI without requiring
    Qt imports in core modules. All events are emitted as Qt signals
    that can be connected to GUI slots.
    
    Note: This class implements the CrawlerEventListener protocol but uses
    composition instead of inheritance to avoid metaclass conflicts between
    QObject and ABC. The class can be used as a listener by
    passing its method references to core components.
    """

    # Signals for all crawler events
    crawl_started = Signal(int, str)  # run_id, target_package
    step_started = Signal(int, int)  # run_id, step_number
    screenshot_captured = Signal(int, int, str)  # run_id, step_number, screenshot_path
    ai_request_sent = Signal(int, int, dict)  # run_id, step_number, request_data
    ai_response_received = Signal(int, int, dict)  # run_id, step_number, response_data
    action_executed = Signal(int, int, int, object)  # run_id, step_number, action_index, result
    step_completed = Signal(int, int, int, float)  # run_id, step_number, actions_count, duration_ms
    step_paused = Signal(int, int)  # run_id, step_number
    crawl_completed = Signal(int, int, float, str, float)  # run_id, total_steps, total_duration_ms, reason, ocr_avg_ms
    error_occurred = Signal(int, int, object)  # run_id, step_number, error
    state_changed = Signal(int, str, str)  # run_id, old_state, new_state
    screen_processed = Signal(int, int, int, bool, int, int)  # run_id, step, screen_id, is_new, visit_count, total
    debug_log = Signal(int, int, str)  # run_id, step_number, message
    
    # Timing signals
    ocr_completed = Signal(int, int, float, int)  # run_id, step, duration_ms, element_count
    screenshot_timing = Signal(int, int, float)   # run_id, step, duration_ms
    
    # Recovery signals (US Story 3)
    recovery_started = Signal(int, int, int)  # run_id, step, attempt
    recovery_completed = Signal(int, int, bool, float)  # run_id, step, success, duration_ms
    recovery_exhausted = Signal(int, int, int, str)  # run_id, step, attempts, message

    def on_crawl_started(self, run_id: int, target_package: str) -> None:
        """Called when a crawl starts."""
        self.crawl_started.emit(run_id, target_package)

    def on_step_started(self, run_id: int, step_number: int) -> None:
        """Called when a step starts."""
        self.step_started.emit(run_id, step_number)

    def on_screenshot_captured(self, run_id: int, step_number: int, screenshot_path: str) -> None:
        """Called when a screenshot is captured."""
        self.screenshot_captured.emit(run_id, step_number, screenshot_path)

    def on_ai_request_sent(self, run_id: int, step_number: int, request_data: Dict[str, Any]) -> None:
        """Called when an AI request is sent."""
        self.ai_request_sent.emit(run_id, step_number, request_data)

    def on_ai_response_received(self, run_id: int, step_number: int, response_data: Dict[str, Any]) -> None:
        """Called when an AI response is received."""
        self.ai_response_received.emit(run_id, step_number, response_data)

    def on_action_executed(self, run_id: int, step_number: int, action_index: int, result: ActionResult) -> None:
        """Called when an action is executed."""
        self.action_executed.emit(run_id, step_number, action_index, result)

    def on_step_completed(self, run_id: int, step_number: int, actions_count: int, duration_ms: float) -> None:
        """Called when a step completes."""
        self.step_completed.emit(run_id, step_number, actions_count, duration_ms)

    def on_step_paused(self, run_id: int, step_number: int) -> None:
        """Called when a step is paused (step-by-step mode)."""
        self.step_paused.emit(run_id, step_number)

    def on_crawl_completed(
        self,
        run_id: int,
        total_steps: int,
        total_duration_ms: float,
        reason: str,
        ocr_avg_ms: float = 0.0
    ) -> None:
        """Called when a crawl completes."""
        self.crawl_completed.emit(run_id, total_steps, total_duration_ms, reason, ocr_avg_ms)

    def on_error(self, run_id: int, step_number: Optional[int], error: Exception) -> None:
        """Called when an error occurs."""
        # Use -1 for step_number if None
        step = step_number if step_number is not None else -1
        self.error_occurred.emit(run_id, step, error)

    def on_state_changed(self, run_id: int, old_state: str, new_state: str) -> None:
        """Called when crawler state changes."""
        self.state_changed.emit(run_id, old_state, new_state)

    def on_screen_processed(
        self,
        run_id: int,
        step_number: int,
        screen_id: int,
        is_new: bool,
        visit_count: int,
        total_screens: int
    ) -> None:
        """Called when a screen is processed."""
        self.screen_processed.emit(run_id, step_number, screen_id, is_new, visit_count, total_screens)

    def on_debug_log(self, run_id: int, step_number: int, message: str) -> None:
        """Called when a debug log message should be displayed."""
        self.debug_log.emit(run_id, step_number, message)

    def on_ocr_completed(
        self, run_id: int, step_number: int, duration_ms: float, element_count: int
    ) -> None:
        """Called after OCR grounding completes."""
        self.ocr_completed.emit(run_id, step_number, duration_ms, element_count)

    def on_screenshot_timing(self, run_id: int, step_number: int, duration_ms: float) -> None:
        """Called after screenshot capture completes."""
        self.screenshot_timing.emit(run_id, step_number, duration_ms)

    def on_recovery_started(self, run_id: int, step_number: int, attempt_number: int) -> None:
        """Called when a crash recovery attempt starts."""
        self.recovery_started.emit(run_id, step_number, attempt_number)

    def on_recovery_completed(self, run_id: int, step_number: int, success: bool, duration_ms: float) -> None:
        """Called when a crash recovery attempt completes."""
        self.recovery_completed.emit(run_id, step_number, success, duration_ms)

    def on_recovery_exhausted(self, run_id: int, step_number: int, attempts: int, message: str) -> None:
        """Called when all recovery attempts are exhausted."""
        self.recovery_exhausted.emit(run_id, step_number, attempts, message)
