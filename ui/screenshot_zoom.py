"""
Screenshot Zoom Viewer - Popup dialog for viewing screenshots at full size.

This module provides a clickable screenshot widget and zoom popup dialog.
Can be removed without affecting the rest of the codebase.
"""

import logging
import os
from typing import Optional

from PySide6.QtWidgets import (
    QLabel, QDialog, QVBoxLayout, QScrollArea, QApplication, QPushButton,
    QHBoxLayout, QWidget, QSlider
)
from PySide6.QtGui import QPixmap, QCursor
from PySide6.QtCore import Qt, Signal


class ClickableScreenshotLabel(QLabel):
    """A QLabel that emits a signal when clicked, for opening zoom view."""
    
    clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Click to zoom")
        self._current_file_path: Optional[str] = None
    
    def set_screenshot_path(self, file_path: str):
        """Store the current screenshot path for zoom view."""
        self._current_file_path = file_path
    
    def get_screenshot_path(self) -> Optional[str]:
        """Get the current screenshot path."""
        return self._current_file_path
    
    def mousePressEvent(self, event):
        """Handle mouse click to open zoom dialog."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ScreenshotZoomDialog(QDialog):
    """Dialog for viewing screenshots at full/zoomed size with controls."""
    
    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.zoom_level = 100  # Percentage
        
        self.setWindowTitle("Screenshot Viewer")
        self.setMinimumSize(600, 400)
        self.resize(900, 700)
        
        # Make dialog modal but allow interaction
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        
        self._setup_ui()
        self._load_image()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Controls bar
        controls = QHBoxLayout()
        
        # Zoom out button
        zoom_out_btn = QPushButton("➖ Zoom Out")
        zoom_out_btn.clicked.connect(self._zoom_out)
        controls.addWidget(zoom_out_btn)
        
        # Zoom slider
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(25, 400)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setTickInterval(25)
        self.zoom_slider.valueChanged.connect(self._on_slider_change)
        controls.addWidget(self.zoom_slider)
        
        # Zoom in button
        zoom_in_btn = QPushButton("➕ Zoom In")
        zoom_in_btn.clicked.connect(self._zoom_in)
        controls.addWidget(zoom_in_btn)
        
        # Zoom label
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        controls.addWidget(self.zoom_label)
        
        # Fit button
        fit_btn = QPushButton("Fit to Window")
        fit_btn.clicked.connect(self._fit_to_window)
        controls.addWidget(fit_btn)
        
        # Actual size button
        actual_btn = QPushButton("Actual Size (100%)")
        actual_btn.clicked.connect(self._actual_size)
        controls.addWidget(actual_btn)
        
        layout.addLayout(controls)
        
        # Scroll area for the image
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        
        layout.addWidget(self.scroll_area)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
    
    def _load_image(self):
        """Load the image from file."""
        if not self.file_path or not os.path.exists(self.file_path):
            self.image_label.setText("Image not found")
            return
        
        self.original_pixmap = QPixmap(self.file_path)
        if self.original_pixmap.isNull():
            self.image_label.setText("Failed to load image")
            return
        
        self._update_display()
    
    def _update_display(self):
        """Update the displayed image based on zoom level."""
        if not hasattr(self, 'original_pixmap') or self.original_pixmap.isNull():
            return
        
        # Calculate scaled size
        scale = self.zoom_level / 100.0
        new_width = int(self.original_pixmap.width() * scale)
        new_height = int(self.original_pixmap.height() * scale)
        
        # Scale the pixmap
        scaled = self.original_pixmap.scaled(
            new_width, new_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.image_label.setPixmap(scaled)
        self.zoom_label.setText(f"{self.zoom_level}%")
        
        # Update slider without triggering signal
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(self.zoom_level)
        self.zoom_slider.blockSignals(False)
    
    def _zoom_in(self):
        """Zoom in by 25%."""
        self.zoom_level = min(400, self.zoom_level + 25)
        self._update_display()
    
    def _zoom_out(self):
        """Zoom out by 25%."""
        self.zoom_level = max(25, self.zoom_level - 25)
        self._update_display()
    
    def _on_slider_change(self, value):
        """Handle zoom slider change."""
        self.zoom_level = value
        self._update_display()
    
    def _fit_to_window(self):
        """Fit image to window size."""
        if not hasattr(self, 'original_pixmap') or self.original_pixmap.isNull():
            return
        
        # Calculate zoom level to fit
        scroll_size = self.scroll_area.size()
        img_width = self.original_pixmap.width()
        img_height = self.original_pixmap.height()
        
        # Account for margins
        available_width = scroll_size.width() - 20
        available_height = scroll_size.height() - 20
        
        width_ratio = available_width / img_width
        height_ratio = available_height / img_height
        
        self.zoom_level = int(min(width_ratio, height_ratio) * 100)
        self.zoom_level = max(25, min(400, self.zoom_level))
        self._update_display()
    
    def _actual_size(self):
        """Show image at actual size (100%)."""
        self.zoom_level = 100
        self._update_display()


def show_screenshot_zoom(file_path: str, parent=None):
    """Open the screenshot zoom dialog.
    
    Args:
        file_path: Path to the screenshot file
        parent: Parent widget for the dialog
    """
    if not file_path or not os.path.exists(file_path):
        logging.warning(f"Cannot zoom: file not found: {file_path}")
        return
    
    dialog = ScreenshotZoomDialog(file_path, parent)
    dialog.exec()
