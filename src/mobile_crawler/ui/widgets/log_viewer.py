"""Log viewer widget for mobile-crawler GUI."""

from datetime import datetime
from typing import List, Tuple

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QComboBox,
    QPushButton,
    QLabel,
    QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor, QColor

from mobile_crawler.core.logging_service import LogLevel


class LogViewer(QWidget):
    """Widget for displaying real-time logs.

    Provides scrolling log display with level filtering,
    color-coded levels, and clear functionality.

    Log entries are stored in memory so that changing the level
    filter re-renders the visible set without losing history.
    """

    # Maximum entries kept in memory to avoid unbounded growth
    _MAX_ENTRIES = 5000

    # Signal emitted when logs are cleared
    logs_cleared = Signal()  # type: ignore

    def __init__(self, parent=None):
        """Initialize log viewer widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._min_level = LogLevel.DEBUG
        self._level_order = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.ACTION: 1,  # Same as INFO
        }
        # Stored log entries: list of (LogLevel, timestamp_str, message)
        self._entries: List[Tuple[LogLevel, str, str]] = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up user interface."""
        layout = QVBoxLayout()

        # Group box for log viewer
        log_group = QGroupBox("Logs")
        log_layout = QVBoxLayout()

        # Controls row (level filter + clear button)
        controls_layout = QHBoxLayout()

        # Level filter label
        level_label = QLabel("Level:")
        controls_layout.addWidget(level_label)

        # Level filter dropdown
        self.level_filter = QComboBox()
        self.level_filter.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "ACTION"])
        self.level_filter.setCurrentText("DEBUG")
        self.level_filter.currentTextChanged.connect(self._on_level_filter_changed)
        controls_layout.addWidget(self.level_filter)

        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._on_clear_clicked)
        controls_layout.addWidget(self.clear_button)

        controls_layout.addStretch()
        log_layout.addLayout(controls_layout)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(300)
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # Set the layout for this widget
        self.setLayout(layout)

    def _get_level_color(self, level: str) -> QColor:
        """Get color for a log level.

        Args:
            level: Log level string

        Returns:
            QColor for the log level
        """
        level_colors = {
            "DEBUG": QColor(150, 150, 150),      # Gray
            "INFO": QColor(0, 150, 0),          # Green
            "WARNING": QColor(255, 165, 0),      # Orange
            "ERROR": QColor(220, 0, 0),          # Red
            "ACTION": QColor(0, 100, 200),        # Blue
        }
        return level_colors.get(level, QColor(0, 0, 0))

    def _on_level_filter_changed(self, level_text: str):
        """Handle level filter dropdown change.

        Updates the minimum level and re-renders all stored entries
        so that the user immediately sees the effect of the filter.

        Args:
            level_text: Selected level text
        """
        level_map = {
            "DEBUG": LogLevel.DEBUG,
            "INFO": LogLevel.INFO,
            "WARNING": LogLevel.WARNING,
            "ERROR": LogLevel.ERROR,
            "ACTION": LogLevel.ACTION,
        }
        self._min_level = level_map.get(level_text, LogLevel.DEBUG)
        self._rebuild_display()

    def _on_clear_clicked(self):
        """Handle clear button click."""
        self._entries.clear()
        self.log_text.clear()
        self.logs_cleared.emit()

    def append_log(self, level: LogLevel, message: str):
        """Append a log message to the viewer.

        Stores the entry for re-filtering and appends to the display
        if it passes the current level filter.

        Args:
            level: Log level
            message: Log message
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Store the entry
        self._entries.append((level, timestamp, message))

        # Trim oldest entries if we exceed the maximum
        if len(self._entries) > self._MAX_ENTRIES:
            self._entries = self._entries[-self._MAX_ENTRIES:]
            # Rebuild needed because we dropped entries
            self._rebuild_display()
            return

        # Append to display only if it passes the filter
        self._append_to_display(level, timestamp, message)

    def _append_to_display(self, level: LogLevel, timestamp: str, message: str):
        """Append a single formatted entry to the text widget.

        Args:
            level: Log level
            timestamp: Pre-formatted timestamp string
            message: Log message text
        """
        level_order = self._level_order.get(level, 0)
        min_order = self._level_order.get(self._min_level, 0)

        if level_order < min_order:
            return

        level_name = level.name
        color = self._get_level_color(level_name)
        formatted_message = f"[{timestamp}] [{level_name}] {message}"

        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        self.log_text.setTextColor(color)
        cursor.insertText(formatted_message + "\n")

        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _rebuild_display(self):
        """Re-render all stored entries based on the current level filter.

        Called when the filter level changes or when old entries are trimmed.
        """
        self.log_text.clear()

        cursor = self.log_text.textCursor()
        min_order = self._level_order.get(self._min_level, 0)

        for level, timestamp, message in self._entries:
            level_order = self._level_order.get(level, 0)
            if level_order < min_order:
                continue

            level_name = level.name
            color = self._get_level_color(level_name)
            formatted_message = f"[{timestamp}] [{level_name}] {message}"

            self.log_text.setTextColor(color)
            cursor.insertText(formatted_message + "\n")

        # Scroll to bottom after rebuild
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def set_level_filter(self, level: LogLevel):
        """Set the minimum log level filter.

        Args:
            level: Minimum log level to display
        """
        level_map = {
            LogLevel.DEBUG: "DEBUG",
            LogLevel.INFO: "INFO",
            LogLevel.WARNING: "WARNING",
            LogLevel.ERROR: "ERROR",
            LogLevel.ACTION: "ACTION",
        }
        self.level_filter.setCurrentText(level_map.get(level, "DEBUG"))
        # Note: setCurrentText triggers currentTextChanged which calls
        # _on_level_filter_changed which calls _rebuild_display

    def get_level_filter(self) -> LogLevel:
        """Get the current minimum log level filter.

        Returns:
            Current minimum log level
        """
        return self._min_level

    def clear_logs(self):
        """Clear all logs from the viewer."""
        self._entries.clear()
        self.log_text.clear()
