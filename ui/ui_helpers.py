#!/usr/bin/env python3
"""
UI Helper Classes
=================

Encapsulates common UI state management patterns used by the main controller.
"""

import logging
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLabel, QWidget


class SessionTimer:
    """Encapsulates session timing logic.
    
    Manages the elapsed time display during crawler sessions with
    proper state tracking for running, paused, and stopped states.
    """
    
    STATE_STOPPED = 'stopped'
    STATE_RUNNING = 'running'
    STATE_PAUSED = 'paused'
    
    COLORS = {
        'running': '#4CAF50',   # Green
        'paused': '#FFC107',    # Yellow/Amber
        'stopped': '#888888'    # Gray
    }
    
    def __init__(self, label_widget: QLabel):
        """Initialize the session timer.
        
        Args:
            label_widget: QLabel to display the time
        """
        self.label = label_widget
        self.elapsed_seconds = 0
        self.timer = QTimer()
        self.timer.setInterval(1000)  # 1 second intervals
        self.timer.timeout.connect(self._tick)
        self._state = self.STATE_STOPPED
    
    @property
    def state(self) -> str:
        """Get current timer state."""
        return self._state
    
    @property
    def is_running(self) -> bool:
        """Check if timer is currently running."""
        return self._state == self.STATE_RUNNING
    
    def start(self):
        """Start timer from zero."""
        self.elapsed_seconds = 0
        self._state = self.STATE_RUNNING
        self._update_display()
        self.timer.start()
    
    def pause(self):
        """Pause timer (keeps elapsed time)."""
        if self._state == self.STATE_RUNNING:
            self._state = self.STATE_PAUSED
            self.timer.stop()
            self._update_display()
    
    def resume(self):
        """Resume timer from paused state."""
        if self._state == self.STATE_PAUSED:
            self._state = self.STATE_RUNNING
            self.timer.start()
            self._update_display()
    
    def stop(self):
        """Stop timer (final state)."""
        self._state = self.STATE_STOPPED
        self.timer.stop()
        self._update_display()
    
    def reset(self):
        """Reset timer to initial state."""
        self.elapsed_seconds = 0
        self._state = self.STATE_STOPPED
        self._update_display()
    
    def _tick(self):
        """Increment timer (called every second)."""
        self.elapsed_seconds += 1
        self._update_display()
    
    def _update_display(self):
        """Update label with current time and state color."""
        hours = self.elapsed_seconds // 3600
        minutes = (self.elapsed_seconds % 3600) // 60
        seconds = self.elapsed_seconds % 60
        
        color = self.COLORS.get(self._state, self.COLORS['stopped'])
        
        self.label.setText(f"⏱️ {hours:02d}:{minutes:02d}:{seconds:02d}")
        self.label.setStyleSheet(
            f"color: {color}; font-weight: bold; font-size: 12px;"
        )


class BusyOverlay:
    """Manages busy overlay display.
    
    Provides a modal overlay that prevents user interaction
    during long-running operations.
    """
    
    def __init__(self, parent: QWidget):
        """Initialize busy overlay.
        
        Args:
            parent: Parent widget to overlay
        """
        self.parent = parent
        self._dialog = None
        self._message = "Working..."
    
    def show(self, message: str = "Working..."):
        """Show overlay with message.
        
        Args:
            message: Message to display in the overlay
        """
        self._message = message
        
        if self._dialog is None:
            self._create_dialog()
        
        if self._dialog:
            self._dialog.set_message(message)
            self._position_dialog()
            self._dialog.show()
            self._dialog.raise_()
            self._dialog.activateWindow()
            QApplication.processEvents()
    
    def hide(self):
        """Hide the overlay."""
        if self._dialog:
            if hasattr(self._dialog, 'close_dialog'):
                self._dialog.close_dialog()
            else:
                self._dialog.hide()
            QApplication.processEvents()
    
    def update_message(self, message: str):
        """Update the overlay message.
        
        Args:
            message: New message to display
        """
        self._message = message
        if self._dialog and hasattr(self._dialog, 'set_message'):
            self._dialog.set_message(message)
            QApplication.processEvents()
    
    def _create_dialog(self):
        """Create the dialog lazily."""
        try:
            # Import from custom_widgets where BusyDialog is defined
            from ui.custom_widgets import BusyDialog
            self._dialog = BusyDialog(self.parent)
        except ImportError:
            logging.warning("BusyDialog not available, overlay disabled")
            self._dialog = None
    
    def _position_dialog(self):
        """Position dialog over parent window."""
        if not self._dialog:
            return
            
        try:
            # Try frameGeometry first (includes title bar)
            geometry = self.parent.frameGeometry()
            self._dialog.setGeometry(geometry)
        except Exception:
            try:
                # Fallback to regular geometry
                geometry = self.parent.geometry()
                self._dialog.setGeometry(geometry)
            except Exception:
                # Last resort: don't set geometry
                pass
    
    def __enter__(self):
        """Context manager entry - show overlay."""
        self.show(self._message)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - hide overlay."""
        self.hide()
        return False  # Don't suppress exceptions
