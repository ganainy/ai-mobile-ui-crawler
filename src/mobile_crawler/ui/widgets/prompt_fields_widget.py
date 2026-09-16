"""Copyable key/value display for prompt payloads.

This replaces the earlier `QTreeWidget`-based prompt view. Tree items elide
long values, scroll a whole item at a time (so a single tall row jumps
straight from top to bottom), and offer no way to grab the exact text. Here
every prompt field gets its own read-only text box — it wraps instead of
eliding, sizes itself to its own text, and carries a copy button. The bulkiest
field (the prompt text) additionally soaks up the panel's spare height so the
prompt, not a gap, fills the view.
"""

import json
from typing import Any

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

MAX_VALUE_HEIGHT = 1200
_BULK_MIN_CHARS = 200
_BULK_MIN_MULTILINE_CHARS = 60
_ICON_COLOR = "#cfcfcf"
_ICON_SIZE = 16


def parse_payload(data: Any) -> Any:
    """Parse a prompt payload into a dict/list, tolerating fences and double encoding."""
    if isinstance(data, (dict, list)):
        return data

    if isinstance(data, str):
        cleaned = data.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
            return parsed
        except (json.JSONDecodeError, TypeError):
            return data

    return data


def _format_value(value: Any) -> str:
    """Render a field value as text; containers become pretty-printed JSON."""
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def _bulk_score(text: str) -> int:
    """Rank a value by how much room it deserves; 0 means "hug my content"."""
    if len(text) >= _BULK_MIN_CHARS:
        return len(text)
    if "\n" in text and len(text) >= _BULK_MIN_MULTILINE_CHARS:
        return len(text)
    return 0


def _copy_icon() -> QIcon:
    """Paint a small 'copy' glyph (two stacked sheets)."""
    pixmap = QPixmap(_ICON_SIZE * 2, _ICON_SIZE * 2)
    pixmap.setDevicePixelRatio(2.0)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(_ICON_COLOR))
    pen.setWidthF(1.3)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(2.0, 2.0, 7.5, 9.0, 1.5, 1.5)
    painter.drawRoundedRect(5.5, 5.5, 7.5, 9.0, 1.5, 1.5)
    painter.end()
    return QIcon(pixmap)


def _check_icon() -> QIcon:
    """Paint a small checkmark, shown briefly after a successful copy."""
    pixmap = QPixmap(_ICON_SIZE * 2, _ICON_SIZE * 2)
    pixmap.setDevicePixelRatio(2.0)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#6fcf6f"))
    pen.setWidthF(1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawLine(3, 8, 6, 11)
    painter.drawLine(6, 11, 13, 4)
    painter.end()
    return QIcon(pixmap)


class PromptField(QWidget):
    """A single prompt key with its full value in a scrollable, copyable box."""

    def __init__(self, key: str, value_text: str, expanding: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self._value_text = value_text
        self._expanding = expanding

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        header = QHBoxLayout()
        header.setSpacing(4)

        key_label = QLabel(key)
        key_label.setStyleSheet("color: #9cdcfe; font-family: monospace; font-weight: bold;")
        key_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        key_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        header.addWidget(key_label)
        header.addStretch()

        self.copy_button = QToolButton()
        self.copy_button.setAutoRaise(True)
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.setIcon(_copy_icon())
        self.copy_button.setIconSize(QSize(_ICON_SIZE, _ICON_SIZE))
        self.copy_button.setToolTip("Copy value")
        self.copy_button.clicked.connect(self._copy_to_clipboard)
        header.addWidget(self.copy_button)

        layout.addLayout(header)

        self.value_edit = QPlainTextEdit()
        self.value_edit.setPlainText(value_text)
        self.value_edit.setReadOnly(True)
        self.value_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.value_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.value_edit.document().setDocumentMargin(6)
        self.value_edit.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #232323;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                selection-background-color: #3d5a80;
            }
            """
        )
        vertical_policy = (
            QSizePolicy.Policy.Expanding if expanding else QSizePolicy.Policy.Preferred
        )
        self.setSizePolicy(QSizePolicy.Policy.Preferred, vertical_policy)
        self.value_edit.setSizePolicy(QSizePolicy.Policy.Preferred, vertical_policy)
        layout.addWidget(self.value_edit)

        self._applied_min_height = 0
        self._apply_min_height()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_min_height()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_min_height()

    def _apply_min_height(self) -> None:
        """Size the value box to exactly fit its text.

        Measured with QFontMetrics rather than the document size: a collapsed
        section lays its children out at a placeholder width, and
        QPlainTextDocumentLayout does not track the wrap width those children
        actually end up with. Side-effect fields keep this height; the bulk
        field keeps it as a floor so it can absorb the panel's spare height
        instead of clipping its text behind a scrollbar. MAX_VALUE_HEIGHT is a
        sanity ceiling for absurd payloads.
        """
        metrics = self.value_edit.fontMetrics()
        margins = 2 * self.value_edit.document().documentMargin() + 2 * self.value_edit.frameWidth()
        available = max(self.width() - margins - 18, 80)
        text_rect = metrics.boundingRect(
            0, 0, available, 100000, Qt.TextFlag.TextWordWrap, self._value_text
        )
        needed = text_rect.height() + margins + 8
        target = int(min(needed, MAX_VALUE_HEIGHT))
        if target != self._applied_min_height:
            self._applied_min_height = target
            if self._expanding:
                # Free to soak up the panel's spare height...
                self.value_edit.setMaximumHeight(16777215)
                self.value_edit.setMinimumHeight(target)
            else:
                # ...while one-liners stay one line tall.
                self.value_edit.setFixedHeight(target)

    def _copy_to_clipboard(self) -> None:
        QApplication.clipboard().setText(self._value_text)
        self.copy_button.setIcon(_check_icon())
        self.copy_button.setToolTip("Copied!")
        QTimer.singleShot(1200, self._reset_copy_button)

    def _reset_copy_button(self) -> None:
        self.copy_button.setIcon(_copy_icon())
        self.copy_button.setToolTip("Copy value")


class PromptFieldsWidget(QWidget):
    """Vertical list of copyable prompt fields, one row per top-level key."""

    def __init__(self, data: Any, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)
        self._build(data)

    def _build(self, data: Any) -> None:
        parsed = parse_payload(data)

        if isinstance(parsed, dict) and parsed:
            fields = [(str(key), value) for key, value in parsed.items()]
        elif parsed is None or parsed == "" or parsed == {} or parsed == []:
            empty_label = QLabel("(empty payload)")
            empty_label.setStyleSheet("color: #666; font-style: italic;")
            self._layout.addWidget(empty_label)
            return
        else:
            fields = [("value", parsed)]

        # Spare height goes to a single bulk field (the prompt text) so it
        # grows to fill the panel; one-liners such as the screenshot
        # placeholder keep exactly the room their line needs.
        scores = [_bulk_score(_format_value(value)) for _, value in fields]
        bulk_index = scores.index(max(scores)) if max(scores) > 0 else -1
        for index, (key, value) in enumerate(fields):
            value_text = _format_value(value)
            is_bulk = index == bulk_index
            self._layout.addWidget(PromptField(key, value_text, expanding=is_bulk), 1 if is_bulk else 0)
