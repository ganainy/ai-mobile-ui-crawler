"""Statistics dashboard widget for mobile-crawler GUI."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QGroupBox,
    QGridLayout,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class StatsDashboard(QWidget):
    """Widget for displaying real-time crawl statistics.
    
    Shows key metrics including steps, screens, errors, and AI performance.
    Includes progress bars for step and time limits.
    """

    # Signal emitted when stats are updated
    stats_updated = Signal()  # type: ignore

    def __init__(self, parent=None):
        """Initialize stats dashboard widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._max_steps = 100
        self._max_duration_seconds = 300
        self._setup_ui()

    def _setup_ui(self):
        """Set up user interface."""
        layout = QVBoxLayout()

        # Group box for statistics
        self.stats_group = QGroupBox("Statistics")
        self.main_stats_layout = QVBoxLayout(self.stats_group)

        # Placeholder for when no crawl is running
        self.placeholder_label = QLabel("Statistics will be shown once the crawler starts")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #888; font-style: italic; padding: 40px;")
        self.main_stats_layout.addWidget(self.placeholder_label)

        # Container for actual statistics
        self.stats_content = QWidget()
        stats_layout = QGridLayout(self.stats_content)

        # Crawl Progress section
        progress_label = QLabel("Crawl Progress")
        progress_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        stats_layout.addWidget(progress_label, 0, 0, 1, 2)

        # Steps metrics
        self.total_steps_label = QLabel("Total Steps: 0")
        stats_layout.addWidget(self.total_steps_label, 1, 0)

        self.successful_steps_label = QLabel("Actions OK: 0")
        stats_layout.addWidget(self.successful_steps_label, 1, 1)

        self.failed_steps_label = QLabel("Actions Failed: 0")
        stats_layout.addWidget(self.failed_steps_label, 2, 0)

        # Step progress bar
        step_progress_label = QLabel("Step Progress:")
        stats_layout.addWidget(step_progress_label, 3, 0)

        self.step_progress_bar = QProgressBar()
        self.step_progress_bar.setRange(0, self._max_steps)
        self.step_progress_bar.setValue(0)
        self.step_progress_bar.setTextVisible(True)
        self.step_progress_bar.setFormat("%v / %m steps")
        stats_layout.addWidget(self.step_progress_bar, 3, 1)

        # Duration section
        duration_label = QLabel("Duration")
        duration_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        stats_layout.addWidget(duration_label, 4, 0, 1, 2)

        self.duration_label = QLabel("Elapsed: 0s")
        stats_layout.addWidget(self.duration_label, 5, 0)

        # Time progress bar
        time_progress_label = QLabel("Time Progress:")
        stats_layout.addWidget(time_progress_label, 6, 0)

        self.time_progress_bar = QProgressBar()
        self.time_progress_bar.setRange(0, self._max_duration_seconds)
        self.time_progress_bar.setValue(0)
        self.time_progress_bar.setTextVisible(True)
        self.time_progress_bar.setFormat("%v / %m seconds")
        stats_layout.addWidget(self.time_progress_bar, 6, 1)

        self.stats_content.setVisible(False)
        self.main_stats_layout.addWidget(self.stats_content)

        layout.addWidget(self.stats_group)
        
        # Set the layout for this widget
        self.setLayout(layout)

    def set_max_steps(self, max_steps: int):
        """Set the maximum number of steps for progress bar.
        
        Args:
            max_steps: Maximum number of steps
        """
        self._max_steps = max_steps
        self.step_progress_bar.setRange(0, max_steps)
        self.step_progress_bar.setFormat(f"%v / {max_steps} steps")

    def set_max_duration(self, max_duration_seconds: int):
        """Set the maximum duration for progress bar.
        
        Args:
            max_duration_seconds: Maximum duration in seconds
        """
        self._max_duration_seconds = max_duration_seconds
        self.time_progress_bar.setRange(0, max_duration_seconds)
        self.time_progress_bar.setFormat(f"%v / {max_duration_seconds} seconds")

    def set_progress_mode(self, mode: str):
        """Set which progress bar to show based on crawl mode.
        
        Args:
            mode: 'steps' to show step progress bar only,
                  'duration' to show time progress bar only
        """
        if mode == 'steps':
            self.step_progress_bar.setVisible(True)
            self.time_progress_bar.setVisible(False)
        else:
            self.step_progress_bar.setVisible(False)
            self.time_progress_bar.setVisible(True)

    def update_stats(
        self,
        total_steps: int = 0,
        successful_steps: int = 0,
        failed_steps: int = 0,
        unique_screens: int = 0,
        total_visits: int = 0,
        screens_per_minute: float = 0.0,
        ai_calls: int = 0,
        avg_ai_response_time_ms: float = 0.0,
        duration_seconds: float = 0.0,
        ocr_avg_ms: float = 0.0,
        action_avg_ms: float = 0.0,
        screenshot_avg_ms: float = 0.0,
        last_action: str = "",
        step_progress: str = "",
        success_rate: float = 0.0,
    ):
        """Update the statistics display.

        Args:
            total_steps: Total number of steps taken
            successful_steps: Number of successful steps
            failed_steps: Number of failed steps
            unique_screens: (Unused - kept for backward compatibility)
            total_visits: (Unused - kept for backward compatibility)
            screens_per_minute: (Unused - kept for backward compatibility)
            ai_calls: (Unused - kept for backward compatibility)
            avg_ai_response_time_ms: (Unused - kept for backward compatibility)
            duration_seconds: Elapsed time in seconds
            ocr_avg_ms: (Unused - kept for backward compatibility)
            action_avg_ms: (Unused - kept for backward compatibility)
            screenshot_avg_ms: (Unused - kept for backward compatibility)
            last_action: Most recent action type
            step_progress: Step progress string e.g. "7 / 15"
            success_rate: Action success rate percentage
        """
        # Show stats content and hide placeholder if we have activity
        if total_steps > 0 or duration_seconds > 0:
            self.placeholder_label.setVisible(False)
            self.stats_content.setVisible(True)

        # Update labels
        self.total_steps_label.setText(f"Total Steps: {total_steps}")
        self.successful_steps_label.setText(f"Actions OK: {successful_steps}")
        self.failed_steps_label.setText(f"Actions Failed: {failed_steps}")
        self.duration_label.setText(f"Elapsed: {duration_seconds:.0f}s")

        # Update progress bars
        self.step_progress_bar.setValue(min(total_steps, self._max_steps))
        self.time_progress_bar.setValue(min(int(duration_seconds), self._max_duration_seconds))

        # Emit signal
        self.stats_updated.emit()

    def reset(self):
        """Reset all statistics to initial state."""
        self.placeholder_label.setVisible(True)
        self.stats_content.setVisible(False)
        self.update_stats(
            total_steps=0,
            successful_steps=0,
            failed_steps=0,
            duration_seconds=0.0,
        )

    def get_total_steps(self) -> int:
        """Get the current total steps value.

        Returns:
            Total steps value
        """
        text = self.total_steps_label.text()
        # Extract number from "Total Steps: X"
        try:
            return int(text.split(": ")[1])
        except (IndexError, ValueError):
            return 0

