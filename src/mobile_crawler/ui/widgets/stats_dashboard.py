"""Statistics dashboard widget for mobile-crawler GUI."""

import io

from PIL import Image
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from mobile_crawler.domain.element_overlay_renderer import ElementOverlayRenderer


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


def _make_stat_label(text: str, tooltip: str = "") -> QLabel:
    lbl = QLabel(text)
    if tooltip:
        lbl.setToolTip(tooltip)
    return lbl


class _ScreenshotView(QLabel):
    """Screenshot label that keeps a 9:16 aspect ratio and scales to fit."""

    _ASPECT_RATIO = 9 / 16  # width / height

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source_pixmap: QPixmap | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("border: 1px solid #333;")
        self.setText("No screenshot yet")

        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def set_source_pixmap(self, pixmap: QPixmap | None):
        self._source_pixmap = pixmap
        self._rescale()

    def clear(self):
        self._source_pixmap = None
        super().clear()
        self.setText("No screenshot yet")

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return max(round(width / self._ASPECT_RATIO), 1)

    def sizeHint(self) -> QSize:
        width = 260
        return QSize(width, self.heightForWidth(width))

    def minimumSizeHint(self) -> QSize:
        width = 180
        return QSize(width, self.heightForWidth(width))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self):
        if self._source_pixmap is None or self._source_pixmap.isNull():
            return
        scaled = self._source_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)


