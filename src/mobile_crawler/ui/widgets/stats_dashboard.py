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

        # Screen Discovery section
        screen_label = QLabel("Screen Discovery")
        screen_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        stats_layout.addWidget(screen_label, 4, 0, 1, 2)

        self.unique_screens_label = QLabel("Unique Screens: 0")
        stats_layout.addWidget(self.unique_screens_label, 5, 0)

        self.total_visits_label = QLabel("Total Visits: 0")
        stats_layout.addWidget(self.total_visits_label, 5, 1)

        self.screens_per_minute_label = QLabel("Screens/min: 0.0")
        stats_layout.addWidget(self.screens_per_minute_label, 6, 0)

        # AI Performance section
        ai_label = QLabel("AI Performance")
        ai_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        stats_layout.addWidget(ai_label, 7, 0, 1, 2)

        self.ai_calls_label = QLabel("AI Calls: 0")
        stats_layout.addWidget(self.ai_calls_label, 8, 0)

        self.ai_response_time_label = QLabel("Avg Response: 0ms")
        stats_layout.addWidget(self.ai_response_time_label, 8, 1)

        # Operation Timing section
        operation_timing_label = QLabel("Operation Timing")
        operation_timing_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        stats_layout.addWidget(operation_timing_label, 9, 0, 1, 2)

        self.ocr_avg_label = QLabel("OCR Avg: 0ms")
        stats_layout.addWidget(self.ocr_avg_label, 10, 0)

        self.action_avg_label = QLabel("Action Avg: 0ms")
        stats_layout.addWidget(self.action_avg_label, 10, 1)

        self.screenshot_avg_label = QLabel("Screenshot Avg: 0ms")
        stats_layout.addWidget(self.screenshot_avg_label, 11, 0)

        # Duration section
        duration_label = QLabel("Duration")
        duration_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        stats_layout.addWidget(duration_label, 12, 0, 1, 2)

        self.duration_label = QLabel("Elapsed: 0s")
        stats_layout.addWidget(self.duration_label, 13, 0)

        # Time progress bar
        time_progress_label = QLabel("Time Progress:")
        stats_layout.addWidget(time_progress_label, 14, 0)

        self.time_progress_bar = QProgressBar()
        self.time_progress_bar.setRange(0, self._max_duration_seconds)
        self.time_progress_bar.setValue(0)
        self.time_progress_bar.setTextVisible(True)
        self.time_progress_bar.setFormat("%v / %m seconds")
        stats_layout.addWidget(self.time_progress_bar, 14, 1)

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
    ):
        """Update the statistics display.
        
        Args:
            total_steps: Total number of steps taken
            successful_steps: Number of successful steps
            failed_steps: Number of failed steps
            unique_screens: Number of unique screens visited
            total_visits: Total number of screen visits
            screens_per_minute: Screens visited per minute
            ai_calls: Number of AI API calls
            avg_ai_response_time_ms: Average AI response time in ms
            duration_seconds: Elapsed time in seconds
            ocr_avg_ms: Average OCR processing time in ms
            action_avg_ms: Average action execution time in ms
            screenshot_avg_ms: Average screenshot capture time in ms
        """
        # Show stats content and hide placeholder if we have activity
        if total_steps > 0 or ai_calls > 0 or duration_seconds > 0:
            self.placeholder_label.setVisible(False)
            self.stats_content.setVisible(True)
        
        # Update labels
        self.total_steps_label.setText(f"Total Steps: {total_steps}")
        self.successful_steps_label.setText(f"Actions OK: {successful_steps}")
        self.failed_steps_label.setText(f"Actions Failed: {failed_steps}")
        self.unique_screens_label.setText(f"Unique Screens: {unique_screens}")
        self.total_visits_label.setText(f"Total Visits: {total_visits}")
        self.screens_per_minute_label.setText(f"Screens/min: {screens_per_minute:.1f}")
        self.ai_calls_label.setText(f"AI Calls: {ai_calls}")
        self.ai_response_time_label.setText(f"Avg Response: {avg_ai_response_time_ms:.0f}ms")
        self.duration_label.setText(f"Elapsed: {duration_seconds:.0f}s")
        
        # Operation timing
        self.ocr_avg_label.setText(f"OCR Avg: {ocr_avg_ms:.0f}ms")
        self.action_avg_label.setText(f"Action Avg: {action_avg_ms:.0f}ms")
        self.screenshot_avg_label.setText(f"Screenshot Avg: {screenshot_avg_ms:.0f}ms")

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
            unique_screens=0,
            total_visits=0,
            screens_per_minute=0.0,
            ai_calls=0,
            avg_ai_response_time_ms=0.0,
            duration_seconds=0.0,
            ocr_avg_ms=0.0,
            action_avg_ms=0.0,
            screenshot_avg_ms=0.0,
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

    def get_unique_screens(self) -> int:
        """Get the current unique screens value.
        
        Returns:
            Unique screens value
        """
        text = self.unique_screens_label.text()
        # Extract number from "Unique Screens: X"
        try:
            return int(text.split(": ")[1])
        except (IndexError, ValueError):
            return 0

    def get_ai_calls(self) -> int:
        """Get the current AI calls value.
        
        Returns:
            AI calls value
        """
        text = self.ai_calls_label.text()
        # Extract number from "AI Calls: X"
        try:
            return int(text.split(": ")[1])
        except (IndexError, ValueError):
            return 0
