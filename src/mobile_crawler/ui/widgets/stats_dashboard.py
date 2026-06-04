"""Statistics dashboard widget for mobile-crawler GUI."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


def _make_section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Arial", 9, QFont.Weight.Bold))
    lbl.setStyleSheet("color: #aaa; text-transform: uppercase; letter-spacing: 1px;")
    return lbl


def _make_separator() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("color: #333;")
    return sep


class StatsDashboard(QWidget):
    """Widget for displaying real-time crawl statistics."""

    stats_updated = Signal()  # type: ignore

    def __init__(self, parent=None):
        super().__init__(parent)
        self._max_steps = 100
        self._max_duration_seconds = 300
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.stats_group = QGroupBox("Statistics")
        group_layout = QVBoxLayout(self.stats_group)
        group_layout.setSpacing(4)

        # Placeholder shown before crawl starts
        self.placeholder_label = QLabel("Statistics will be shown once the crawler starts")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #888; font-style: italic; padding: 40px;")
        group_layout.addWidget(self.placeholder_label)

        # Real stats content
        self.stats_content = QWidget()
        grid = QGridLayout(self.stats_content)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)

        row = 0

        # ── Crawl Progress ──────────────────────────────────────
        grid.addWidget(_make_section_label("Crawl Progress"), row, 0, 1, 2)
        row += 1

        self.total_steps_label = QLabel("Total Steps: 0")
        grid.addWidget(self.total_steps_label, row, 0)

        self.current_step_label = QLabel("Current: —")
        grid.addWidget(self.current_step_label, row, 1)
        row += 1

        grid.addWidget(QLabel("Step Progress:"), row, 0)
        self.step_progress_bar = QProgressBar()
        self.step_progress_bar.setRange(0, self._max_steps)
        self.step_progress_bar.setValue(0)
        self.step_progress_bar.setTextVisible(True)
        self.step_progress_bar.setFormat("%v / %m steps")
        grid.addWidget(self.step_progress_bar, row, 1)
        row += 1

        grid.addWidget(_make_separator(), row, 0, 1, 2)
        row += 1

        # ── Actions ─────────────────────────────────────────────
        grid.addWidget(_make_section_label("Actions"), row, 0, 1, 2)
        row += 1

        self.successful_steps_label = QLabel("Actions OK: 0")
        self.successful_steps_label.setStyleSheet("color: #4caf50;")
        grid.addWidget(self.successful_steps_label, row, 0)

        self.failed_steps_label = QLabel("Actions Failed: 0")
        self.failed_steps_label.setStyleSheet("color: #f44336;")
        grid.addWidget(self.failed_steps_label, row, 1)
        row += 1

        self.success_rate_label = QLabel("Success Rate: —")
        grid.addWidget(self.success_rate_label, row, 0)

        self.last_action_label = QLabel("Last Action: —")
        grid.addWidget(self.last_action_label, row, 1)
        row += 1

        grid.addWidget(_make_separator(), row, 0, 1, 2)
        row += 1

        # ── AI Performance ──────────────────────────────────────
        grid.addWidget(_make_section_label("AI Performance"), row, 0, 1, 2)
        row += 1

        self.ai_calls_label = QLabel("AI Calls: 0")
        grid.addWidget(self.ai_calls_label, row, 0)

        self.ai_response_time_label = QLabel("Avg Response: —")
        grid.addWidget(self.ai_response_time_label, row, 1)
        row += 1

        self.tokens_in_label = QLabel("Tokens In: —")
        grid.addWidget(self.tokens_in_label, row, 0)

        self.tokens_out_label = QLabel("Tokens Out: —")
        grid.addWidget(self.tokens_out_label, row, 1)
        row += 1

        grid.addWidget(_make_separator(), row, 0, 1, 2)
        row += 1

        # ── Tool Metrics ─────────────────────────────────────────
        grid.addWidget(_make_section_label("Tool Metrics"), row, 0, 1, 2)
        row += 1

        self.tool_calls_per_step_label = QLabel("Calls/Step: —")
        grid.addWidget(self.tool_calls_per_step_label, row, 0)

        self.tool_error_count_label = QLabel("Tool Errors: 0")
        self.tool_error_count_label.setStyleSheet("color: #f44336;")
        grid.addWidget(self.tool_error_count_label, row, 1)
        row += 1

        self.phase_transition_label = QLabel("Phase Transitions: 0")
        grid.addWidget(self.phase_transition_label, row, 0, 1, 2)
        row += 1

        grid.addWidget(_make_separator(), row, 0, 1, 2)
        row += 1

        # ── Duration ─────────────────────────────────────────────
        grid.addWidget(_make_section_label("Duration"), row, 0, 1, 2)
        row += 1

        self.duration_label = QLabel("Elapsed: 0s")
        grid.addWidget(self.duration_label, row, 0, 1, 2)
        row += 1

        self.stats_content.setVisible(False)
        group_layout.addWidget(self.stats_content)

        outer.addWidget(self.stats_group)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_max_steps(self, max_steps: int):
        self._max_steps = max_steps
        self.step_progress_bar.setRange(0, max_steps)
        self.step_progress_bar.setFormat(f"%v / {max_steps} steps")

    def set_max_duration(self, max_duration_seconds: int):
        """Store max duration for progress tracking."""
        self._max_duration_seconds = max_duration_seconds
        if getattr(self, "_progress_mode", "steps") == "duration":
            self.step_progress_bar.setRange(0, max_duration_seconds)
            self.step_progress_bar.setFormat(f"%v / {max_duration_seconds} sec")

    def set_progress_mode(self, mode: str):
        """Set whether the progress bar tracks 'steps' or 'duration'."""
        self._progress_mode = mode
        if mode == "duration":
            self.step_progress_bar.setRange(0, self._max_duration_seconds)
            self.step_progress_bar.setFormat(f"%v / {self._max_duration_seconds} sec")
        else:
            self.step_progress_bar.setRange(0, self._max_steps)
            self.step_progress_bar.setFormat(f"%v / {self._max_steps} steps")

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
        total_input_tokens: int = 0,
        total_output_tokens: int = 0,
        tool_calls_per_step: float = 0.0,
        tool_error_count: int = 0,
        phase_transition_count: int = 0,
    ):
        """Update all statistics labels and progress bar."""
        if total_steps > 0 or duration_seconds > 0:
            self.placeholder_label.setVisible(False)
            self.stats_content.setVisible(True)

        # ── Step progress ──────────────────────────────────────
        self.total_steps_label.setText(f"Total Steps: {total_steps}")

        if step_progress:
            self.current_step_label.setText(f"Current: {step_progress}")
        elif total_steps > 0:
            self.current_step_label.setText(f"Current: {total_steps}")
        else:
            self.current_step_label.setText("Current: —")

        if getattr(self, "_progress_mode", "steps") == "duration":
            self.step_progress_bar.setValue(min(int(duration_seconds), self._max_duration_seconds))
        else:
            self.step_progress_bar.setValue(min(total_steps, self._max_steps))

        # ── Actions ───────────────────────────────────────────
        self.successful_steps_label.setText(f"Actions OK: {successful_steps}")
        self.failed_steps_label.setText(f"Actions Failed: {failed_steps}")

        if successful_steps + failed_steps > 0:
            rate = round(successful_steps / (successful_steps + failed_steps) * 100)
            color = "#4caf50" if rate >= 70 else "#ff9800" if rate >= 40 else "#f44336"
            self.success_rate_label.setText(f"Success Rate: {rate}%")
            self.success_rate_label.setStyleSheet(f"color: {color};")
        else:
            self.success_rate_label.setText("Success Rate: —")
            self.success_rate_label.setStyleSheet("")

        self.last_action_label.setText(f"Last Action: {last_action or '—'}")

        # ── AI performance ────────────────────────────────────
        self.ai_calls_label.setText(f"AI Calls: {ai_calls}")
        if avg_ai_response_time_ms > 0:
            self.ai_response_time_label.setText(
                f"Avg Response: {avg_ai_response_time_ms / 1000:.1f}s"
            )
        else:
            self.ai_response_time_label.setText("Avg Response: —")

        if total_input_tokens > 0 or total_output_tokens > 0:
            self.tokens_in_label.setText(f"Tokens In: {total_input_tokens:,}")
            self.tokens_out_label.setText(f"Tokens Out: {total_output_tokens:,}")
        else:
            self.tokens_in_label.setText("Tokens In: —")
            self.tokens_out_label.setText("Tokens Out: —")

        # ── Duration ─────────────────────────────────────────
        self.duration_label.setText(f"Elapsed: {duration_seconds:.0f}s")

        # ── Tool Metrics ─────────────────────────────────────
        if tool_calls_per_step > 0:
            self.tool_calls_per_step_label.setText(f"Calls/Step: {tool_calls_per_step:.1f}")
        else:
            self.tool_calls_per_step_label.setText("Calls/Step: —")
        self.tool_error_count_label.setText(f"Tool Errors: {tool_error_count}")
        self.phase_transition_label.setText(f"Phase Transitions: {phase_transition_count}")

        self.stats_updated.emit()

    def reset(self):
        """Reset all statistics to initial state."""
        self.placeholder_label.setVisible(True)
        self.stats_content.setVisible(False)
        self.update_stats(total_steps=0, successful_steps=0, failed_steps=0, duration_seconds=0.0)

    def get_total_steps(self) -> int:
        text = self.total_steps_label.text()
        try:
            return int(text.split(": ")[1])
        except (IndexError, ValueError):
            return 0
