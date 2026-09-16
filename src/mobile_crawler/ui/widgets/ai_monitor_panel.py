"""AI Monitor Panel widget for displaying AI interactions in real-time."""

import base64
import html
import json
import logging
import os
import re
from datetime import datetime

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSize, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import io
from PIL import Image
from mobile_crawler.domain.element_overlay_renderer import ElementOverlayRenderer
from .prompt_fields_widget import PromptFieldsWidget

logger = logging.getLogger(__name__)


def _extract_prompt_text(request_data: dict) -> str:
    """Pull the prompt text out of a request_data dict (shape produced by the crawler service)."""
    if "user_prompt" in request_data:
        return request_data["user_prompt"]
    if "prompt" in request_data:
        return request_data["prompt"]
    return ""


def _extract_response_text(response_data: dict) -> str:
    """Pull the raw response text out of a response_data dict."""
    if "response" in response_data:
        return response_data["response"]
    if "raw_response" in response_data:
        return response_data["raw_response"]
    if "parsed_response" in response_data:
        return response_data["parsed_response"]
    return ""


def _extract_parsed_actions(response_data: dict) -> list[dict]:
    """Pull the parsed actions list out of a response_data dict, if any."""
    if response_data.get("actions"):
        return response_data["actions"]
    if "parsed_response" in response_data:
        try:
            parsed = json.loads(response_data["parsed_response"])
            if isinstance(parsed, dict) and "actions" in parsed:
                return parsed["actions"]
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, KeyError):
            pass
    return []


