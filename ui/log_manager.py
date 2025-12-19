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
            logging.debug(f"LOG (from thread): {message}")
            return

        level_map = {
            "red": ("[[ERROR]]", "#FF4136"),
            "orange": ("[[WARNING]]", "#FF851B"),
            "green": ("[[SUCCESS]]", "#2ECC40"),
            "blue": ("[[INFO]]", "#0074D9"),
            "gray": ("[[DEBUG]]", "#AAAAAA"),
            "magenta": ("[[FOCUS]]", "#F012BE"),
            "cyan": ("[[FOCUS]]", "#7FDBFF"),
            "yellow": ("[[FOCUS]]", "#FFDC00"),
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

    def log_action_with_focus(self, action_data: Dict[str, Any], step_count: Optional[int] = None):
        """Log action with focus area attribution."""
        action_type = action_data.get("action", "unknown")
        reasoning = action_data.get("reasoning", "No reasoning provided")
        focus_ids = action_data.get("focus_ids", [])
        focus_names = action_data.get("focus_names", [])

        # Format display
        if focus_names:
            focus_text = f" [Focus: {', '.join(focus_names)}]"
        elif focus_ids:
            focus_text = f" [Focus IDs: {', '.join(focus_ids)}]"
        else:
            focus_text = " [No focus influence specified]"

        # Determine prefix and color
        prefix, color = self._get_action_visuals(action_type, focus_ids)

        log_message = f"{prefix}Action: {action_type}{focus_text}\nReasoning: {reasoning}"
        
        # Log to main output
        self.log_message(log_message, color)

        # Update action history
        self._update_action_history(action_data, action_type, reasoning, step_count)

    def _get_action_visuals(self, action_type: str, focus_ids: List[str]) -> tuple:
        """Determine prefix emoji and color for an action."""
        if focus_ids:
            if any(fid in ["privacy_policy", "data_rights", "data_collection"] for fid in focus_ids):
                return "🔐 ", "magenta"
            elif any(fid in ["security_features", "account_privacy"] for fid in focus_ids):
                return "🔒 ", "cyan"
            elif any(fid in ["third_party", "advertising_tracking", "network_requests"] for fid in focus_ids):
                return "👁️ ", "orange"
            elif any(fid in ["location_tracking", "permissions"] for fid in focus_ids):
                return "📍 ", "yellow"
            else:
                return "🔍 ", "green"
        else:
            visual_map = {
                "click": ("👆 ", "blue"),
                "input": ("⌨️ ", "cyan"),
                "scroll_down": ("📜 ", "gray"),
                "scroll_up": ("📜 ", "gray"),
                "swipe_left": ("👈 ", "gray"),
                "swipe_right": ("👉 ", "gray"),
                "back": ("⬅️ ", "orange"),
            }
            return visual_map.get(action_type, ("⚡ ", "white"))

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
