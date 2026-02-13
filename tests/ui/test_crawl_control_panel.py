"""Tests for CrawlControlPanel widget."""

import pytest
from unittest.mock import Mock

from mobile_crawler.ui.widgets.crawl_control_panel import CrawlControlPanel
from mobile_crawler.core.crawl_controller import CrawlController
from mobile_crawler.core.crawl_state_machine import CrawlState


def _create_panel():
    """Helper function to create a CrawlControlPanel instance."""
    mock_controller = Mock(spec=CrawlController)
    mock_controller.get_state = Mock(return_value=CrawlState.UNINITIALIZED)
    return CrawlControlPanel(crawl_controller=mock_controller)


class TestCrawlControlPanelInit:
    """Tests for CrawlControlPanel initialization."""

    def test_initialization(self, qtbot):
        """Test that CrawlControlPanel initializes correctly."""
        panel = _create_panel()
        qtbot.addWidget(panel)

        assert panel.crawl_controller is not None
        assert panel._validation_passed is False


class TestButtonStates:
    """Tests for button state management."""

    def test_start_button_disabled_initially(self, qtbot):
        """Test that start button is disabled initially."""
        panel = _create_panel()
        qtbot.addWidget(panel)

        assert panel.start_button.isEnabled() is False

    def test_pause_button_disabled_initially(self, qtbot):
        """Test that pause button is disabled initially."""
        panel = _create_panel()
        qtbot.addWidget(panel)

        assert panel.pause_button.isEnabled() is False

    def test_resume_button_hidden_initially(self, qtbot):
        """Test that resume button is hidden initially."""
        panel = _create_panel()
        qtbot.addWidget(panel)

        assert panel.resume_button.isVisible() is False

    def test_stop_button_disabled_initially(self, qtbot):
        """Test that stop button is disabled initially."""
        panel = _create_panel()
        qtbot.addWidget(panel)

        assert panel.stop_button.isEnabled() is False


class TestStateUpdates:
    """Tests for state update functionality."""

    def test_uninitialized_state(self, qtbot):
        """Test button states for UNINITIALIZED state."""
        panel = _create_panel()
        qtbot.addWidget(panel)
        panel._validation_passed = True
        panel.update_state(CrawlState.UNINITIALIZED)

        assert panel.start_button.isEnabled() is True
        assert panel.pause_button.isEnabled() is False
        assert panel.resume_button.isVisible() is False
        assert panel.stop_button.isEnabled() is False

    def test_initializing_state(self, qtbot):
        """Test button states for INITIALIZING state."""
        panel = _create_panel()
        qtbot.addWidget(panel)
        panel.update_state(CrawlState.INITIALIZING)

        assert panel.start_button.isEnabled() is False
        assert panel.pause_button.isEnabled() is False
        assert panel.resume_button.isVisible() is False
        assert panel.stop_button.isEnabled() is True

    def test_running_state(self, qtbot):
        """Test button states for RUNNING state."""
        panel = _create_panel()
        qtbot.addWidget(panel)
        panel.update_state(CrawlState.RUNNING)

        assert panel.start_button.isEnabled() is False
        assert panel.pause_button.isEnabled() is True
        assert panel.resume_button.isVisible() is False
        assert panel.stop_button.isEnabled() is True

    def test_paused_state(self, qtbot):
        """Test button states for PAUSED_MANUAL state."""
        panel = _create_panel()
        qtbot.addWidget(panel)
        panel.update_state(CrawlState.PAUSED_MANUAL)

        assert panel.start_button.isEnabled() is False
        assert panel.pause_button.isVisible() is False
        assert panel.resume_button.isEnabled() is True
        # Note: isVisible() depends on parent widget being shown
        # In unit tests without showing widget, we just check it's enabled
        assert panel.stop_button.isEnabled() is True

    def test_stopping_state(self, qtbot):
        """Test button states for STOPPING state."""
        panel = _create_panel()
        qtbot.addWidget(panel)
        panel.update_state(CrawlState.STOPPING)

        assert panel.start_button.isEnabled() is False
        assert panel.pause_button.isEnabled() is False
        assert panel.resume_button.isVisible() is False
        assert panel.stop_button.isEnabled() is False

    def test_stopped_state(self, qtbot):
        """Test button states for STOPPED state."""
        panel = _create_panel()
        qtbot.addWidget(panel)
        panel._validation_passed = True
        panel.update_state(CrawlState.STOPPED)

        assert panel.start_button.isEnabled() is True
        assert panel.pause_button.isEnabled() is False
        assert panel.resume_button.isVisible() is False
        assert panel.stop_button.isEnabled() is False

    def test_error_state(self, qtbot):
        """Test button states for ERROR state."""
        panel = _create_panel()
        qtbot.addWidget(panel)
        panel._validation_passed = True
        panel.update_state(CrawlState.ERROR)

        assert panel.start_button.isEnabled() is True
        assert panel.pause_button.isEnabled() is False
        assert panel.resume_button.isVisible() is False
        assert panel.stop_button.isEnabled() is False


