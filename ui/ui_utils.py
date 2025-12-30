#!/usr/bin/env python3
# ui/utils.py - Utility functions for the UI controller

import logging
import os
from typing import Optional

from PySide6.QtGui import QPixmap


def update_screenshot(screenshot_label, file_path: str, is_blocked: bool = False) -> None:
    """
    Update the screenshot displayed in the UI.
    
    Args:
        screenshot_label: The QLabel to display the screenshot
        file_path: Path to the screenshot file
        is_blocked: If True, screenshot was blocked by FLAG_SECURE and should show message instead
    """
    try:
        if is_blocked:
            # Display informative message instead of black screenshot
            from PySide6.QtCore import Qt as QtCore_Qt
            
            # Create a styled HTML message
            message_html = """
            <div style='text-align: center; padding: 40px; background-color: #FFF3CD; 
                        border: 2px solid #FF6B6B; border-radius: 8px; margin: 20px;'>
                <div style='font-size: 48px; margin-bottom: 20px;'>🔒</div>
                <div style='font-size: 24px; font-weight: bold; color: #721C24; margin-bottom: 15px;'>
                    Screenshot Blocked
                </div>
                <div style='font-size: 16px; color: #856404; line-height: 1.6;'>
                    This screen has <strong>FLAG_SECURE</strong> enabled,<br/>
                    preventing screenshots and OCR.<br/><br/>
                    Relying on <strong>XML data only</strong>.
                </div>
            </div>
            """
            screenshot_label.setText(message_html)
            screenshot_label.setAlignment(QtCore_Qt.AlignCenter)
            screenshot_label.setStyleSheet("background-color: white;")
            return
        
        # Normal screenshot display
        if not file_path or not os.path.exists(file_path):
            logging.error(f"Screenshot file not found: {file_path}")
            return
                
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            # Scale the pixmap to fit the label while maintaining aspect ratio
            label_size = screenshot_label.size()
            scaled_pixmap = pixmap.scaled(
                label_size.width(), 
                label_size.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            screenshot_label.setPixmap(scaled_pixmap)
            screenshot_label.setText("")  # Clear any previous text
            screenshot_label.setStyleSheet("")  # Clear any previous styling
        else:
            logging.error(f"Error loading screenshot: {file_path}")
    except Exception as e:
        logging.error(f"Error updating screenshot: {e}")


# Import here to avoid circular imports
from PySide6.QtCore import Qt

