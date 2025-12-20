# ui/log_manager.py - Handles UI logging and status updates

import logging
import time
from typing import Any, Dict, List, Optional
from PySide6.QtCore import QObject, QThread, Qt
from PySide6.QtWidgets import QApplication, QLabel, QProgressBar, QTextEdit

class LogManager(QObject):
    """Handles UI logging, status updates, and action history."""
    
    def __init__(
        self, 
        log_output: QTextEdit, 
        action_history_output: QTextEdit,
        status_label: QLabel,
        step_label: QLabel,
        progress_bar: QProgressBar,
        parent=None
    ):
        super().__init__(parent)
        self.log_output = log_output
        self.action_history = action_history_output
        self.status_label = status_label
        self.step_label = step_label
        self.progress_bar = progress_bar
        
    def log_message(self, message: str, color: str = "white"):
        """Append a message to the log output with a specified color."""
        if not self.log_output:
            return

        app = QApplication.instance()
        if app and app.thread() != QThread.currentThread():
            return

        level_map = {
            "red": ("[[ERROR]]", "#FF4136"),
            "orange": ("[[WARNING]]", "#FF851B"),
            "green": ("[[SUCCESS]]", "#2ECC40"),
            "blue": ("[[INFO]]", "#0074D9"),
            "gray": ("[[DEBUG]]", "#AAAAAA"),

        }

        log_level, hex_color = level_map.get(color.lower(), ("", "#FFFFFF"))

        if log_level:
            log_html = f"<font color='{hex_color}'>{log_level}</font> {message}"
        else:
            log_html = message

        try:
            self.log_output.append(log_html)
            scrollbar = self.log_output.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())
            QApplication.processEvents()
        except Exception as e:
            logging.error(f"Error updating log output: {e}")



    def _update_action_history(self, action_data: Dict[str, Any], action_type: str, reasoning: str, step_count: Optional[int]):
        """Append structured entry to action history."""
        if not self.action_history:
            return
            
        try:
            step_label = f"Step {step_count}" if step_count is not None else "Step"
            target_identifier = action_data.get("target_identifier")
            result_text = action_data.get("result") or action_data.get("status")

            structured_lines = [f"{step_label}: {action_type}"]
            if target_identifier:
                structured_lines.append(f"Target: {target_identifier}")
            structured_lines.append(f"Reasoning: {reasoning}")
            if result_text:
                structured_lines.append(f"Result: {result_text}")

            entry = "\n".join(structured_lines)
            self.action_history.append(entry)
            self.action_history.verticalScrollBar().setValue(self.action_history.verticalScrollBar().maximum())
        except Exception:
            pass

    def update_status(self, status: str, step: Optional[int] = None, progress: Optional[int] = None):
        """Update UI status elements."""
        if self.status_label:
            self.status_label.setText(f"Status: {status}")
        if step is not None and self.step_label:
            self.step_label.setText(f"Step: {step}")
        if progress is not None and self.progress_bar:
            self.progress_bar.setValue(progress)
        QApplication.processEvents()