_JSON_FENCE_RE = re.compile(r"```json\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _extract_embedded_json(raw_text: str):
    """Find and parse a JSON blob within a larger text response, if any.

    Many raw responses (e.g. the Manager's <thought>/<plan>/```json block)
    aren't valid JSON as a whole, which used to make the prompt tree fall back
    to a single table row with an empty key and the entire blob crammed into
    the value cell. Split the two apart instead: return the surrounding plain
    text (JSON portion removed) and the parsed JSON object, so each can be
    rendered appropriately.

    Returns:
        (plain_text, parsed_json) — parsed_json is None if nothing
        JSON-shaped was found; plain_text is the original text unchanged
        in that case.
    """
    if not raw_text:
        return raw_text, None

    stripped = raw_text.strip()
    try:
        return "", json.loads(stripped)
    except (json.JSONDecodeError, TypeError):
        pass

    match = _JSON_FENCE_RE.search(raw_text)
    if match:
        try:
            parsed = json.loads(match.group(1).strip())
        except (json.JSONDecodeError, TypeError):
            return raw_text, None
        plain_text = (raw_text[: match.start()] + raw_text[match.end():]).strip()
        return plain_text, parsed

    return raw_text, None


_JSON_TOKEN_RE = re.compile(
    r'(?P<key>"(?:\\.|[^"\\])*"(?=\s*:))'
    r'|(?P<string>"(?:\\.|[^"\\])*")'
    r'|(?P<bool>\btrue\b|\bfalse\b|\bnull\b)'
    r'|(?P<number>-?\d+\.?\d*)'
)

_JSON_TOKEN_COLORS = {
    "key": "#9cdcfe",
    "string": "#ce9178",
    "bool": "#569cd6",
    "number": "#b5cea8",
}


def _json_to_html(obj) -> str:
    """Pretty-print a JSON-able object as syntax-colored HTML for a QTextEdit."""
    text = json.dumps(obj, indent=2, ensure_ascii=False)

    def _colorize(m: re.Match) -> str:
        color = _JSON_TOKEN_COLORS[m.lastgroup]
        return f'<span style="color:{color};">{html.escape(m.group())}</span>'

    colored = _JSON_TOKEN_RE.sub(_colorize, text)
    return f'<pre style="font-family:monospace; white-space:pre-wrap; margin:0;">{colored}</pre>'


class CollapsibleSection(QWidget):
    """A titled section that can be expanded/collapsed by clicking its header."""

    def __init__(self, title: str, content: QWidget, collapsed: bool = True, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.toggle_button = QToolButton()
        self.toggle_button.setStyleSheet("QToolButton { border: none; font-weight: bold; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(not collapsed)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if not collapsed else Qt.ArrowType.RightArrow)
        self.toggle_button.setText(f" {title}")
        self.toggle_button.clicked.connect(self._on_toggled)
        layout.addWidget(self.toggle_button)

        self.content = content
        self.content.setVisible(not collapsed)
        layout.addWidget(self.content)

    def _on_toggled(self, checked: bool) -> None:
        self.content.setVisible(checked)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)


class AIInteractionItem(QWidget):
    """Custom widget for displaying a single AI interaction in the list."""

    show_details_requested = Signal(int)  # Emits step_number

    def __init__(self, step_number: int, timestamp: datetime, success: bool,
                 latency_ms: float | None, tokens_in: int | None,
                 tokens_out: int | None, error_message: str | None,
                 prompt_preview: str, response_preview: str,
                 full_prompt: str, full_response: str,
                 parsed_actions: list[dict], pending: bool = False,
                 timing_summary: dict | None = None, parent=None):
        """Initialize AI interaction item.

        Args:
            step_number: Step number in crawl
            timestamp: When interaction occurred
            success: Whether interaction succeeded
            latency_ms: Response time in milliseconds
            tokens_in: Input token count
            tokens_out: Output token count
            error_message: Error message if failed
            prompt_preview: Truncated prompt preview
            response_preview: Truncated response preview
            full_prompt: Complete prompt text
            full_response: Complete response text
            parsed_actions: Parsed action details
            pending: Whether interaction is still pending
            parent: Parent widget
        """
        super().__init__(parent)
        self.step_number = step_number
        self.timestamp = timestamp
        self.success = success
        self.latency_ms = latency_ms
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.error_message = error_message
        self.prompt_preview = prompt_preview
        self.response_preview = response_preview
        self.full_prompt = full_prompt
        self.full_response = full_response
        self.parsed_actions = parsed_actions
        self.pending = pending
        self.timing_summary = timing_summary or {}

        self.expanded = False
        self.list_item = None  # Will be set after creation
        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Header row with status, step, metrics, timestamp
        header_layout = QHBoxLayout()

        # Status indicator
        status_label = QLabel()
        if self.pending:
            status_label.setText("○")
            status_label.setStyleSheet("color: gray; font-weight: bold;")
        elif self.success:
            status_label.setText("✓")
            status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            status_label.setText("✗")
            status_label.setStyleSheet("color: red; font-weight: bold;")
        header_layout.addWidget(status_label)

        # Step number
        step_label = QLabel(f"Step {self.step_number}")
        step_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(step_label)

        # Metrics
        metrics_parts = []
        step_duration_ms = self.timing_summary.get("total_step_duration_ms")
        if step_duration_ms is not None:
            metrics_parts.append(f"step {step_duration_ms / 1000:.1f}s")
        if self.latency_ms is not None:
            metrics_parts.append(f"AI {self.latency_ms/1000:.1f}s")
        if self.tokens_in is not None and self.tokens_out is not None:
            metrics_parts.append(f"{self.tokens_in}→{self.tokens_out}")
        elif self.tokens_in is not None:
            metrics_parts.append(f"{self.tokens_in}→?")
        elif self.tokens_out is not None:
            metrics_parts.append(f"?→{self.tokens_out}")

        metrics_text = " | ".join(metrics_parts) if metrics_parts else ""
        metrics_label = QLabel(metrics_text)
        metrics_label.setStyleSheet("color: #666;")
        header_layout.addWidget(metrics_label)

        header_layout.addStretch()

        # Timestamp
        time_str = self.timestamp.strftime("%H:%M:%S")
        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: #666;")
        header_layout.addWidget(time_label)

        layout.addLayout(header_layout)

        # Content preview (collapsed state)
        preview_text = f"Prompt: {self.prompt_preview}\nResponse: {self.response_preview}"
        self.preview_label = QLabel(preview_text)
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("margin-left: 20px;")
        layout.addWidget(self.preview_label)

        # Show Details button
        self.expand_button = QPushButton("Show Details")
        self.expand_button.clicked.connect(lambda: self.show_details_requested.emit(self.step_number))
        layout.addWidget(self.expand_button)

        # Error message (if any)
        if self.error_message:
            error_label = QLabel(f"Error: {self.error_message}")
            error_label.setStyleSheet("color: red; font-style: italic;")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)



class _ScalableScreenshotLabel(QLabel):
    """Screenshot label that fills the width the layout gives it.

    Unlike a fixed `scaledToWidth(200)` pixmap, this keeps the source image's
    aspect ratio via `heightForWidth` (so a taller column means a taller,
    sharper screenshot) and scales the pixmap up to a height ceiling, beyond
    which it centres the image instead of growing the row forever.
    """

    def __init__(self, max_height: int = 900, parent=None):
        super().__init__(parent)
        self._source_pixmap: QPixmap | None = None
        self._max_height = max_height
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("border: 1px solid #3d3d3d; background-color: #1e1e1e;")
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def set_source_pixmap(self, pixmap: QPixmap | None) -> None:
        self._source_pixmap = pixmap
        self._rescale()

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        if not self._source_pixmap or self._source_pixmap.isNull() or self._source_pixmap.width() == 0:
            return 320
        ratio = self._source_pixmap.height() / self._source_pixmap.width()
        return max(1, min(round(width * ratio), self._max_height))

    def sizeHint(self) -> QSize:
        return QSize(380, self.heightForWidth(380))

    def minimumSizeHint(self) -> QSize:
        return QSize(220, 320)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        if not self._source_pixmap or self._source_pixmap.isNull():
            return
        super().setPixmap(
            self._source_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class StepDetailWidget(QWidget):
    """Widget for displaying detailed step information in a tab.

    Layout: the screenshot gets the left column; the right column stacks the
    prompt that was sent (the bulky part, so it gets most of the height) over
    the Result (parsed action, reasoning, raw response). The timing breakdown
    stays collapsed at the bottom as supporting detail.

    A step may involve multiple AI calls (e.g. Manager plan, then Executor
    action) — `calls` carries all of them, and a selector lets the viewer
    switch between their Result/Prompt views when there's more than one.
    """

    def __init__(self, step_number: int, timestamp: datetime, success: bool,
                 calls: list[dict], default_index: int = 0,
                 screenshot_path: str | None = None,
                 timing_data: dict | None = None, parent=None):
        """Initialize step detail widget.

        Args:
            step_number: Step number
            timestamp: When interaction occurred
            success: Whether the step overall succeeded (AND of all its calls)
            calls: List of {label, success, error_message, prompt_text,
                response_text, parsed_actions} dicts, one per AI call made
                during this step, in order
            default_index: Which call to show first (the most relevant one)
            screenshot_path: Optional path to screenshot file
            timing_data: Step-level timing breakdown data
            parent: Parent widget
        """
        super().__init__(parent)
        self.step_number = step_number
        self.timestamp = timestamp
        self.success = success
        self.calls = calls or [
            {
                "label": "Call",
                "success": success,
                "error_message": None,
                "prompt_text": "",
                "response_text": "",
                "parsed_actions": [],
            }
        ]
        self.default_index = default_index if 0 <= default_index < len(self.calls) else 0
        self.screenshot_path = screenshot_path
        self.timing_data = timing_data or {}
        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        status_text = "✓ Success" if self.success else "✗ Failed"
        status_color = "green" if self.success else "red"
        title_label = QLabel(f"Step {self.step_number} - {status_text}")
        title_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {status_color};")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        time_label = QLabel(self.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        time_label.setStyleSheet("color: #666;")
        header_layout.addWidget(time_label)
        layout.addLayout(header_layout)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # ---- Main tier: Screenshot (left) + Prompt over Result (right) ----
        # The prompt is the bulky part, so it takes the top of the right
        # column; the Result is usually a few lines and sits underneath it.
        top_row_layout = QHBoxLayout()

        screenshot_group = self._build_screenshot_group()
        top_row_layout.addWidget(screenshot_group, 2)

        right_column_layout = QVBoxLayout()

        self.result_stack = QStackedWidget()
        self.prompt_stack = QStackedWidget()
        for call in self.calls:
            self.result_stack.addWidget(self._build_result_page(call))
            self.prompt_stack.addWidget(self._build_prompt_fields(call))
        self.result_stack.setCurrentIndex(self.default_index)
        self.prompt_stack.setCurrentIndex(self.default_index)

        if len(self.calls) > 1:
            selector_layout = QHBoxLayout()
            selector_layout.addWidget(QLabel("Call:"))
            self.call_selector = QComboBox()
            for call in self.calls:
                self.call_selector.addItem(call.get("label", "Call"))
            self.call_selector.setCurrentIndex(self.default_index)
            self.call_selector.currentIndexChanged.connect(self._on_call_selected)
            selector_layout.addWidget(self.call_selector)
            selector_layout.addStretch()
            right_column_layout.addLayout(selector_layout)
        else:
            self.call_selector = None

        # Prompt sent dominates the right column (its value boxes soak up the
        # spare height); the Result keeps only the room its few lines need.
        prompt_section = CollapsibleSection("Prompt sent", self.prompt_stack, collapsed=False)
        right_column_layout.addWidget(prompt_section, 1)

        result_group = QGroupBox("Result")
        result_group_layout = QVBoxLayout(result_group)
        result_group_layout.addWidget(self.result_stack)
        right_column_layout.addWidget(result_group, 0)

        top_row_layout.addLayout(right_column_layout, 3)
        scroll_layout.addLayout(top_row_layout)

        timing_group = self._create_timing_group()
        if timing_group:
            timing_section = CollapsibleSection("Timing breakdown", timing_group, collapsed=True)
            scroll_layout.addWidget(timing_section)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def _on_call_selected(self, index: int) -> None:
        """Switch the Result/Prompt views to the selected call."""
        self.result_stack.setCurrentIndex(index)
        self.prompt_stack.setCurrentIndex(index)

    def _build_result_page(self, call: dict) -> QWidget:
        """Build one page of the Result stack for a single AI call."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        if call.get("error_message"):
            error_label = QLabel(f"Error: {call['error_message']}")
            error_label.setStyleSheet("color: red; font-weight: bold;")
            error_label.setWordWrap(True)
            page_layout.addWidget(error_label)

        parsed_actions = call.get("parsed_actions") or []
        if parsed_actions:
            actions_text = ""
            for action in parsed_actions:
                actions_text += f"• Action: {action.get('action', 'unknown')}\n"
                if action.get('action_desc'):
                    actions_text += f"  Description: {action['action_desc']}\n"
                elif action.get('description'):
                    actions_text += f"  Description: {action['description']}\n"

                # Check for label_id OR target_bounding_box
                label_id = action.get('label_id')
                bbox = action.get('target_bounding_box')

                if label_id is not None:
                    actions_text += f"  Label ID: {label_id}\n"
                elif bbox:
                    tl = bbox.get('top_left')
                    br = bbox.get('bottom_right')
                    if tl and br and len(tl) >= 2 and len(br) >= 2:
                        actions_text += f"  Target: [{tl[0]}, {tl[1]}] → [{br[0]}, {br[1]}]\n"
                    else:
                        actions_text += f"  Target: {bbox}\n"

                if action.get('input_text'):
                    actions_text += f"  Input: {action['input_text']}\n"
                if action.get('reasoning'):
                    actions_text += f"  Reasoning: {action['reasoning']}\n"
                actions_text += "\n"

            actions_display = QTextEdit()
            actions_display.setPlainText(actions_text.strip())
            actions_display.setReadOnly(True)
            page_layout.addWidget(actions_display)
        else:
            no_actions_label = QLabel("No parsed actions available")
            no_actions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_actions_label.setStyleSheet("color: #666; font-style: italic;")
            page_layout.addWidget(no_actions_label)

        raw_response_section = CollapsibleSection(
            "Raw response", self._build_raw_response_widget(call.get("response_text") or ""), collapsed=True
        )
        page_layout.addWidget(raw_response_section)

        return page

    @staticmethod
    def _build_raw_response_widget(response_text: str) -> QWidget:
        """Render a raw response as plain text plus any embedded JSON, colored.

        Many raw responses aren't valid JSON as a whole (e.g. the Manager's
        <thought>/<plan>/```json block) — showing them through a plain
        key/value tree used to produce one row with an empty key and the
        entire blob crammed into the value cell. Split the two apart: plain
        text stays plain text, and any embedded JSON gets pretty-printed
        with syntax coloring so its fields are easy to see.
        """
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        plain_text, embedded_json = _extract_embedded_json(response_text)

        if plain_text:
            text_display = QTextEdit()
            text_display.setPlainText(plain_text)
            text_display.setReadOnly(True)
            container_layout.addWidget(text_display)

        if embedded_json is not None:
            if plain_text:
                container_layout.addWidget(QLabel("Parsed JSON:"))
            json_display = QTextEdit()
            json_display.setReadOnly(True)
            json_display.setHtml(_json_to_html(embedded_json))
            container_layout.addWidget(json_display)
        elif not plain_text:
            empty_label = QLabel("No response text")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #666; font-style: italic;")
            container_layout.addWidget(empty_label)

        return container

    def _build_prompt_fields(self, call: dict) -> QWidget:
        """Build one page of the Prompt stack for a single AI call."""
        full_prompt = call.get("prompt_text") or ""
        prompt_json_data = full_prompt

        try:
            prompt_data = json.loads(full_prompt)
            if isinstance(prompt_data, dict):
                actual_prompt_data = prompt_data
                if 'user_prompt' in prompt_data:
                    try:
                        actual_prompt_data = json.loads(prompt_data['user_prompt'])
                    except (json.JSONDecodeError, TypeError):
                        actual_prompt_data = prompt_data

                prompt_json_data = actual_prompt_data.copy() if isinstance(actual_prompt_data, dict) else actual_prompt_data
                if isinstance(prompt_json_data, dict) and 'screenshot' in prompt_json_data:
                    screenshot_value = prompt_json_data['screenshot']
                    if screenshot_value and len(screenshot_value) > 100:
                        prompt_json_data['screenshot'] = "[Image displayed on left]"
                    else:
                        prompt_json_data['screenshot'] = "(none sent for this call)"
        except (json.JSONDecodeError, TypeError):
            if len(full_prompt) > 1000 and all(
                c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
                for c in full_prompt.replace('\n', '').replace('\r', '').replace(' ', '')
            ):
                prompt_json_data = "[Large base64 data - not displayed]"

        return PromptFieldsWidget(prompt_json_data)

    def _build_screenshot_group(self) -> QGroupBox:
        """Build the Screenshot group with element overlay checkbox."""
        screenshot_group = QGroupBox("Screenshot")
        self.screenshot_layout = QVBoxLayout(screenshot_group)
        self._overlay_renderer = ElementOverlayRenderer()

        # Checkbox to toggle element labels
        toggle_layout = QHBoxLayout()
        self.show_labels_checkbox = QCheckBox("Show element labels")
        self.show_labels_checkbox.setChecked(True)
        self.show_labels_checkbox.stateChanged.connect(self._on_toggle_changed)
        toggle_layout.addWidget(self.show_labels_checkbox)
        toggle_layout.addStretch()
        self.screenshot_layout.addLayout(toggle_layout)

        self.orig_pixmap = None
        self.overlaid_pixmap = None

        screenshot_pixmap = None
        if self.screenshot_path and os.path.exists(self.screenshot_path):
            pixmap = QPixmap(self.screenshot_path)
            if not pixmap.isNull():
                screenshot_pixmap = pixmap

        if not screenshot_pixmap:
            # Fallback: look for a base64 screenshot embedded in any call's prompt
            for call in self.calls:
                prompt_text = call.get("prompt_text") or ""
                try:
                    prompt_data = json.loads(prompt_text)
                except (json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(prompt_data, dict):
                    continue
                actual = prompt_data
                if 'user_prompt' in prompt_data:
                    try:
                        actual = json.loads(prompt_data['user_prompt'])
                    except (json.JSONDecodeError, TypeError):
                        actual = prompt_data
                screenshot_b64 = actual.get('screenshot', '') if isinstance(actual, dict) else ''
                if screenshot_b64 and len(screenshot_b64) > 100:
                    try:
                        if screenshot_b64.startswith('data:image'):
                            screenshot_b64 = screenshot_b64.split(',', 1)[1]
                        image_data = base64.b64decode(screenshot_b64)
                        pixmap = QPixmap()
                        if pixmap.loadFromData(image_data):
                            screenshot_pixmap = pixmap
                            break
                    except Exception:
                        pass

        if screenshot_pixmap:
            self.orig_pixmap = screenshot_pixmap

            # Use the first call that has ui_elements captured (added alongside
            # request_data by crawler_agent_service.py, not nested in prompt_text)
            elements = None
            status_bar_exclusion_px = 0
            for call in self.calls:
                if call.get("ui_elements"):
                    elements = call["ui_elements"]
                    status_bar_exclusion_px = call.get("status_bar_exclusion_px", 0)
                    break

            # Render overlay if elements available
            if elements:
                # Name the actual source in the checkbox label so it's clear
                # what's being shown — OmniParser only kicks in as a fallback
                # when the accessibility tree is sparse; otherwise the labels
                # come from the plain a11y tree.
                first = elements[0] if isinstance(elements[0], dict) else {}
                source_label = "OmniParser" if first.get("source") == "omni" else "Accessibility tree"
                self.show_labels_checkbox.setText(f"Show element labels ({source_label})")
                try:
                    # Convert QPixmap to PIL Image via QBuffer (QPixmap.save()
                    # needs a real QIODevice, not a Python io.BytesIO)
                    qbuffer = QBuffer()
                    qbuffer.open(QIODevice.OpenModeFlag.WriteOnly)
                    screenshot_pixmap.save(qbuffer, "PNG")
                    pil_image = Image.open(io.BytesIO(qbuffer.data().data()))
                    qbuffer.close()

                    # Render overlay
                    overlaid_pil = self._overlay_renderer.render(
                        pil_image, elements, top_offset_px=status_bar_exclusion_px
                    )

                    # Convert back to QPixmap
                    out_buffer = io.BytesIO()
                    overlaid_pil.save(out_buffer, format="PNG")
                    overlaid_pixmap = QPixmap()
                    overlaid_pixmap.loadFromData(QByteArray(out_buffer.getvalue()))
                    self.overlaid_pixmap = overlaid_pixmap
                except Exception as e:
                    logger.warning(f"Failed to render element-label overlay: {e}", exc_info=True)
                    self.overlaid_pixmap = screenshot_pixmap
            else:
                # No elements data — disable checkbox and show plain screenshot
                self.overlaid_pixmap = screenshot_pixmap
                self.show_labels_checkbox.setEnabled(False)

            self.screenshot_label = _ScalableScreenshotLabel()
            display_pixmap = self.overlaid_pixmap if self.show_labels_checkbox.isChecked() else self.orig_pixmap
            self.screenshot_label.set_source_pixmap(display_pixmap)
            self.screenshot_layout.addWidget(self.screenshot_label)
        else:
            # No screenshot available
            vision_used = any(call.get("vision_enabled", True) for call in self.calls)
            if vision_used:
                message = "No screenshot available"
            else:
                message = "Screenshot not needed — vision is disabled for this step;\na text-based UI description was sent instead"
            no_screenshot_label = QLabel(message)
            no_screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_screenshot_label.setStyleSheet("color: #666; font-style: italic;")
            self.screenshot_layout.addWidget(no_screenshot_label)
            self.show_labels_checkbox.setEnabled(False)

        self.screenshot_layout.addStretch()
        return screenshot_group

    def _on_toggle_changed(self):
        """Handle element labels checkbox toggle."""
        if not self.orig_pixmap or not self.overlaid_pixmap:
            return

        if self.show_labels_checkbox.isChecked():
            pixmap = self.overlaid_pixmap
        else:
            pixmap = self.orig_pixmap

        self.screenshot_label.set_source_pixmap(pixmap)

    def _create_timing_group(self) -> QGroupBox | None:
        """Create a timing breakdown section from step phase metadata."""
        rows = self.timing_data.get("rows", [])
        retries = self.timing_data.get("validation_retries", [])
        if not rows and not retries:
            return None

        timing_group = QGroupBox("Timing Breakdown")
        timing_layout = QVBoxLayout(timing_group)

        if rows:
            table = QTableWidget(len(rows), 4)
            table.setHorizontalHeaderLabels(["Phase", "Metric", "Duration", "% Step"])
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
            total_ms = self.timing_data.get("total_step_duration_ms") or 0.0

            for row_idx, row in enumerate(rows):
                duration_ms = row.get("duration_ms") or 0.0
                pct = (duration_ms / total_ms * 100) if total_ms else 0.0
                values = [
                    row.get("phase", ""),
                    row.get("metric", ""),
                    f"{duration_ms:.0f} ms",
                    f"{pct:.0f}%",
                ]
                for col_idx, value in enumerate(values):
                    table.setItem(row_idx, col_idx, QTableWidgetItem(value))

            table.resizeColumnsToContents()
            timing_layout.addWidget(table)

        if retries:
            retry_text = QTextEdit()
            retry_text.setReadOnly(True)
            retry_text.setMaximumHeight(90)
            lines = []
            for retry in retries:
                attempt = retry.get("attempt")
                prefix = f"Attempt {attempt}: " if attempt is not None else ""
                lines.append(f"{prefix}{retry.get('reason', 'Validation retry')}")
            retry_text.setPlainText("\n".join(lines))
            timing_layout.addWidget(QLabel(f"Manager validation retries: {len(retries)}"))
            timing_layout.addWidget(retry_text)

        return timing_group


class AIMonitorPanel(QWidget):
    """Widget for monitoring AI interactions in real-time.

    A crawl step can involve multiple AI calls (e.g. Manager plan, then
    Executor action). Each call is tracked individually in `_calls` so none
    of them get overwritten, but the visible list shows exactly one row per
    step (`_interactions`, keyed by step_number) — its preview reflects the
    most relevant completed call for that step (the latest one with an
    actual parsed action, since that's "what the AI did").
    """

    show_step_details = Signal(int, datetime, bool, list, int, str, object)
    # step_number, timestamp, overall_success, calls, default_index, screenshot_path, timing_data

    def __init__(self, parent=None):
        """Initialize AI monitor panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._interactions = {}  # step_number -> aggregated row data
        self._calls = {}  # call_key -> single AI call's request/response data
        self._calls_by_step = {}  # step_number -> ordered list of call_keys
        self._pending_by_step = {}  # step_number -> list of call_keys awaiting a response
        self._call_seq = 0
        self._filter_state = {"status": "all", "search": ""}
        self._timing_provider = None
        self._setup_ui()

    def set_timing_provider(self, provider) -> None:
        """Set a callback returning phase transitions for (run_id, step_number)."""
        self._timing_provider = provider

    @Slot(int, int, str)
    def add_screenshot_path(self, run_id: int, step_number: int, screenshot_path: str):
        """Store screenshot path for a step.

        Args:
            run_id: Run ID
            step_number: Step number
            screenshot_path: Path to the captured screenshot
        """
        if step_number not in self._interactions:
            # Create base interaction if it doesn't exist yet
            self._interactions[step_number] = {
                "run_id": run_id,
                "step_number": step_number,
                "timestamp": datetime.now(),
                "request_data": {},
                "response_data": {},
                "success": False,
                "_response_updated": False
            }

        # Update path
        self._interactions[step_number]["screenshot_path"] = screenshot_path

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Group box for AI monitor
        monitor_group = QGroupBox("AI Monitor")
        monitor_layout = QVBoxLayout(monitor_group)

        # Controls row
        controls_layout = QHBoxLayout()

        # Status filter
        controls_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Success Only", "Failed Only"])
        self.status_filter.currentTextChanged.connect(self._on_status_filter_changed)
        controls_layout.addWidget(self.status_filter)

        # Search box
        controls_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search prompts/responses...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        controls_layout.addWidget(self.search_input)

        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._on_clear_clicked)
        controls_layout.addWidget(self.clear_button)

        controls_layout.addStretch()
        monitor_layout.addLayout(controls_layout)

        # Interactions list
        self.interactions_list = QListWidget()
        self.interactions_list.setMinimumHeight(400)
        monitor_layout.addWidget(self.interactions_list)

        layout.addWidget(monitor_group)

        # Search debounce timer
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._perform_search)

    @Slot(int, int, dict)
    def add_request(self, run_id: int, step_number: int, request_data: dict):
        """Add a pending AI request.

        A step may receive several of these (one per sub-agent call); each
        gets its own tracked call slot, but they render as a single list row.

        Args:
            run_id: Run ID
            step_number: Step number
            request_data: Request data dictionary
        """
        call_key = f"{step_number}:{self._call_seq}"
        self._call_seq += 1
        self._calls[call_key] = {
            "run_id": run_id,
            "timestamp": datetime.now(),
            "request_data": request_data,
            "response_data": None,
            "success": None,
            "error_message": None,
            "_response_updated": False,
        }
        self._calls_by_step.setdefault(step_number, []).append(call_key)
        self._pending_by_step.setdefault(step_number, []).append(call_key)

        self._recompute_step_aggregate(run_id, step_number)
        self._sync_list_item(step_number)

    @Slot(int, int, dict)
    def add_response(self, run_id: int, step_number: int, response_data: dict):
        """Complete an AI interaction with response data.

        Correlates to the oldest still-pending call for this step (the
        producer emits request→response synchronously per call, in order,
        so FIFO always resolves to the right one).

        Args:
            run_id: Run ID
            step_number: Step number
            response_data: Response data dictionary
        """
        pending_keys = self._pending_by_step.get(step_number)
        call_key = pending_keys.pop(0) if pending_keys else None

        if call_key is None or call_key not in self._calls:
            # Defensive: a response arrived without a tracked pending request.
            call_key = f"{step_number}:{self._call_seq}"
            self._call_seq += 1
            self._calls[call_key] = {
                "run_id": run_id,
                "timestamp": datetime.now(),
                "request_data": {},
                "response_data": None,
                "success": None,
                "error_message": None,
                "_response_updated": False,
            }
            self._calls_by_step.setdefault(step_number, []).append(call_key)

        call = self._calls[call_key]

        # Skip if already updated with full data and this is just a summary
        is_full = self._is_full_response(response_data)
        if call.get("_response_updated") and not is_full:
            return

        call["run_id"] = run_id
        call["response_data"] = response_data
        call["success"] = self._determine_success(response_data)
        call["error_message"] = response_data.get("error_message")
        if is_full:
            call["_response_updated"] = True

        self._recompute_step_aggregate(run_id, step_number)
        self._sync_list_item(step_number)

    def _recompute_step_aggregate(self, run_id: int, step_number: int) -> None:
        """Recompute the step's single list-row summary from all its calls so far.

        Preview prefers the latest completed call with an actual parsed
        action (Executor/FastAgent) over a plan-only call (Manager) — that's
        "what the AI did", which matters more than the raw plan. Overall
        success is the AND of every completed call for the step.
        """
        call_keys = self._calls_by_step.get(step_number, [])
        calls = [self._calls[k] for k in call_keys if k in self._calls]
        if not calls:
            return

        latest = calls[-1]
        pending = latest.get("response_data") is None
        completed = [c for c in calls if c.get("response_data") is not None]

        preview = None
        for c in reversed(completed):
            if _extract_parsed_actions(c.get("response_data") or {}):
                preview = c
                break
        if preview is None and completed:
            preview = completed[-1]

        success = all(c.get("success") for c in completed) if completed else False

        interaction = self._interactions.setdefault(
            step_number, {"step_number": step_number, "timestamp": calls[0]["timestamp"]}
        )
        interaction["run_id"] = run_id
        interaction["step_number"] = step_number
        interaction["request_data"] = latest.get("request_data") or {}
        interaction["response_data"] = preview.get("response_data") if preview else None
        interaction["success"] = success
        interaction["error_message"] = preview.get("error_message") if preview else None
        interaction["_pending"] = pending

    def _sync_list_item(self, step_number: int) -> None:
        """Append the step's row if it's new, otherwise refresh it in place."""
        interaction = self._interactions.get(step_number)
        if interaction is None:
            return
        if interaction.get("_list_item") is None:
            self._add_list_item(step_number)
        else:
            self._refresh_list_item(step_number)

    def _add_list_item(self, step_number: int):
        """Create the list item for a step from its current aggregated data.

        Args:
            step_number: Step number
        """
        interaction = self._interactions.get(step_number)
        if not interaction:
            return

        timestamp = interaction["timestamp"]
        pending = interaction.get("_pending", False)
        success = interaction.get("success", False) if not pending else False
        error_message = interaction.get("error_message")
        timing_data = self._get_timing_data(
            interaction.get("run_id"),
            step_number,
        )

        request_data = interaction.get("request_data") or {}
        response_data = interaction.get("response_data") or {}

        latency_ms = response_data.get("latency_ms")
        tokens_in = response_data.get("tokens_input")
        tokens_out = response_data.get("tokens_output")

        prompt_text = _extract_prompt_text(request_data)

        # Filter base64 from prompt preview
        prompt_preview_text = prompt_text
        try:
            prompt_data = json.loads(prompt_text)
            if isinstance(prompt_data, dict) and 'screenshot' in prompt_data:
                # Create preview without base64
                preview_parts = []
                for key, value in prompt_data.items():
                    if key == 'screenshot':
                        preview_parts.append(f"{key}: [Image]")
                    elif isinstance(value, (list, dict)):
                        preview_parts.append(f"{key}: {json.dumps(value)[:50]}...")
                    else:
                        preview_parts.append(f"{key}: {str(value)[:50]}")
                prompt_preview_text = " | ".join(preview_parts)
        except (json.JSONDecodeError, TypeError):
            pass

        parsed_actions = _extract_parsed_actions(response_data)
        full_response = _extract_response_text(response_data)

        # Create response preview
        response_preview_text = full_response
        if parsed_actions:
            # Use first action for preview
            action = parsed_actions[0]
            action_name = action.get('action', action.get('action_type', 'unknown'))
            reasoning = action.get('reasoning', '')
            response_preview_text = f"{action_name}: {reasoning}"

        # Create previews
        prompt_preview = prompt_preview_text[:100] + "..." if len(prompt_preview_text) > 100 else prompt_preview_text
        response_preview = response_preview_text[:100] + "..." if len(response_preview_text) > 100 else response_preview_text

        # Create custom widget
        item_widget = AIInteractionItem(
            step_number=step_number,
            timestamp=timestamp,
            success=success,
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            error_message=error_message,
            prompt_preview=prompt_preview,
            response_preview=response_preview,
            full_prompt=prompt_text,
            full_response=full_response,
            parsed_actions=parsed_actions,
            pending=pending,
            timing_summary=timing_data,
        )

        # Create list item
        list_item = QListWidgetItem()
        list_item.setSizeHint(item_widget.sizeHint())

        # Link widget to list item for size updates
        item_widget.list_item = list_item

        # Connect show details signal
        item_widget.show_details_requested.connect(lambda sn: self._on_show_details(sn))

        # Add to list
        self.interactions_list.addItem(list_item)
        self.interactions_list.setItemWidget(list_item, item_widget)

        # Auto-scroll to latest entry
        self.interactions_list.scrollToItem(list_item)

        # Store reference for updates
        interaction["_list_item"] = list_item
        interaction["_item_widget"] = item_widget

    def _is_full_response(self, response_data: dict) -> bool:
        """Check if response_data contains full AI response (not just summary)."""
        return (
            "parsed_response" in response_data or
            "raw_response" in response_data or
            "response" in response_data
        )

    def _determine_success(self, response_data: dict) -> bool:
        """Determine if AI response was successful."""
        if isinstance(response_data.get("success"), bool):
            return response_data["success"]

        # Has error? -> Failed
        if response_data.get("error_message"):
            return False

        # Has parsed actions? -> Success
        if "parsed_response" in response_data:
            try:
                parsed = json.loads(response_data["parsed_response"])
                if "actions" in parsed and len(parsed["actions"]) > 0:
                    return True
            except (json.JSONDecodeError, TypeError):
                pass

        # Has actions count > 0? -> Success
        if response_data.get("actions_count", 0) > 0:
            return True

        # Default to False
        return False

    def _refresh_list_item(self, step_number: int):
        """Remove and re-add the list item for a step from its current aggregated data.

        Args:
            step_number: Step number
        """
        interaction = self._interactions.get(step_number)
        if not interaction:
            return

        # Remove old list item if it exists
        old_list_item = interaction.get("_list_item")
        old_widget = interaction.get("_item_widget")

        if old_list_item:
            row = self.interactions_list.row(old_list_item)
            if row >= 0:
                # Remove widget first, then item
                self.interactions_list.removeItemWidget(old_list_item)
                self.interactions_list.takeItem(row)
            # Clear references
            interaction["_list_item"] = None
            interaction["_item_widget"] = None
            if old_widget:
                old_widget.deleteLater()

        # Add updated item
        self._add_list_item(step_number)

    def _on_status_filter_changed(self, status_text: str):
        """Handle status filter change.

        Args:
            status_text: Selected status filter
        """
        status_map = {
            "All": "all",
            "Success Only": "success",
            "Failed Only": "failed"
        }
        self._filter_state["status"] = status_map.get(status_text, "all")
        self._apply_filters()

    def _on_search_text_changed(self, text: str):
        """Handle search text change with debouncing.

        Args:
            text: Search text
        """
        self._filter_state["search"] = text
        self._search_timer.stop()
        self._search_timer.start(300)  # 300ms debounce

    def _perform_search(self):
        """Apply search filter after debounce."""
        self._apply_filters()

    def _apply_filters(self):
        """Apply current filters to visible items."""
        status_filter = self._filter_state["status"]
        search_text = self._filter_state["search"].lower()

        for _step_number, interaction in self._interactions.items():
            if "_list_item" not in interaction:
                continue

            list_item = interaction["_list_item"]
            visible = True

            # Status filter
            if status_filter != "all":
                success = interaction.get("success", False)
                if status_filter == "success" and not success:
                    visible = False
                elif status_filter == "failed" and success:
                    visible = False

            # Search filter
            if visible and search_text:
                request_data = interaction.get("request_data", {})
                response_data = interaction.get("response_data", {})

                search_content = ""
                if "user_prompt" in request_data:
                    search_content += request_data["user_prompt"]
                if "response" in response_data:
                    search_content += response_data["response"]

                if search_text not in search_content.lower():
                    visible = False

            list_item.setHidden(not visible)

    def _on_clear_clicked(self):
        """Handle clear button click."""
        self._interactions.clear()
        self._calls.clear()
        self._calls_by_step.clear()
        self._pending_by_step.clear()
        self._call_seq = 0
        self.interactions_list.clear()
        self._filter_state = {"status": "all", "search": ""}
        self.status_filter.setCurrentText("All")
        self.search_input.clear()

    def clear(self):
        """Clear all interactions."""
        self._on_clear_clicked()

    def _on_show_details(self, step_number: int):
        """Handle show details request for a step.

        Gathers every AI call made for this step (not just one), so the
        detail dialog can present all of them (e.g. Manager's plan and the
        Executor's action) rather than only the last one.

        Args:
            step_number: Step number to show details for
        """
        call_keys = self._calls_by_step.get(step_number, [])
        if not call_keys:
            return

        label_counts: dict[str, int] = {}
        calls_payload = []
        for key in call_keys:
            call = self._calls.get(key)
            if not call:
                continue
            request_data = call.get("request_data") or {}
            response_data = call.get("response_data") or {}
            parsed_actions = _extract_parsed_actions(response_data)

            base_label = "Action" if parsed_actions else "Plan"
            label_counts[base_label] = label_counts.get(base_label, 0) + 1
            count = label_counts[base_label]
            label = base_label if count == 1 else f"{base_label} {count}"

            calls_payload.append({
                "label": label,
                "success": call.get("success", False),
                "error_message": call.get("error_message"),
                "prompt_text": _extract_prompt_text(request_data),
                "response_text": _extract_response_text(response_data),
                "parsed_actions": parsed_actions,
                "vision_enabled": response_data.get("vision_enabled", True),
                "ui_elements": request_data.get("ui_elements"),
                "status_bar_exclusion_px": request_data.get("status_bar_exclusion_px", 0),
            })

        if not calls_payload:
            return

        # Default to the last call with an actual parsed action (that's the
        # one the viewer cares about first); fall back to the last call.
        default_index = len(calls_payload) - 1
        for i in range(len(calls_payload) - 1, -1, -1):
            if calls_payload[i]["parsed_actions"]:
                default_index = i
                break

        interaction = self._interactions.get(step_number, {})
        overall_success = interaction.get("success", False)
        timestamp = interaction.get("timestamp", datetime.now())

        self.show_step_details.emit(
            step_number,
            timestamp,
            overall_success,
            calls_payload,
            default_index,
            interaction.get("screenshot_path"),
            self._get_timing_data(interaction.get("run_id"), step_number),
        )

    def _get_timing_data(self, run_id: int | None, step_number: int) -> dict:
        if not run_id or not self._timing_provider:
            return {}
        try:
            transitions = self._timing_provider(run_id, step_number) or []
        except Exception:
            return {}
        return _build_timing_breakdown(transitions)


def _build_timing_breakdown(transitions) -> dict:
    """Build UI timing rows from StepPhaseTransition-like objects."""
    rows = []
    validation_retries = []
    total_step_duration_ms = 0.0

    for transition in transitions:
        phase = getattr(transition, "from_phase", "")
        duration_ms = getattr(transition, "duration_ms", None)
        if duration_ms is not None:
            duration_ms = float(duration_ms)
            total_step_duration_ms += duration_ms
            rows.append(
                {
                    "phase": phase,
                    "metric": "phase total",
                    "duration_ms": duration_ms,
                }
            )

        metadata_json = getattr(transition, "metadata_json", None)
        if not metadata_json:
            continue
        try:
            metadata = json.loads(metadata_json)
        except (json.JSONDecodeError, TypeError):
            continue

        for metric, sub_duration_ms in (metadata.get("sub_phases") or {}).items():
            rows.append(
                {
                    "phase": phase,
                    "metric": metric,
                    "duration_ms": float(sub_duration_ms),
                }
            )

        validation_retries.extend(metadata.get("validation_retries") or [])

    return {
        "rows": rows,
        "validation_retries": validation_retries,
        "total_step_duration_ms": total_step_duration_ms or None,
    }
