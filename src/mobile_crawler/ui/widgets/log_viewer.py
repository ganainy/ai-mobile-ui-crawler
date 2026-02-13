"""Log viewer widget for mobile-crawler GUI."""

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
    """

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

    def _on_clear_clicked(self):
        """Handle clear button click."""
        self.log_text.clear()
        self.logs_cleared.emit()

    def append_log(self, level: LogLevel, message: str):
        """Append a log message to the viewer.
        
        Args:
            level: Log level
            message: Log message
        """
        # Check if message should be displayed based on level filter
        # Use numeric ordering from _level_order
        level_order = self._level_order.get(level, 0)
        min_order = self._level_order.get(self._min_level, 0)
        
        if level_order < min_order:
            return

        # Get level name and color
        level_name = level.name
        color = self._get_level_color(level_name)

        # Format message with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{level_name}] {message}"

        # Move cursor to end and append
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Insert with color
        self.log_text.setTextColor(color)
        cursor.insertText(formatted_message + "\n")

        # Auto-scroll to bottom
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
        self._min_level = level

    def get_level_filter(self) -> LogLevel:
        """Get the current minimum log level filter.
        
        Returns:
            Current minimum log level
        """
        return self._min_level

    def clear_logs(self):
        """Clear all logs from the viewer."""
        self.log_text.clear()
