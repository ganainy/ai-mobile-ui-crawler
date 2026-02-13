"""Tests for StuckDetector."""

import pytest

from mobile_crawler.core.stuck_detector import StuckDetector


class TestStuckDetector:
    """Tests for StuckDetector."""

    def test_init_default_threshold(self):
        """Test initialization with default threshold."""
        detector = StuckDetector()
        assert detector._threshold == 3
        assert detector._is_stuck is False
        assert detector._stuck_reason is None
        assert detector._stuck_recovery_success_count == 0
        assert detector._current_screen_id is None
        assert detector._screen_visit_counts == {}

    def test_init_custom_threshold(self):
        """Test initialization with custom threshold."""
        detector = StuckDetector(threshold=5)
        assert detector._threshold == 5

    def test_record_first_screen_visit(self):
        """Test recording first screen visit."""
        detector = StuckDetector()
        detector.record_screen_visit(1)

        assert detector.current_screen_id == 1
        assert detector.consecutive_visits == 1
        assert detector.is_stuck is False
        assert detector.stuck_reason is None

    def test_record_consecutive_same_screen(self):
        """Test recording consecutive visits to same screen."""
        detector = StuckDetector(threshold=3)

        detector.record_screen_visit(1)
        assert detector.consecutive_visits == 1
        assert detector.is_stuck is False

        detector.record_screen_visit(1)
        assert detector.consecutive_visits == 2
        assert detector.is_stuck is False

        detector.record_screen_visit(1)
        assert detector.consecutive_visits == 3
        assert detector.is_stuck is False

        detector.record_screen_visit(1)
        assert detector.consecutive_visits == 4
        assert detector.is_stuck is True
        assert "Stuck on screen 1 after 4 consecutive visits" in detector.stuck_reason

    def test_record_different_screens(self):
        """Test recording visits to different screens."""
        detector = StuckDetector()

        detector.record_screen_visit(1)
        assert detector.consecutive_visits == 1
        assert detector.get_screen_visit_count(1) == 1

        detector.record_screen_visit(2)
        assert detector.current_screen_id == 2
        assert detector.consecutive_visits == 1
        assert detector.get_screen_visit_count(1) == 0  # Reset when screen changes
        assert detector.get_screen_visit_count(2) == 1

    def test_screen_change_resets_previous_count(self):
        """Test that changing screens resets previous screen's count."""
        detector = StuckDetector(threshold=2)

        detector.record_screen_visit(1)
        detector.record_screen_visit(1)

        assert detector.get_screen_visit_count(1) == 2

        detector.record_screen_visit(2)

        # Screen 1's count should be reset
        assert detector.get_screen_visit_count(1) == 0
        assert detector.get_screen_visit_count(2) == 1

    def test_threshold_exactly(self):
        """Test stuck detection when threshold is exactly reached."""
        detector = StuckDetector(threshold=3)

        for _ in range(3):
            detector.record_screen_visit(1)

        assert detector.consecutive_visits == 3
        assert detector.is_stuck is False

        detector.record_screen_visit(1)
        assert detector.consecutive_visits == 4
        assert detector.is_stuck is True

    def test_threshold_greater_than_default(self):
        """Test stuck detection with higher threshold."""
        detector = StuckDetector(threshold=5)

        for _ in range(5):
            detector.record_screen_visit(1)

        assert detector.consecutive_visits == 5
        assert detector.is_stuck is False

        detector.record_screen_visit(1)
        assert detector.consecutive_visits == 6
        assert detector.is_stuck is True

    def test_threshold_less_than_default(self):
        """Test stuck detection with lower threshold."""
        detector = StuckDetector(threshold=2)

        detector.record_screen_visit(1)
        assert detector.consecutive_visits == 1
        assert detector.is_stuck is False

        detector.record_screen_visit(1)
        assert detector.consecutive_visits == 2
        assert detector.is_stuck is False

        detector.record_screen_visit(1)
        assert detector.consecutive_visits == 3
        assert detector.is_stuck is True

    def test_multiple_screens_tracking(self):
        """Test tracking multiple different screens."""
        detector = StuckDetector(threshold=2)

        # Visit screen 1 twice
        detector.record_screen_visit(1)
        detector.record_screen_visit(1)

        # Visit screen 2 once
        detector.record_screen_visit(2)

        # Visit screen 3 three times (should be stuck)
        detector.record_screen_visit(3)
        detector.record_screen_visit(3)
        detector.record_screen_visit(3)

        assert detector.get_screen_visit_count(1) == 0  # Reset when changed
        assert detector.get_screen_visit_count(2) == 0  # Reset when changed
        assert detector.get_screen_visit_count(3) == 3
        assert detector.current_screen_id == 3
        assert detector.is_stuck is True

    def test_record_recovery_success(self):
        """Test recording successful recovery."""
        detector = StuckDetector(threshold=2)

        # Get stuck
        detector.record_screen_visit(1)
        detector.record_screen_visit(1)
        detector.record_screen_visit(1)

        assert detector.is_stuck is True

        # Record recovery
        detector.record_recovery(success=True)

        assert detector.is_stuck is False
        assert detector.stuck_reason is None
        assert detector.stuck_recovery_success_count == 1
        assert detector.consecutive_visits == 0

    def test_record_recovery_failure(self):
        """Test recording failed recovery."""
        detector = StuckDetector(threshold=2)

        # Get stuck
        detector.record_screen_visit(1)
        detector.record_screen_visit(1)
        detector.record_screen_visit(1)

        assert detector.is_stuck is True

        # Record failed recovery
        detector.record_recovery(success=False)

        assert detector.is_stuck is False
        assert detector.stuck_reason is None
        assert detector.stuck_recovery_success_count == 0  # Not incremented on failure

    def test_multiple_recoveries(self):
        """Test multiple recovery attempts."""
        detector = StuckDetector(threshold=2)

        # First stuck and recovery
        detector.record_screen_visit(1)
        detector.record_screen_visit(1)
        detector.record_screen_visit(1)
        detector.record_recovery(success=True)

        assert detector.stuck_recovery_success_count == 1

        # Second stuck and recovery
        detector.record_screen_visit(2)
        detector.record_screen_visit(2)
        detector.record_screen_visit(2)
        detector.record_recovery(success=True)

        assert detector.stuck_recovery_success_count == 2

    def test_reset(self):
        """Test resetting detector state."""
        detector = StuckDetector(threshold=2)

        # Build up some state
        detector.record_screen_visit(1)
        detector.record_screen_visit(1)
        detector.record_screen_visit(1)
        detector.record_recovery(success=True)
        detector.record_screen_visit(2)

        # Reset
        detector.reset()

        assert detector._screen_visit_counts == {}
        assert detector._current_screen_id is None
        assert detector.is_stuck is False
        assert detector.stuck_reason is None
        assert detector.consecutive_visits == 0
        assert detector.stuck_recovery_success_count == 0

    def test_get_screen_visit_count_for_existing_screen(self):
        """Test getting visit count for existing screen."""
        detector = StuckDetector()
        detector.record_screen_visit(1)
        detector.record_screen_visit(1)

        assert detector.get_screen_visit_count(1) == 2

    def test_get_screen_visit_count_for_nonexistent_screen(self):
        """Test getting visit count for nonexistent screen."""
        detector = StuckDetector()

        assert detector.get_screen_visit_count(999) == 0

    def test_stuck_reason_format(self):
        """Test stuck reason message format."""
        detector = StuckDetector(threshold=3)

        for _ in range(4):
            detector.record_screen_visit(5)

        assert "Stuck on screen 5" in detector.stuck_reason
        assert "after 4 consecutive visits" in detector.stuck_reason

    def test_not_stuck_after_new_screen(self):
        """Test that stuck state clears when visiting new screen."""
        detector = StuckDetector(threshold=2)

        # Get stuck on screen 1
        detector.record_screen_visit(1)
        detector.record_screen_visit(1)
        detector.record_screen_visit(1)

        assert detector.is_stuck is True

        # Visit new screen
        detector.record_screen_visit(2)

        assert detector.is_stuck is False
        assert detector.stuck_reason is None
        assert detector.consecutive_visits == 1

    def test_consecutive_visits_property_before_any_visit(self):
        """Test consecutive_visits property before any visits."""
        detector = StuckDetector()

        assert detector.consecutive_visits == 0

    def test_current_screen_id_property_before_any_visit(self):
        """Test current_screen_id property before any visits."""
        detector = StuckDetector()

        assert detector.current_screen_id is None

    def test_alternating_screens_no_stuck(self):
        """Test that alternating screens doesn't trigger stuck state."""
        detector = StuckDetector(threshold=2)

        # Alternate between screens
        for i in range(10):
            screen_id = 1 if i % 2 == 0 else 2
            detector.record_screen_visit(screen_id)

        assert detector.is_stuck is False
        assert detector.stuck_reason is None

    def test_recovery_clears_current_screen_count(self):
        """Test that recovery clears current screen's visit count."""
        detector = StuckDetector(threshold=2)

        detector.record_screen_visit(1)
        detector.record_screen_visit(1)
        detector.record_screen_visit(1)

        assert detector.consecutive_visits == 3

        detector.record_recovery(success=True)

        assert detector.consecutive_visits == 0
        assert detector.get_screen_visit_count(1) == 0