class StatsDashboard(QWidget):
    """Widget for displaying real-time crawl statistics."""

    stats_updated = Signal()  # type: ignore

    def __init__(self, parent=None):
        super().__init__(parent)
        self._max_steps = 100
        self._max_duration_seconds = 300
        self._overlay_renderer = ElementOverlayRenderer()
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

        # Real stats content, split into two columns: the screenshot on the
        # left (so it can be displayed large) and the metrics on the right.
        self.stats_content = QWidget()
        content_layout = QHBoxLayout(self.stats_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        content_layout.addWidget(self._build_screenshot_column(), 1)
        content_layout.addWidget(self._build_metrics_column(), 1)

        self.stats_content.setVisible(False)
        group_layout.addWidget(self.stats_content)

        outer.addWidget(self.stats_group)

    def _build_screenshot_column(self) -> QWidget:
        column = QWidget()
        column.setMaximumWidth(420)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        layout.addWidget(_make_section_label("Screenshot"))

        self.screenshot_label = _ScreenshotView()
        layout.addWidget(self.screenshot_label)

        self.screenshot_hint_label = QLabel(
            "For reference only — not necessarily what was sent to the AI this step."
        )
        self.screenshot_hint_label.setWordWrap(True)
        self.screenshot_hint_label.setStyleSheet("color: #888; font-size: 9px; font-style: italic;")
        self.screenshot_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screenshot_hint_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        layout.addWidget(self.screenshot_hint_label)
        layout.addStretch(1)

        return column

    def _build_metrics_column(self) -> QWidget:
        column = QWidget()
        column.setMinimumWidth(300)
        grid = QGridLayout(column)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)

        row = 0

        # ── Crawl Progress ──────────────────────────────────────
        grid.addWidget(_make_section_label("Crawl Progress"), row, 0, 1, 2)
        row += 1

        self.total_steps_label = _make_stat_label(
            "Total Steps: 0",
            "Number of crawl steps completed since the run started.",
        )
        grid.addWidget(self.total_steps_label, row, 0, 1, 2)
        row += 1

        self.current_step_label = _make_stat_label(
            "Current: —",
            "The step currently being executed, shown as 'step / limit'.",
        )
        grid.addWidget(self.current_step_label, row, 0, 1, 2)
        row += 1

        self.step_progress_label = _make_stat_label(
            "Step Progress:",
            "Progress toward the configured run limit, measured in steps or duration.",
        )
        grid.addWidget(self.step_progress_label, row, 0, 1, 2)
        row += 1

        self.step_progress_bar = QProgressBar()
        self.step_progress_bar.setRange(0, self._max_steps)
        self.step_progress_bar.setValue(0)
        self.step_progress_bar.setTextVisible(True)
        self.step_progress_bar.setFormat("%v / %m steps")
        self.step_progress_bar.setToolTip(
            "Progress toward the configured run limit, measured in steps or duration."
        )
        grid.addWidget(self.step_progress_bar, row, 0, 1, 2)
        row += 1

        grid.addWidget(_make_separator(), row, 0, 1, 2)
        row += 1

        # ── Actions ─────────────────────────────────────────────
        grid.addWidget(_make_section_label("Actions"), row, 0, 1, 2)
        row += 1

        self.successful_steps_label = _make_stat_label(
            "Actions OK: 0",
            "UI actions that executed successfully.",
        )
        self.successful_steps_label.setStyleSheet("color: #4caf50;")
        grid.addWidget(self.successful_steps_label, row, 0, 1, 2)
        row += 1

        self.failed_steps_label = _make_stat_label(
            "Actions Failed: 0",
            "UI actions that failed to execute.",
        )
        self.failed_steps_label.setStyleSheet("color: #f44336;")
        grid.addWidget(self.failed_steps_label, row, 0, 1, 2)
        row += 1

        self.success_rate_label = _make_stat_label(
            "Success Rate: —",
            "Share of attempted actions that succeeded (OK / total actions).",
        )
        grid.addWidget(self.success_rate_label, row, 0, 1, 2)
        row += 1

        self.last_action_label = _make_stat_label(
            "Last Action: —",
            "The most recent action performed by the crawler.",
        )
        grid.addWidget(self.last_action_label, row, 0, 1, 2)
        row += 1

        grid.addWidget(_make_separator(), row, 0, 1, 2)
        row += 1

        # ── AI Performance ──────────────────────────────────────
        grid.addWidget(_make_section_label("AI Performance"), row, 0, 1, 2)
        row += 1

        self.ai_calls_label = _make_stat_label(
            "AI Calls: 0",
            "Number of AI model requests made during the crawl.",
        )
        grid.addWidget(self.ai_calls_label, row, 0, 1, 2)
        row += 1

        self.ai_response_time_label = _make_stat_label(
            "Avg Response: —",
            "Average AI model response time per call.",
        )
        grid.addWidget(self.ai_response_time_label, row, 0, 1, 2)
        row += 1

        self.tokens_in_label = _make_stat_label(
            "Tokens In: —",
            "Total input tokens sent to the AI model.",
        )
        grid.addWidget(self.tokens_in_label, row, 0, 1, 2)
        row += 1

        self.tokens_out_label = _make_stat_label(
            "Tokens Out: —",
            "Total output tokens generated by the AI model.",
        )
        grid.addWidget(self.tokens_out_label, row, 0, 1, 2)
        row += 1

        grid.addWidget(_make_separator(), row, 0, 1, 2)
        row += 1

        # ── Tool Metrics ─────────────────────────────────────────
        grid.addWidget(_make_section_label("Tool Metrics"), row, 0, 1, 2)
        row += 1

        self.tool_calls_per_step_label = _make_stat_label(
            "Calls/Step: —",
            "Average number of agent tool calls made per crawl step.",
        )
        grid.addWidget(self.tool_calls_per_step_label, row, 0, 1, 2)
        row += 1

        self.tool_error_count_label = _make_stat_label(
            "Tool Errors: 0",
            "Number of agent tool calls that returned an error.",
        )
        self.tool_error_count_label.setStyleSheet("color: #f44336;")
        grid.addWidget(self.tool_error_count_label, row, 0, 1, 2)
        row += 1

        self.phase_transition_label = _make_stat_label(
            "Phase Transitions: 0",
            "Number of step phase changes observed (for example planning to acting).",
        )
        grid.addWidget(self.phase_transition_label, row, 0, 1, 2)
        row += 1

        grid.addWidget(_make_separator(), row, 0, 1, 2)
        row += 1

        # ── Screen Discovery ──────────────────────────────────────
        grid.addWidget(_make_section_label("Screen Discovery"), row, 0, 1, 2)
        row += 1

        self.unique_screens_label = _make_stat_label(
            "Unique Screens: —",
            "Number of distinct screens discovered during the crawl.",
        )
        grid.addWidget(self.unique_screens_label, row, 0, 1, 2)
        row += 1

        self.total_visits_label = _make_stat_label(
            "Total Visits: —",
            "Total screen visits, counting revisits of already-seen screens.",
        )
        grid.addWidget(self.total_visits_label, row, 0, 1, 2)
        row += 1

        self.screens_per_min_label = _make_stat_label(
            "Screens/min: —",
            "Average rate of screen visits per minute of crawl time.",
        )
        grid.addWidget(self.screens_per_min_label, row, 0, 1, 2)
        row += 1

        self.revisit_ratio_label = _make_stat_label(
            "Revisit Ratio: —",
            "Share of screen visits that revisited an already-seen screen.",
        )
        grid.addWidget(self.revisit_ratio_label, row, 0, 1, 2)
        row += 1

        grid.addWidget(_make_separator(), row, 0, 1, 2)
        row += 1

        # ── Timing ────────────────────────────────────────────────
        grid.addWidget(_make_section_label("Timing"), row, 0, 1, 2)
        row += 1

        self.ocr_avg_label = _make_stat_label(
            "Avg OCR: n/a (OCR not used)",
            "Average OCR grounding time per step (OCR is not used in the current pipeline).",
        )
        self.ocr_avg_label.setStyleSheet("color: #888;")
        grid.addWidget(self.ocr_avg_label, row, 0, 1, 2)
        row += 1

        self.action_avg_label = _make_stat_label(
            "Avg Action: —",
            "Average time to execute a single UI action.",
        )
        grid.addWidget(self.action_avg_label, row, 0, 1, 2)
        row += 1

        self.screenshot_avg_label = _make_stat_label(
            "Avg Screenshot: —",
            "Average time to capture a screenshot.",
        )
        grid.addWidget(self.screenshot_avg_label, row, 0, 1, 2)
        row += 1

        self.omniparser_avg_label = _make_stat_label(
            "Avg OmniParser: —",
            "Average time to parse the screen with OmniParser.",
        )
        grid.addWidget(self.omniparser_avg_label, row, 0, 1, 2)
        row += 1

        grid.addWidget(_make_separator(), row, 0, 1, 2)
        row += 1

        # ── Duration ─────────────────────────────────────────────
        grid.addWidget(_make_section_label("Duration"), row, 0, 1, 2)
        row += 1

        self.duration_label = _make_stat_label(
            "Elapsed: 0s",
            "Total wall-clock time since the crawl started.",
        )
        grid.addWidget(self.duration_label, row, 0, 1, 2)
        row += 1

        # Keep the metrics pinned to the top instead of stretched down
        grid.setRowStretch(row, 1)

        return column

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
        omniparser_avg_ms: float = 0.0,
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

        # ── Screen Discovery ─────────────────────────────────
        if unique_screens > 0 or total_visits > 0:
            self.unique_screens_label.setText(f"Unique Screens: {unique_screens}")
            self.total_visits_label.setText(f"Total Visits: {total_visits}")
            if screens_per_minute > 0:
                self.screens_per_min_label.setText(f"Screens/min: {screens_per_minute:.1f}")
            else:
                self.screens_per_min_label.setText("Screens/min: —")
        else:
            self.unique_screens_label.setText("Unique Screens: —")
            self.total_visits_label.setText("Total Visits: —")
            self.screens_per_min_label.setText("Screens/min: —")
            self.revisit_ratio_label.setText("Revisit Ratio: —")

        # ── Timing ─────────────────────────────────────────
        # ocr_avg_ms is accepted for caller compatibility but not displayed:
        # OCR grounding isn't part of the live pipeline (OmniParser/a11y tree
        # are used instead), so it's always inapplicable rather than "no data
        # yet" — the label says so explicitly instead of showing "—".

        if action_avg_ms > 0:
            self.action_avg_label.setText(f"Avg Action: {action_avg_ms:.0f} ms")
        else:
            self.action_avg_label.setText("Avg Action: —")

        if screenshot_avg_ms > 0:
            self.screenshot_avg_label.setText(f"Avg Screenshot: {screenshot_avg_ms:.0f} ms")
        else:
            self.screenshot_avg_label.setText("Avg Screenshot: —")

        if omniparser_avg_ms > 0:
            self.omniparser_avg_label.setText(f"Avg OmniParser: {omniparser_avg_ms:.0f} ms")
        else:
            self.omniparser_avg_label.setText("Avg OmniParser: —")

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
        self.screenshot_label.clear()
        self.screenshot_label.setText("No screenshot yet")
        self.screenshot_hint_label.setText(
            "For reference only — not necessarily what was sent to the AI this step."
        )
        self.unique_screens_label.setText("Unique Screens: —")
        self.total_visits_label.setText("Total Visits: —")
        self.screens_per_min_label.setText("Screens/min: —")
        self.ocr_avg_label.setText("Avg OCR: n/a (OCR not used)")
        self.action_avg_label.setText("Avg Action: —")
        self.screenshot_avg_label.setText("Avg Screenshot: —")
        self.omniparser_avg_label.setText("Avg OmniParser: —")
        self.update_stats(total_steps=0, successful_steps=0, failed_steps=0, duration_seconds=0.0)

    def update_screenshot(self, screenshot_path: str | None, elements: list[dict] | None, vision_enabled: bool):
        """Update the screenshot display with optional element overlay.

        Args:
            screenshot_path: Path to the screenshot file, or None if no screenshot
            elements: List of UI elements to overlay (with 'index' and 'bounds'), or None
            vision_enabled: Whether vision was enabled for this step
        """
        if not screenshot_path:
            self.screenshot_label.clear()
            self.screenshot_label.setText("No screenshot yet")
            return

        try:
            # Load screenshot as PIL image
            pil_image = Image.open(screenshot_path)

            # Render overlay if elements are available
            if elements:
                pil_image = self._overlay_renderer.render(pil_image, elements)

            # Convert PIL image to QPixmap via in-memory buffer
            buffer = io.BytesIO()
            pil_image.save(buffer, format="PNG")
            buffer.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.read())

            # The view stores the source and rescales it to its own size
            self.screenshot_label.set_source_pixmap(pixmap)

            # Update hint text
            if not vision_enabled:
                self.screenshot_hint_label.setText(
                    "Vision disabled this step — shown for reference; "
                    "a text description was sent to the AI instead."
                )
            else:
                self.screenshot_hint_label.setText(
                    "For reference only — not necessarily what was sent to the AI this step."
                )

        except Exception as e:
            self.screenshot_label.clear()
            self.screenshot_label.setText(f"Error loading screenshot: {e}")

    def get_total_steps(self) -> int:
        text = self.total_steps_label.text()
        try:
            return int(text.split(": ")[1])
        except (IndexError, ValueError):
            return 0
