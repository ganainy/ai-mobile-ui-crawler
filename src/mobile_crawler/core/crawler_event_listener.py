"""Protocol for crawler event listeners."""

from abc import ABC, abstractmethod
from typing import Any

from mobile_crawler.domain.models import ActionResult


class CrawlerEventListener(ABC):
    """Protocol for listening to crawler events."""

    @abstractmethod
    def on_crawl_started(self, run_id: int, target_package: str) -> None:
        """Called when a crawl starts."""
        pass

    @abstractmethod
    def on_step_started(self, run_id: int, step_number: int) -> None:
        """Called when a step starts."""
        pass

    @abstractmethod
    def on_screenshot_captured(self, run_id: int, step_number: int, screenshot_path: str) -> None:
        """Called when a screenshot is captured."""
        pass

    @abstractmethod
    def on_ai_request_sent(self, run_id: int, step_number: int, request_data: dict[str, Any]) -> None:
        """Called when an AI request is sent."""
        pass

    @abstractmethod
    def on_ai_response_received(self, run_id: int, step_number: int, response_data: dict[str, Any]) -> None:
        """Called when an AI response is received."""
        pass

    @abstractmethod
    def on_action_executed(self, run_id: int, step_number: int, action_index: int, result: ActionResult) -> None:
        """Called when an action is executed."""
        pass

    @abstractmethod
    def on_step_completed(self, run_id: int, step_number: int, actions_count: int, duration_ms: float) -> None:
        """Called when a step completes."""
        pass

    @abstractmethod
    def on_crawl_completed(
        self,
        run_id: int,
        total_steps: int,
        total_duration_ms: float,
        reason: str,
        ocr_avg_ms: float = 0.0
    ) -> None:
        """Called when a crawl completes."""
        pass

    @abstractmethod
    def on_error(self, run_id: int, step_number: int | None, error: Exception) -> None:
        """Called when an error occurs.

        Args:
            run_id: The run ID where the error occurred
            step_number: Step number if error occurred during a step, else None
            error: The exception. May be a CrawlerError with structured context
                   accessible via error.context and error.to_log_dict().
        """
        pass

    @abstractmethod
    def on_state_changed(self, run_id: int, old_state: str, new_state: str) -> None:
        """Called when the crawler state changes."""
        pass

    @abstractmethod
    def on_screen_processed(
        self,
        run_id: int,
        step_number: int,
        screen_id: int,
        is_new: bool,
        visit_count: int,
        total_screens: int
    ) -> None:
        """Called when a screen is processed by the screen tracker."""
        pass

    @abstractmethod
    def on_debug_log(self, run_id: int, step_number: int, message: str) -> None:
        """Called to emit a debug log message to the UI."""
        pass

    @abstractmethod
    def on_ocr_completed(
        self,
        run_id: int,
        step_number: int,
        duration_ms: float,
        element_count: int
    ) -> None:
        """Called after OCR grounding completes."""
        pass

    @abstractmethod
    def on_screenshot_timing(
        self,
        run_id: int,
        step_number: int,
        duration_ms: float
    ) -> None:
        """Called after screenshot capture completes."""
        pass

    def on_recovery_started(self, run_id: int, step_number: int, attempt_number: int) -> None:
        """Called when a crash recovery attempt starts."""
        return None

    def on_recovery_completed(self, run_id: int, step_number: int, success: bool, duration_ms: float) -> None:
        """Called when a crash recovery attempt completes."""
        return None

    def on_recovery_exhausted(self, run_id: int, step_number: int, attempts: int, message: str) -> None:
        """Called when all recovery attempts are exhausted."""
        return None

    def on_step_phase_transition(
        self,
        run_id: int,
        step_number: int,
        from_phase: str,
        to_phase: str,
        duration_ms: float,
    ) -> None:
        """Called when a step phase transition occurs.

        Args:
            run_id: The run ID
            step_number: Step number within the run
            from_phase: Previous phase (e.g., "capture")
            to_phase: New phase (e.g., "decide")
            duration_ms: Time spent in from_phase in milliseconds
        """
        return None
