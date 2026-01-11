"""Protocol for crawler event listeners."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

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
    def on_ai_request_sent(self, run_id: int, step_number: int, request_data: Dict[str, Any]) -> None:
        """Called when an AI request is sent."""
        pass

    @abstractmethod
    def on_ai_response_received(self, run_id: int, step_number: int, response_data: Dict[str, Any]) -> None:
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
    def on_crawl_completed(self, run_id: int, total_steps: int, total_duration_ms: float, reason: str) -> None:
        """Called when a crawl completes."""
        pass

    @abstractmethod
    def on_error(self, run_id: int, step_number: Optional[int], error: Exception) -> None:
        """Called when an error occurs."""
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
        """Called when a screen is processed by the screen tracker.
        
        Args:
            run_id: Current run ID
            step_number: Current step number
            screen_id: ID of the processed screen
            is_new: True if this screen was just discovered
            visit_count: Number of times this screen has been visited in this run
            total_screens: Total unique screens discovered in this run
        """
        pass