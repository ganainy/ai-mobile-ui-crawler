"""AI Monitor Panel widget for displaying AI interactions in real-time."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QLabel,
    QTextEdit,
    QPushButton,
    QComboBox,
    QLineEdit,
    QScrollArea,
    QTabWidget,
    QRadioButton,
    QButtonGroup
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QColor, QPixmap, QPainter, QPen, QFont
from typing import Dict, Any, Optional, List
import json
import base64
import os
from datetime import datetime
from .json_tree_widget import JsonTreeWidget


class AIInteractionItem(QWidget):
    """Custom widget for displaying a single AI interaction in the list."""

    show_details_requested = Signal(int)  # Emits step_number

    def __init__(self, step_number: int, timestamp: datetime, success: bool,
                 latency_ms: Optional[float], tokens_in: Optional[int],
                 tokens_out: Optional[int], error_message: Optional[str],
                 prompt_preview: str, response_preview: str,
                 full_prompt: str, full_response: str,
                 parsed_actions: List[dict], pending: bool = False, parent=None):
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
        if self.latency_ms is not None:
            metrics_parts.append(f"{self.latency_ms/1000:.1f}s")
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



class StepDetailWidget(QWidget):
    """Widget for displaying detailed step information in a tab."""

    def __init__(self, step_number: int, timestamp: datetime, success: bool,
                 full_prompt: str, full_response: str, parsed_actions: List[dict],
                 error_message: Optional[str] = None, screenshot_path: Optional[str] = None, parent=None):
        """Initialize step detail widget.

        Args:
            step_number: Step number
            timestamp: When interaction occurred
            success: Whether interaction succeeded
            full_prompt: Complete prompt text
            full_response: Complete response text
            parsed_actions: Parsed action details
            error_message: Error message if failed
            screenshot_path: Optional path to screenshot file
            parent: Parent widget
        """
        super().__init__(parent)
        self.step_number = step_number
        self.timestamp = timestamp
        self.success = success
        self.full_prompt = full_prompt
        self.full_response = full_response
        self.parsed_actions = parsed_actions
        self.error_message = error_message
        self.screenshot_path = screenshot_path
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

        # Try to extract screenshot for display, but keep rest of prompt data for JsonTreeWidget
        screenshot_pixmap = None
        prompt_json_data = self.full_prompt

        try:
            prompt_data = json.loads(self.full_prompt)
            if isinstance(prompt_data, dict):
                # Handle nested structure from AIInteractionService
                # request_data = {"system_prompt": "...", "user_prompt": "{json string}"}
                actual_prompt_data = prompt_data
                if 'user_prompt' in prompt_data:
                    # Parse the nested user_prompt JSON string
                    try:
                        actual_prompt_data = json.loads(prompt_data['user_prompt'])
                    except (json.JSONDecodeError, TypeError):
                        actual_prompt_data = prompt_data
                
                # Extract screenshot if present
                screenshot_b64 = actual_prompt_data.get('screenshot', '')
                if screenshot_b64 and len(screenshot_b64) > 100:
                    try:
                        if screenshot_b64.startswith('data:image'):
                            screenshot_b64 = screenshot_b64.split(',', 1)[1]
                        image_data = base64.b64decode(screenshot_b64)
                        pixmap = QPixmap()
                        if pixmap.loadFromData(image_data):
                            screenshot_pixmap = pixmap
                    except Exception:
                        pass
                
                # Create a version of data without the huge base64 screenshot for the tree view
                prompt_json_data = actual_prompt_data.copy() if isinstance(actual_prompt_data, dict) else actual_prompt_data
                if isinstance(prompt_json_data, dict) and 'screenshot' in prompt_json_data:
                    prompt_json_data['screenshot'] = "[Image displayed on left]"
        except (json.JSONDecodeError, TypeError):
            # Not JSON, handle large base64 if needed
            if len(self.full_prompt) > 1000 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in self.full_prompt.replace('\n', '').replace('\r', '').replace(' ', '')):
                prompt_json_data = "[Large base64 data - not displayed]"

        # TOP ROW: Screenshot (1/3) + Prompt Data (2/3)
        top_row_layout = QHBoxLayout()
        
        # Screenshot section (1/3 width)
        screenshot_group = QGroupBox("Screenshot")
        self.screenshot_layout = QVBoxLayout(screenshot_group)
        
        # Add toggle buttons
        toggle_layout = QHBoxLayout()
        self.annotated_radio = QRadioButton("Annotated")
        self.ocr_radio = QRadioButton("OCR")
        self.annotated_radio.setChecked(True)
        
        self.toggle_group = QButtonGroup(self)
        self.toggle_group.addButton(self.annotated_radio)
        self.toggle_group.addButton(self.ocr_radio)
        self.toggle_group.buttonClicked.connect(self._on_toggle_changed)
        
        toggle_layout.addWidget(self.annotated_radio)
        toggle_layout.addWidget(self.ocr_radio)
        toggle_layout.addStretch()
        self.screenshot_layout.addLayout(toggle_layout)

        # Store pixmaps for toggling
        self.orig_pixmap = None
        self.annotated_pixmap = None
        self.ocr_pixmap = None

        # Load screenshot - prioritize file path if available
        if self.screenshot_path and os.path.exists(self.screenshot_path):
            pixmap = QPixmap(self.screenshot_path)
            if not pixmap.isNull():
                screenshot_pixmap = pixmap

        if screenshot_pixmap:
            self.orig_pixmap = screenshot_pixmap
            
            # Load images from disk if available to avoid re-implementing drawing logic
            # Annotated view (Actions)
            if self.screenshot_path:
                base, ext = os.path.splitext(self.screenshot_path)
                
                # 1. Annotated Actions
                annotated_path = f"{base}_annotated{ext}"
                if os.path.exists(annotated_path):
                    pixmap = QPixmap(annotated_path)
                    if not pixmap.isNull():
                        self.annotated_pixmap = pixmap
                
                # 2. Grounded OCR
                grounded_path = f"{base}_grounded{ext}"
                if os.path.exists(grounded_path):
                    pixmap = QPixmap(grounded_path)
                    if not pixmap.isNull():
                        self.ocr_pixmap = pixmap

            # Fallbacks for runtime reliability
            if not self.annotated_pixmap:
                self.annotated_pixmap = screenshot_pixmap
            if not self.ocr_pixmap:
                self.ocr_pixmap = screenshot_pixmap
            
            self.screenshot_label = QLabel()
            # Initial display: Annotated
            scaled_pixmap = self.annotated_pixmap.scaledToWidth(200, Qt.TransformationMode.SmoothTransformation)
            self.screenshot_label.setPixmap(scaled_pixmap)
            self.screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.screenshot_layout.addWidget(self.screenshot_label)
        else:
            no_screenshot_label = QLabel("No screenshot available")
            no_screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_screenshot_label.setStyleSheet("color: #666; font-style: italic;")
            self.screenshot_layout.addWidget(no_screenshot_label)
            self.annotated_radio.setEnabled(False)
            self.ocr_radio.setEnabled(False)
            
        self.screenshot_layout.addStretch()
        top_row_layout.addWidget(screenshot_group, 1)  # 1/3 stretch factor

        # Prompt Data section (2/3 width)
        prompt_group = QGroupBox("Prompt Data")
        prompt_layout = QVBoxLayout(prompt_group)
        self.prompt_tree = JsonTreeWidget(prompt_json_data)
        prompt_layout.addWidget(self.prompt_tree)
        top_row_layout.addWidget(prompt_group, 2)  # 2/3 stretch factor

        scroll_layout.addLayout(top_row_layout)

        # BOTTOM ROW: Response (1/2) + Parsed Actions (1/2)
        bottom_row_layout = QHBoxLayout()

        # Response section (1/2 width)
        response_group = QGroupBox("Response")
        response_layout = QVBoxLayout(response_group)
        self.response_tree = JsonTreeWidget(self.full_response)
        response_layout.addWidget(self.response_tree)
        bottom_row_layout.addWidget(response_group, 1)

        # Actions section (1/2 width)
        if self.parsed_actions:
            actions_group = QGroupBox("Parsed Actions")
            actions_layout = QVBoxLayout(actions_group)
            actions_text = ""
            for action in self.parsed_actions:
                actions_text += f"• Action: {action.get('action', 'unknown')}\n"
                if 'action_desc' in action:
                    actions_text += f"  Description: {action['action_desc']}\n"
                
                # Check for label_id OR target_bounding_box
                label_id = action.get('label_id')
                bbox = action.get('target_bounding_box')
                
                if label_id is not None:
                    actions_text += f"  Label ID: {label_id}\n"
                elif bbox:
                    # Sanity check for bbox content
                    tl = bbox.get('top_left')
                    br = bbox.get('bottom_right')
                    if tl and br and len(tl) >= 2 and len(br) >= 2:
                        actions_text += f"  Target: [{tl[0]}, {tl[1]}] → [{br[0]}, {br[1]}]\n"
                    else:
                        actions_text += f"  Target: {bbox}\n"
                
                if 'input_text' in action and action['input_text']:
                    actions_text += f"  Input: {action['input_text']}\n"
                if 'reasoning' in action:
                    actions_text += f"  Reasoning: {action['reasoning']}\n"
                actions_text += "\n"


            actions_display = QTextEdit()
            actions_display.setPlainText(actions_text.strip())
            actions_display.setReadOnly(True)
            actions_layout.addWidget(actions_display)
            bottom_row_layout.addWidget(actions_group, 1)
        else:
            # Empty placeholder if no actions
            no_actions_group = QGroupBox("Parsed Actions")
            no_actions_layout = QVBoxLayout(no_actions_group)
            no_actions_label = QLabel("No parsed actions available")
            no_actions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_actions_label.setStyleSheet("color: #666; font-style: italic;")
            no_actions_layout.addWidget(no_actions_label)
            bottom_row_layout.addWidget(no_actions_group, 1)

        scroll_layout.addLayout(bottom_row_layout)

        # Error message (if any)
        if self.error_message:
            error_group = QGroupBox("Error")
            error_layout = QVBoxLayout(error_group)
            error_text = QTextEdit()
            error_text.setPlainText(self.error_message)
            error_text.setReadOnly(True)
            error_text.setStyleSheet("color: red;")
            error_layout.addWidget(error_text)
            scroll_layout.addWidget(error_group)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def _on_toggle_changed(self, button):
        """Handle screenshot viewer toggle change."""
        if not self.orig_pixmap:
            return
            
        if button == self.annotated_radio:
            pixmap = self.annotated_pixmap
        else:
            pixmap = self.ocr_pixmap
            
        if pixmap:
            scaled_pixmap = pixmap.scaledToWidth(200, Qt.TransformationMode.SmoothTransformation)
            self.screenshot_label.setPixmap(scaled_pixmap)


class AIMonitorPanel(QWidget):
    """Widget for monitoring AI interactions in real-time."""

    show_step_details = Signal(int, datetime, bool, str, str, list, object, str)  # step_number, timestamp, success, prompt, response, actions, error_msg, screenshot_path

    def __init__(self, parent=None):
        """Initialize AI monitor panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._interactions = {}  # step_number -> interaction data
        self._filter_state = {"status": "all", "search": ""}
        self._setup_ui()
    
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

        Args:
            run_id: Run ID
            step_number: Step number
            request_data: Request data dictionary
        """
        # Initialize or update existing entry (to preserve screenshot_path if already set)
        if step_number not in self._interactions:
            self._interactions[step_number] = {
                "run_id": run_id,
                "step_number": step_number,
                "timestamp": datetime.now(),
                "response_data": None,
                "success": None,
                "error_message": None,
                "_response_updated": False
            }
        
        # Update request data and ensure basic fields are set
        interaction = self._interactions[step_number]
        interaction["run_id"] = run_id
        interaction["request_data"] = request_data
        
        # If timestamp was just a placeholder, update it to actual request time
        if "timestamp" not in interaction:
            interaction["timestamp"] = datetime.now()

        # Create pending list item
        self._add_list_item(step_number, pending=True)

    @Slot(int, int, dict)
    def add_response(self, run_id: int, step_number: int, response_data: dict):
        """Complete an AI interaction with response data.

        Args:
            run_id: Run ID
            step_number: Step number
            response_data: Response data dictionary
        """
        if step_number not in self._interactions:
            return

        interaction = self._interactions[step_number]
        
        # Skip if already updated with full data and this is just a summary
        is_full = self._is_full_response(response_data)
        if interaction.get("_response_updated") and not is_full:
            return
            
        # Update interaction with response
        interaction["response_data"] = response_data
        interaction["success"] = self._determine_success(response_data)
        interaction["error_message"] = response_data.get("error_message")
        
        if is_full:
            interaction["_response_updated"] = True

        # Update or replace list item
        self._update_list_item(step_number)

    def _add_list_item(self, step_number: int, pending: bool = False):
        """Add or update list item for step.

        Args:
            step_number: Step number
            pending: Whether this is a pending request
        """
        interaction = self._interactions.get(step_number)
        if not interaction:
            return

        # Create item data
        timestamp = interaction["timestamp"]
        success = interaction.get("success", False) if not pending else False
        latency_ms = interaction.get("latency_ms")
        tokens_in = interaction.get("tokens_input")
        tokens_out = interaction.get("tokens_output")
        error_message = interaction.get("error_message")

        # Extract prompt and response previews
        request_data = interaction.get("request_data") or {}
        response_data = interaction.get("response_data") or {}

        prompt_text = ""
        if "user_prompt" in request_data:
            prompt_text = request_data["user_prompt"]
        elif "prompt" in request_data:
            prompt_text = request_data["prompt"]

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

        # Parse actions if available
        parsed_actions = []
        if "actions" in response_data:
            parsed_actions = response_data["actions"]
        elif "parsed_response" in response_data:
            try:
                parsed = json.loads(response_data["parsed_response"])
                if isinstance(parsed, dict) and "actions" in parsed:
                    parsed_actions = parsed["actions"]
                elif isinstance(parsed, list):
                    parsed_actions = parsed
            except (json.JSONDecodeError, KeyError):
                pass

        # Extract full response text
        full_response = ""
        if "response" in response_data:
            full_response = response_data["response"]
        elif "raw_response" in response_data:
            full_response = response_data["raw_response"]
        elif "parsed_response" in response_data:
            full_response = response_data["parsed_response"]

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
            pending=pending
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

    def _update_list_item(self, step_number: int):
        """Update existing list item with response data.

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

        # Add updated item (not pending anymore)
        self._add_list_item(step_number, pending=False)

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

        for step_number, interaction in self._interactions.items():
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
        self.interactions_list.clear()
        self._filter_state = {"status": "all", "search": ""}
        self.status_filter.setCurrentText("All")
        self.search_input.clear()

    def clear(self):
        """Clear all interactions."""
        self._on_clear_clicked()

    def _on_show_details(self, step_number: int):
        """Handle show details request for a step.

        Args:
            step_number: Step number to show details for
        """
        interaction = self._interactions.get(step_number)
        if not interaction:
            return

        # Extract all data needed for detail view
        timestamp = interaction["timestamp"]
        success = interaction.get("success", False)
        error_message = interaction.get("error_message")

        request_data = interaction.get("request_data") or {}
        response_data = interaction.get("response_data") or {}

        prompt_text = ""
        if "user_prompt" in request_data:
            prompt_text = request_data["user_prompt"]
        elif "prompt" in request_data:
            prompt_text = request_data["prompt"]

        response_text = ""
        if "response" in response_data:
            response_text = response_data["response"]
        elif "raw_response" in response_data:
            response_text = response_data["raw_response"]
        elif "parsed_response" in response_data:
            response_text = response_data["parsed_response"]

        # Parse actions if available
        parsed_actions = []
        if "actions" in response_data:
            parsed_actions = response_data["actions"]
        elif "parsed_response" in response_data:
            try:
                parsed = json.loads(response_data["parsed_response"])
                if isinstance(parsed, dict) and "actions" in parsed:
                    parsed_actions = parsed["actions"]
                elif isinstance(parsed, list):
                    parsed_actions = parsed
            except (json.JSONDecodeError, KeyError):
                pass

        # Emit signal with all data
        self.show_step_details.emit(
            step_number,
            timestamp,
            success,
            prompt_text,
            response_text,
            parsed_actions,
            error_message,
            interaction.get("screenshot_path")
        )