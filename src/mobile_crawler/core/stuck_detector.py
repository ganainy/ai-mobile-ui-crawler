"""Stuck detector for identifying when crawler is stuck on the same screen."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class StuckDetector:
    """Detects when the crawler is stuck on the same screen consecutively."""

    def __init__(self, threshold: int = 3):
        """Initialize the stuck detector.

        Args:
            threshold: Number of consecutive visits before considering stuck (default: 3)
        """
        self._threshold = threshold
        self._screen_visit_counts: dict[int, int] = {}  # screen_id -> consecutive count
        self._current_screen_id: Optional[int] = None
        self._is_stuck: bool = False
        self._stuck_reason: Optional[str] = None
        self._stuck_recovery_success_count: int = 0

    def record_screen_visit(self, screen_id: int) -> None:
        """Record a screen visit and update stuck detection.

        Args:
            screen_id: ID of the screen being visited
        """
        # If this is a new screen, reset the previous screen's count
        if self._current_screen_id is not None and self._current_screen_id != screen_id:
            self._screen_visit_counts[self._current_screen_id] = 0

        # Update current screen
        self._current_screen_id = screen_id

        # Increment consecutive visit count for this screen
        self._screen_visit_counts[screen_id] = self._screen_visit_counts.get(screen_id, 0) + 1

        # Check if we're stuck
        consecutive_visits = self._screen_visit_counts[screen_id]
        if consecutive_visits > self._threshold:
            self._is_stuck = True
            self._stuck_reason = (
                f"Stuck on screen {screen_id} after {consecutive_visits} consecutive visits"
            )
            logger.warning(self._stuck_reason)
        else:
            self._is_stuck = False
            self._stuck_reason = None

    def record_recovery(self, success: bool = True) -> None:
        """Record a recovery attempt from a stuck state.

        Args:
            success: Whether the recovery was successful
        """
        if success:
            self._stuck_recovery_success_count += 1
            logger.info(f"Stuck recovery successful. Total successes: {self._stuck_recovery_success_count}")

        # Reset stuck state after recovery attempt
        if self._current_screen_id is not None:
            self._screen_visit_counts[self._current_screen_id] = 0
        self._is_stuck = False
        self._stuck_reason = None

    def reset(self) -> None:
        """Reset the stuck detector state."""
        self._screen_visit_counts.clear()
        self._current_screen_id = None
        self._is_stuck = False
        self._stuck_reason = None
        self._stuck_recovery_success_count = 0

    @property
    def is_stuck(self) -> bool:
        """Check if the crawler is currently stuck.

        Returns:
            True if stuck, False otherwise
        """
        return self._is_stuck

    @property
    def stuck_reason(self) -> Optional[str]:
        """Get the reason for being stuck.

        Returns:
            Stuck reason string or None if not stuck
        """
        return self._stuck_reason

    @property
    def stuck_recovery_success_count(self) -> int:
        """Get the number of successful stuck recoveries.

        Returns:
            Number of successful recovery attempts
        """
        return self._stuck_recovery_success_count

    @property
    def consecutive_visits(self) -> int:
        """Get the number of consecutive visits to the current screen.

        Returns:
            Consecutive visit count
        """
        if self._current_screen_id is None:
            return 0
        return self._screen_visit_counts.get(self._current_screen_id, 0)

    @property
    def current_screen_id(self) -> Optional[int]:
        """Get the current screen ID.

        Returns:
            Current screen ID or None
        """
        return self._current_screen_id

    def get_screen_visit_count(self, screen_id: int) -> int:
        """Get the consecutive visit count for a specific screen.

        Args:
            screen_id: Screen ID to query

        Returns:
            Consecutive visit count for the screen
        """
        return self._screen_visit_counts.get(screen_id, 0)
