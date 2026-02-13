"""Tests for LogViewer widget."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from mobile_crawler.ui.widgets.log_viewer import LogViewer
from mobile_crawler.core.logging_service import LogLevel


def _create_log_viewer():
    """Helper function to create a LogViewer instance."""
    return LogViewer()


@pytest.fixture
def log_viewer(qtbot):
    """Create LogViewer instance for tests.
    
    Uses qtbot.addWidget to ensure proper cleanup after each test.
    """
    viewer = _create_log_viewer()
    qtbot.addWidget(viewer)
    return viewer


class TestLogViewerInit:
    """Tests for LogViewer initialization."""

    def test_initialization(self, log_viewer):
        """Test that LogViewer initializes correctly."""
        assert log_viewer.level_filter is not None
        assert log_viewer.log_text is not None
        assert log_viewer.clear_button is not None
        assert log_viewer.get_level_filter() == LogLevel.DEBUG


class TestLevelFilter:
    """Tests for level filter functionality."""

    def test_default_level_is_debug(self, log_viewer):
        """Test that default level filter is DEBUG."""
        assert log_viewer.get_level_filter() == LogLevel.DEBUG

    def test_level_filter_changes(self, log_viewer):
        """Test that level filter changes when dropdown changes."""
        log_viewer.level_filter.setCurrentText("INFO")
        assert log_viewer.get_level_filter() == LogLevel.INFO

    def test_set_level_filter(self, log_viewer):
        """Test that set_level_filter() updates filter."""
        log_viewer.set_level_filter(LogLevel.WARNING)
        assert log_viewer.get_level_filter() == LogLevel.WARNING
        assert log_viewer.level_filter.currentText() == "WARNING"

    def test_all_levels_map_correctly(self, log_viewer):
        """Test that all log levels map correctly."""
        level_map = {
            LogLevel.DEBUG: "DEBUG",
            LogLevel.INFO: "INFO",
            LogLevel.WARNING: "WARNING",
            LogLevel.ERROR: "ERROR",
            LogLevel.ACTION: "ACTION",
        }
        
        for level, text in level_map.items():
            log_viewer.set_level_filter(level)
            assert log_viewer.level_filter.currentText() == text
            assert log_viewer.get_level_filter() == level


class TestLogDisplay:
    """Tests for log message display."""

    def test_append_log_displays_message(self, log_viewer):
        """Test that append_log() displays message."""
        log_viewer.append_log(LogLevel.INFO, "Test message")
        text = log_viewer.log_text.toPlainText()
        assert "[INFO] Test message" in text

    def test_append_log_with_newline(self, log_viewer):
        """Test that append_log() adds newline."""
        log_viewer.append_log(LogLevel.INFO, "Message 1")
        log_viewer.append_log(LogLevel.INFO, "Message 2")
        text = log_viewer.log_text.toPlainText()
        assert text.endswith("Message 2\n")

    def test_append_log_filters_by_level(self, log_viewer):
        """Test that append_log() filters by level."""
        log_viewer.set_level_filter(LogLevel.WARNING)
        
        log_viewer.append_log(LogLevel.DEBUG, "Debug message")
        log_viewer.append_log(LogLevel.INFO, "Info message")
        log_viewer.append_log(LogLevel.WARNING, "Warning message")
        
        text = log_viewer.log_text.toPlainText()
        assert "[DEBUG] Debug message" not in text
        assert "[INFO] Info message" not in text
        assert "[WARNING] Warning message" in text

    def test_append_log_allows_equal_level(self, log_viewer):
        """Test that append_log() allows equal level."""
        log_viewer.set_level_filter(LogLevel.WARNING)
        log_viewer.append_log(LogLevel.WARNING, "Warning message")
        text = log_viewer.log_text.toPlainText()
        assert "[WARNING] Warning message" in text

    def test_append_log_allows_higher_level(self):
        """Test that append_log() allows higher level."""
        viewer = _create_log_viewer()
        viewer.set_level_filter(LogLevel.WARNING)
        viewer.append_log(LogLevel.ERROR, "Error message")
        text = viewer.log_text.toPlainText()
        assert "[ERROR] Error message" in text


class TestLogColors:
    """Tests for log level colors."""

    def test_debug_color(self, log_viewer):
        """Test that DEBUG level has gray color."""
        color = log_viewer._get_level_color("DEBUG")
        # Gray should have equal RGB values
        assert color.red() == color.green() == color.blue()

    def test_info_color(self, log_viewer):
        """Test that INFO level has green color."""
        color = log_viewer._get_level_color("INFO")
        assert color.red() == 0
        assert color.green() > 0
        assert color.blue() == 0

    def test_warning_color(self, log_viewer):
        """Test that WARNING level has orange color."""
        color = log_viewer._get_level_color("WARNING")
        assert color.red() == 255
        assert color.green() == 165
        assert color.blue() == 0

    def test_error_color(self, log_viewer):
        """Test that ERROR level has red color."""
        color = log_viewer._get_level_color("ERROR")
        assert color.red() > 0
        assert color.green() == 0
        assert color.blue() == 0

    def test_action_color(self, log_viewer):
        """Test that ACTION level has blue color."""
        color = log_viewer._get_level_color("ACTION")
        assert color.red() == 0
        assert color.green() > 0
        assert color.blue() > 0


class TestClearLogs:
    """Tests for clear logs functionality."""

    def test_clear_button_clears_text(self, log_viewer):
        """Test that clear button clears log text."""
        log_viewer.append_log(LogLevel.INFO, "Test message")
        assert log_viewer.log_text.toPlainText() != ""
        
        log_viewer.clear_button.click()
        assert log_viewer.log_text.toPlainText() == ""

    def test_clear_logs_method_clears_text(self, log_viewer):
        """Test that clear_logs() method clears log text."""
        log_viewer.append_log(LogLevel.INFO, "Test message")
        assert log_viewer.log_text.toPlainText() != ""
        
        log_viewer.clear_logs()
        assert log_viewer.log_text.toPlainText() == ""

    def test_clear_emits_signal(self, log_viewer):
        """Test that clear emits logs_cleared signal."""
        signal_emitted = []

        def capture_signal():
            signal_emitted.append(True)

        log_viewer.logs_cleared.connect(capture_signal)
        log_viewer.clear_button.click()

        assert len(signal_emitted) == 1


class TestUIComponents:
    """Tests for UI components."""

    def test_level_filter_exists(self, log_viewer):
        """Test that level filter exists."""
        assert log_viewer.level_filter is not None
        assert log_viewer.level_filter.count() == 5

    def test_level_filter_options(self, log_viewer):
        """Test that level filter has correct options."""
        options = [log_viewer.level_filter.itemText(i) for i in range(log_viewer.level_filter.count())]
        assert "DEBUG" in options
        assert "INFO" in options
        assert "WARNING" in options
        assert "ERROR" in options
        assert "ACTION" in options

    def test_clear_button_exists(self, log_viewer):
        """Test that clear button exists."""
        assert log_viewer.clear_button is not None
        assert log_viewer.clear_button.text() == "Clear"

    def test_log_text_exists(self, log_viewer):
        """Test that log text area exists."""
        assert log_viewer.log_text is not None
        assert log_viewer.log_text.isReadOnly()

    def test_log_text_has_minimum_height(self, log_viewer):
        """Test that log text has minimum height."""
        assert log_viewer.log_text.minimumHeight() >= 300


class TestAutoScroll:
    """Tests for auto-scroll functionality."""

    def test_auto_scroll_to_bottom(self, log_viewer):
        """Test that logs auto-scroll to bottom."""
        # Add enough messages to trigger scrollbar
        for i in range(10):
            log_viewer.append_log(LogLevel.INFO, f"Message {i}")
        
        # Check that scrollbar is at maximum
        scrollbar = log_viewer.log_text.verticalScrollBar()
        assert scrollbar.value() == scrollbar.maximum()
