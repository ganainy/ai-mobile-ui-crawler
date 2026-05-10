"""Log viewer widget for mobile-crawler GUI."""

from datetime import datetime
from html import escape
import re
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
from PySide6.QtCore import Signal
from PySide6.QtGui import QTextCursor, QColor, QFont

from mobile_crawler.core.logging_service import LogLevel


class LogViewer(QWidget):
    """Widget for displaying real-time logs.

    Provides scrolling log display with level filtering, terminal-like
    rich text formatting, color-coded levels, and clear functionality.

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
        self._theme = {
            "bg": "#0b0f14",
            "border": "#263241",
            "text": "#d7dde5",
            "muted": "#7f8b98",
            "debug": "#8b949e",
            "info": "#d7dde5",
            "ok": "#7dd88f",
            "action": "#5cc8ff",
            "warning": "#f4bd50",
            "error": "#ff6b6b",
            "badge_bg": "#151d27",
            "stdout": "#73808e",
            "stderr": "#d68a58",
            "source": "#aab7c4",
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
        self.log_text.setAcceptRichText(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: {self._theme["bg"]};
                color: {self._theme["text"]};
                border: 1px solid {self._theme["border"]};
                border-radius: 6px;
                padding: 8px;
                selection-background-color: #24415f;
                selection-color: #ffffff;
            }}
            """
        )
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
            "DEBUG": QColor(139, 148, 158),      # Muted gray
            "INFO": QColor(215, 221, 229),       # Terminal foreground
            "WARNING": QColor(244, 189, 80),     # Amber
            "ERROR": QColor(255, 107, 107),      # Red
            "ACTION": QColor(92, 200, 255),      # Cyan-blue
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

        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        cursor.insertHtml(self._format_entry_html(level, timestamp, message))
        cursor.insertBlock()

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

            cursor.insertHtml(self._format_entry_html(level, timestamp, message))
            cursor.insertBlock()

        # Scroll to bottom after rebuild
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _format_entry_html(self, level: LogLevel, timestamp: str, message: str) -> str:
        """Build the rich HTML representation for one stored log entry."""
        display_message = re.sub(r"^\s*\[(stdout|stderr)\]\s*", "", message, flags=re.IGNORECASE)
        classification = self._classify_message(level, message)
        lines = display_message.splitlines() or [""]
        first_line = lines[0]
        continuation_lines = lines[1:]

        level_name = level.name
        level_color = classification["level_color"]
        text_color = classification["text_color"]
        badge_bg = classification["badge_bg"]
        source = classification["source"]

        timestamp_html = self._span(f"[{timestamp}]", self._theme["muted"])
        level_html = self._badge(level_name, level_color, badge_bg)
        source_html = f" {self._badge(source, classification['source_color'], badge_bg)}" if source else ""
        first_line_html = self._preserve_spaces(escape(first_line))

        blocks = [
            (
                "<div style=\"font-family: Consolas, 'Courier New', monospace; "
                "font-size: 9pt; line-height: 130%; margin: 0 0 2px 0; "
                f"color: {text_color}; white-space: pre-wrap;\">"
                f"{timestamp_html} {level_html}{source_html} "
                f"<span style=\"color: {text_color};\">{first_line_html}</span>"
                "</div>"
            )
        ]

        for line in continuation_lines:
            line_html = self._preserve_spaces(escape(line))
            blocks.append(
                "<div style=\"font-family: Consolas, 'Courier New', monospace; "
                "font-size: 9pt; line-height: 130%; margin: 0; white-space: pre-wrap; "
                f"color: {classification['continuation_color']};\">"
                f"<span style=\"color: {self._theme['muted']};\">          | </span>{line_html}"
                "</div>"
            )

        return "".join(blocks)

    def _classify_message(self, level: LogLevel, message: str) -> dict:
        """Classify a log entry for display styling only."""
        lower = message.lower()
        stripped = message.strip()
        source = ""
        source_color = self._theme["source"]
        text_color = self._theme["info"]
        level_color = self._qcolor_to_hex(self._get_level_color(level.name))
        badge_bg = self._theme["badge_bg"]
        continuation_color = "#a5b0bd"

        if stripped.startswith("[stdout]"):
            source = "STDOUT"
            source_color = self._theme["stdout"]
            text_color = self._theme["debug"]
            continuation_color = self._theme["muted"]
        elif stripped.startswith("[stderr]"):
            source = "STDERR"
            source_color = self._theme["stderr"]
            text_color = "#c79a80"
            continuation_color = "#aa8370"

        role_match = re.search(r"\b(Manager|Executor|AppOpener) response:", message)
        if role_match:
            source = role_match.group(1).upper()
            source_color = self._theme["action"]

        if re.match(r"^\s*(step\s+\d+|\[\w+\]\s*step\s+\d+)", lower):
            source = source or "STEP"
            source_color = self._theme["action"]

        if self._looks_like_action(message):
            source = source or "ACTION"
            text_color = self._theme["action"]
            level_color = self._theme["action"]

        if level == LogLevel.DEBUG:
            text_color = text_color if source else self._theme["debug"]
            continuation_color = self._theme["muted"]
        elif level == LogLevel.ACTION:
            text_color = self._theme["action"]
            level_color = self._theme["action"]
            source = source or "ACTION"
            source_color = self._theme["action"]
        elif level == LogLevel.WARNING:
            text_color = self._theme["warning"]
            level_color = self._theme["warning"]
            source = source or "WARN"
            source_color = self._theme["warning"]
        elif level == LogLevel.ERROR:
            text_color = self._theme["error"]
            level_color = self._theme["error"]
            source = source or "ERROR"
            source_color = self._theme["error"]

        if self._has_error_words(lower):
            text_color = self._theme["error"]
            source = source or "ERROR"
            source_color = self._theme["error"]
        elif self._has_warning_words(lower):
            text_color = self._theme["warning"]
            source = source or "WARN"
            source_color = self._theme["warning"]
        elif self._has_success_words(lower):
            text_color = self._theme["ok"]
            source = source or "OK"
            source_color = self._theme["ok"]

        return {
            "source": source,
            "source_color": source_color,
            "text_color": text_color,
            "level_color": level_color,
            "badge_bg": badge_bg,
            "continuation_color": continuation_color,
        }

    def _looks_like_action(self, message: str) -> bool:
        stripped = message.strip()
        if "action" in stripped.lower() and ("{" in stripped or ":" in stripped):
            return True
        if not (stripped.startswith("{") and stripped.endswith("}")):
            return False
        return any(token in stripped.lower() for token in ("tap", "type", "swipe", "action", "coordinate"))

    def _has_success_words(self, lower_message: str) -> bool:
        return any(word in lower_message for word in ("success", "succeeded", "finished", "completed", " ok", "passed"))

    def _has_warning_words(self, lower_message: str) -> bool:
        return any(word in lower_message for word in ("warning", "warn:", "retry", "timeout", "slow"))

    def _has_error_words(self, lower_message: str) -> bool:
        return any(word in lower_message for word in ("error", "failed", "failure", "exception", "traceback", "crash"))

    def _badge(self, text: str, color: str, background: str) -> str:
        return (
            f"<span style=\"color: {color}; background-color: {background}; "
            f"font-weight: 700;\">[{escape(text)}]</span>"
        )

    def _span(self, text: str, color: str) -> str:
        return f"<span style=\"color: {color};\">{escape(text)}</span>"

    def _preserve_spaces(self, text: str) -> str:
        return text.replace(" ", "&nbsp;").replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;")

    def _qcolor_to_hex(self, color: QColor) -> str:
        return f"#{color.red():02x}{color.green():02x}{color.blue():02x}"

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