class TestValidationPassed:
    """Tests for validation passed functionality."""

    def test_validation_passed_enables_start(self, qtbot):
        """Test that passing validation enables start button."""
        panel = _create_panel()
        qtbot.addWidget(panel)
        panel.set_validation_passed(True)

        assert panel.start_button.isEnabled() is True

    def test_validation_failed_disables_start(self, qtbot):
        """Test that failing validation disables start button."""
        panel = _create_panel()
        qtbot.addWidget(panel)
        panel.set_validation_passed(False)

        assert panel.start_button.isEnabled() is False

    def test_validation_passed_during_run(self, qtbot):
        """Test that validation doesn't affect start button during run."""
        panel = _create_panel()
        panel.crawl_controller.get_state = Mock(return_value=CrawlState.RUNNING)
        qtbot.addWidget(panel)
        panel.set_validation_passed(True)

        assert panel.start_button.isEnabled() is False


class TestUIComponents:
    """Tests for UI components."""

    def test_start_button_exists(self, qtbot):
        """Test that start button exists."""
        panel = _create_panel()
        qtbot.addWidget(panel)

        assert panel.start_button is not None
        assert panel.start_button.text() == "Start Crawl"

    def test_pause_button_exists(self, qtbot):
        """Test that pause button exists."""
        panel = _create_panel()
        qtbot.addWidget(panel)

        assert panel.pause_button is not None
        assert panel.pause_button.text() == "Pause"

    def test_resume_button_exists(self, qtbot):
        """Test that resume button exists."""
        panel = _create_panel()
        qtbot.addWidget(panel)

        assert panel.resume_button is not None
        assert panel.resume_button.text() == "Resume"

    def test_stop_button_exists(self, qtbot):
        """Test that stop button exists."""
        panel = _create_panel()
        qtbot.addWidget(panel)

        assert panel.stop_button is not None
        assert panel.stop_button.text() == "Stop"

    def test_status_label_exists(self, qtbot):
        """Test that status label exists."""
        panel = _create_panel()
        qtbot.addWidget(panel)

        assert panel.status_label is not None


class TestStatusColors:
    """Tests for status label colors."""

    def test_ready_status_color(self, qtbot):
        """Test that ready status has gray color."""
        panel = _create_panel()
        qtbot.addWidget(panel)
        panel.update_state(CrawlState.UNINITIALIZED)

        assert "gray" in panel.status_label.styleSheet()

    def test_running_status_color(self, qtbot):
        """Test that running status has green color."""
        panel = _create_panel()
        qtbot.addWidget(panel)
        panel.update_state(CrawlState.RUNNING)

        assert "green" in panel.status_label.styleSheet()

    def test_paused_status_color(self, qtbot):
        """Test that paused status has blue color."""
        panel = _create_panel()
        qtbot.addWidget(panel)
        panel.update_state(CrawlState.PAUSED_MANUAL)

        assert "blue" in panel.status_label.styleSheet()

    def test_error_status_color(self, qtbot):
        """Test that error status has red color."""
        panel = _create_panel()
        qtbot.addWidget(panel)
        panel.update_state(CrawlState.ERROR)

        assert "red" in panel.status_label.styleSheet()
