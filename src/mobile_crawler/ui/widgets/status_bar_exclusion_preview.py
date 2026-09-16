"""Screen crop preview: a device screenshot with draggable top/bottom crop lines.

Lets the user calibrate top_bar_height (Status Bar Exclusion) and
bottom_bar_height (Bottom Bar Exclusion) visually against a real screenshot
instead of guessing pixel counts blind. See CONTEXT.md and ADR-0002.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

PREVIEW_WIDTH = 320
LINE_GRAB_MARGIN = 6

TOP_LINE_COLOR = QColor("#ff5050")
TOP_SHADE_COLOR = QColor(220, 50, 50, 90)
BOTTOM_LINE_COLOR = QColor("#5090ff")
BOTTOM_SHADE_COLOR = QColor(50, 100, 220, 90)


class StatusBarExclusionPreview(QWidget):
    """Displays a device screenshot with draggable top and bottom exclusion lines.

    The shaded band above the top line and below the bottom line are the
    regions that will be cropped (Status Bar Exclusion / Bottom Bar
    Exclusion). Dragging a line emits its *_changed signal with the value in
    real device pixels, already accounting for the preview's on-screen scale
    factor.
    """

    top_exclusion_changed = Signal(int)  # type: ignore
    bottom_exclusion_changed = Signal(int)  # type: ignore

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._device_height = 0
        self._scale = 1.0  # on-screen px per device px
        self._top_px = 0
        self._bottom_px = 0
        self._dragging_edge: str | None = None  # "top" | "bottom" | None
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._placeholder_text = "Connect a device to preview"
        self.setMinimumSize(PREVIEW_WIDTH, 80)
        self.setCursor(Qt.ArrowCursor)

    # -- public API -----------------------------------------------------

    def set_placeholder(self, text: str) -> None:
        """Show *text* instead of a screenshot (e.g. no device connected)."""
        self._pixmap = None
        self._placeholder_text = text
        self.setFixedHeight(80)
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def set_screenshot(self, image_bytes: bytes) -> None:
        """Load a freshly captured device screenshot into the preview."""
        pixmap = QPixmap()
        if not pixmap.loadFromData(image_bytes):
            self.set_placeholder("Couldn't decode screenshot")
            return

        self._device_height = pixmap.height()
        self._scale = PREVIEW_WIDTH / pixmap.width()
        scaled_height = round(pixmap.height() * self._scale)
        self._pixmap = pixmap.scaled(
            PREVIEW_WIDTH, scaled_height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        )
        self.setFixedHeight(scaled_height)
        self.setCursor(Qt.SizeVerCursor)
        self.update()

    def set_top_exclusion_px(self, px: int) -> None:
        """Move the top line to *px* device pixels without emitting a signal."""
        self._top_px = max(0, px)
        self.update()

    def set_bottom_exclusion_px(self, px: int) -> None:
        """Move the bottom line to *px* device pixels without emitting a signal."""
        self._bottom_px = max(0, px)
        self.update()

    def has_screenshot(self) -> bool:
        return self._pixmap is not None

    # -- painting ---------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        if self._pixmap is None:
            painter.fillRect(self.rect(), QColor("#2a2a2a"))
            painter.setPen(QColor("#999999"))
            painter.drawText(self.rect(), Qt.AlignCenter, self._placeholder_text)
            return

        painter.drawPixmap(0, 0, self._pixmap)
        width = self._pixmap.width()
        height = self._pixmap.height()
        top_y = self._top_line_y()
        bottom_y = self._bottom_line_y()

        # Shade the excluded bands.
        painter.fillRect(QRect(0, 0, width, top_y), TOP_SHADE_COLOR)
        painter.fillRect(QRect(0, bottom_y, width, height - bottom_y), BOTTOM_SHADE_COLOR)

        # Draw the draggable lines.
        painter.setPen(TOP_LINE_COLOR)
        painter.drawLine(0, top_y, width, top_y)
        painter.setPen(BOTTOM_LINE_COLOR)
        painter.drawLine(0, bottom_y, width, bottom_y)

    # -- drag interaction ---------------------------------------------------

    def _top_line_y(self) -> int:
        if self._pixmap is None:
            return 0
        return round(self._top_px * self._scale)

    def _bottom_line_y(self) -> int:
        if self._pixmap is None:
            return 0
        return self._pixmap.height() - round(self._bottom_px * self._scale)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._pixmap is None:
            return
        y = event.position().y()
        top_dist = abs(y - self._top_line_y())
        bottom_dist = abs(y - self._bottom_line_y())
        if top_dist > LINE_GRAB_MARGIN and bottom_dist > LINE_GRAB_MARGIN:
            return
        # Grab whichever line is closer when both are within reach.
        self._dragging_edge = "top" if top_dist <= bottom_dist else "bottom"
        self._update_from_mouse(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging_edge is not None:
            self._update_from_mouse(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging_edge = None

    def _update_from_mouse(self, event: QMouseEvent) -> None:
        if self._pixmap is None:
            return
        height = self._pixmap.height()
        y = max(0, min(round(event.position().y()), height))
        if self._dragging_edge == "top":
            device_px = round(y / self._scale)
            device_px = max(0, min(device_px, self._device_height))
            self._top_px = device_px
            self.update()
            self.top_exclusion_changed.emit(device_px)
        elif self._dragging_edge == "bottom":
            device_px = round((height - y) / self._scale)
            device_px = max(0, min(device_px, self._device_height))
            self._bottom_px = device_px
            self.update()
            self.bottom_exclusion_changed.emit(device_px)
