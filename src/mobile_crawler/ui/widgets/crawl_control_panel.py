"""Crawl control panel widget for mobile-crawler GUI."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox
)
from PySide6.QtCore import Signal

from mobile_crawler.core.crawl_controller import CrawlController
from mobile_crawler.core.crawl_state_machine import CrawlState


class CrawlControlPanel(QWidget):
    """Widget for controlling crawl execution.

    Provides Start/Pause/Resume/Stop buttons with state management.
    Emits control signals for crawl operations.
    """

    # Control signals
    start_requested = Signal()  # type: ignore
    pause_requested = Signal()  # type: ignore
    resume_requested = Signal()  # type: ignore
    stop_requested = Signal()  # type: ignore

    def __init__(self, crawl_controller: CrawlController, parent=None):
        """Initialize crawl control panel widget.

        Args:
            crawl_controller: CrawlController instance for state management
            parent: Parent widget
        """
        super().__init__(parent)
        self.crawl_controller = crawl_controller
        self._validation_passed: bool = False
        self._setup_ui()

    def _setup_ui(self):
        """Set up user interface."""
        layout = QVBoxLayout()

        # Group box for controls
        control_group = QGroupBox("Crawl Controls")
        control_layout = QHBoxLayout()

        # Start button
        self.start_button = QPushButton("Start Crawl")
        self.start_button.setEnabled(False)  # Disabled until validation passes
        self.start_button.setMinimumWidth(120)
        self.start_button.clicked.connect(self.start_requested.emit)
        control_layout.addWidget(self.start_button)

        # Pause button
        self.pause_button = QPushButton("Pause")
        self.pause_button.setEnabled(False)
        self.pause_button.setMinimumWidth(100)
        self.pause_button.clicked.connect(self.pause_requested.emit)
        control_layout.addWidget(self.pause_button)

        # Resume button
        self.resume_button = QPushButton("Resume")
        self.resume_button.setEnabled(False)
        self.resume_button.setVisible(False)  # Hidden by default
        self.resume_button.setMinimumWidth(100)
        self.resume_button.clicked.connect(self.resume_requested.emit)
        control_layout.addWidget(self.resume_button)

        # Stop button
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.setMinimumWidth(100)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        control_layout.addWidget(self.stop_button)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray; font-weight: bold;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        
        # Set the layout for this widget
        self.setLayout(layout)

    def update_state(self, state: CrawlState):
        """Update button states based on crawl state.

        Args:
            state: Current CrawlState
        """
        # Reset all buttons
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        # Update based on state
        if state == CrawlState.UNINITIALIZED:
            self.status_label.setText("Ready")
            self.status_label.setStyleSheet("color: gray; font-weight: bold;")
            self.start_button.setEnabled(self._validation_passed)
            self.pause_button.setVisible(True)
            self.resume_button.setVisible(False)

        elif state == CrawlState.INITIALIZING:
            self.status_label.setText("Initializing...")
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
            self.stop_button.setEnabled(True)
            self.pause_button.setVisible(True)
            self.resume_button.setVisible(False)

        elif state == CrawlState.RUNNING:
            self.status_label.setText("Running")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.pause_button.setVisible(True)
            self.resume_button.setVisible(False)

        elif state == CrawlState.PAUSED_MANUAL:
            self.status_label.setText("Paused")
            self.status_label.setStyleSheet("color: blue; font-weight: bold;")
            self.resume_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.pause_button.setVisible(False)
            self.resume_button.setVisible(True)

        elif state == CrawlState.STOPPING:
            self.status_label.setText("Stopping...")
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
            self.stop_button.setEnabled(False)
            self.pause_button.setVisible(True)
            self.resume_button.setVisible(False)

        elif state == CrawlState.STOPPED:
            self.status_label.setText("Stopped")
            self.status_label.setStyleSheet("color: gray; font-weight: bold;")
            self.start_button.setEnabled(self._validation_passed)
            self.pause_button.setVisible(True)
            self.resume_button.setVisible(False)

        elif state == CrawlState.ERROR:
            self.status_label.setText("Error")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.start_button.setEnabled(self._validation_passed)
            self.pause_button.setVisible(True)
            self.resume_button.setVisible(False)

    def set_validation_passed(self, passed: bool):
        """Set whether pre-crawl validation has passed.

        Args:
            passed: True if validation passed, False otherwise
        """
        self._validation_passed = passed

        # Enable/disable start button based on validation and current state
        current_state = self.crawl_controller.get_state()
        if current_state in [CrawlState.UNINITIALIZED, CrawlState.STOPPED, CrawlState.ERROR]:
            self.start_button.setEnabled(passed)
