# ui/components.py - UI components for the Appium Crawler Controller

import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.custom_widgets import NoScrollComboBox as QComboBox
from ui.custom_widgets import NoScrollSpinBox as QSpinBox
from ui.custom_widgets import CollapsibleBox, SearchableComboBox


class ComponentFactory:
    """Factory class for creating UI components used in the Crawler Controller."""



    @staticmethod
    def create_appium_settings_group(
        layout: QFormLayout,
        config_widgets: Dict[str, Any],
        tooltips: Dict[str, str],
        controls_handler: Any,
    ) -> QWidget:
        """Create the Appium settings group."""
        appium_group = CollapsibleBox("Appium Settings")
        appium_layout = QFormLayout()
        appium_group.content_layout.addLayout(appium_layout)

        config_widgets["APPIUM_SERVER_URL"] = QLabel()
        label_appium_url = QLabel("Server URL:")
        from config.urls import ServiceURLs
        from ui.strings import APPIUM_URL_TOOLTIP
        label_appium_url.setToolTip(tooltips.get("APPIUM_SERVER_URL", APPIUM_URL_TOOLTIP.format(url=ServiceURLs.APPIUM)))
        appium_layout.addRow(label_appium_url, config_widgets["APPIUM_SERVER_URL"])

        config_widgets["TARGET_DEVICE_UDID"] = QComboBox()
        label_device_udid = QLabel("Target Device UDID:")
        label_device_udid.setToolTip(tooltips["TARGET_DEVICE_UDID"])

        device_layout = QHBoxLayout()
        device_layout.addWidget(config_widgets["TARGET_DEVICE_UDID"])
        refresh_devices_btn = QPushButton("Refresh")
        controls_handler.refresh_devices_btn = refresh_devices_btn
        device_layout.addWidget(refresh_devices_btn)
        appium_layout.addRow(label_device_udid, device_layout)

        layout.addRow(appium_group)
        return appium_group

    @staticmethod
    def create_app_settings_group(
        layout: QFormLayout,
        config_widgets: Dict[str, Any],
        tooltips: Dict[str, str],
        config_handler: Any,
    ) -> QWidget:
        """Create the App settings group with health app selection."""
        app_group = CollapsibleBox("App Settings")
        app_layout = QFormLayout()
        app_group.content_layout.addLayout(app_layout)

        # Health App Selector with Discovery Filter checkbox
        # Use SearchableComboBox for type-to-search capability
        config_handler.health_app_dropdown = SearchableComboBox(
            placeholder_text="Type to search apps..."
        )
        config_handler.health_app_dropdown.addItem(
            "Select target app (Scan first)", None
        )
        config_handler.health_app_dropdown.currentIndexChanged.connect(
            config_handler._on_health_app_selected
        )
        config_handler.health_app_dropdown.setToolTip(
            "Select a health-related app discovered on the device. Type to search or use button below to scan."
        )

        # Create a horizontal layout for dropdown and discovery filter checkbox
        health_app_layout = QHBoxLayout()
        health_app_layout.addWidget(config_handler.health_app_dropdown)
        
        # Health-only filter toggle (AI)
        # This controls whether the discovery script applies AI filtering to only show health-related apps
        config_widgets["USE_AI_FILTER_FOR_TARGET_APP_DISCOVERY"] = QCheckBox("Health-only filter (AI)")
        config_widgets["USE_AI_FILTER_FOR_TARGET_APP_DISCOVERY"].setToolTip(
            "If enabled, the scanner uses AI to keep only health-related apps (fitness, wellness, medical, medication, mental health)."
        )
        health_app_layout.addWidget(config_widgets["USE_AI_FILTER_FOR_TARGET_APP_DISCOVERY"])
        
        app_layout.addRow(
            QLabel("Target Health App:"), health_app_layout
        )

        config_handler.refresh_apps_btn = QPushButton("Scan/Refresh Health Apps List")
        config_handler.refresh_apps_btn.setToolTip(
            "Scans the connected device for installed applications and filters for health-related ones using AI."
        )
        app_layout.addRow(config_handler.refresh_apps_btn)

        config_handler.app_scan_status_label = QLabel("App Scan: Idle")
        app_layout.addRow(QLabel("Scan Status:"), config_handler.app_scan_status_label)

        layout.addRow(app_group)
        return app_group

    @staticmethod
    def create_ai_settings_group(
        layout: QFormLayout,
        config_widgets: Dict[str, Any],
        tooltips: Dict[str, str],
        config_handler: Any = None,
    ) -> QWidget:
        """Create the AI settings group."""
        ai_group = CollapsibleBox("AI Settings")
        ai_layout = QFormLayout()
        ai_group.content_layout.addLayout(ai_layout)

        # AI Provider Selection
        config_widgets["AI_PROVIDER"] = QComboBox()
        # Use provider registry to get all available providers
        from domain.providers.registry import ProviderRegistry
        provider_names = ProviderRegistry.get_all_names()
        config_widgets["AI_PROVIDER"].addItems(provider_names)
        label_ai_provider = QLabel("AI Provider: ")
        label_ai_provider.setToolTip(
            "The AI model provider to use for analysis and decision making."
        )
        ai_layout.addRow(label_ai_provider, config_widgets["AI_PROVIDER"])

        # Create refresh button for models (visible for all providers)
        config_widgets["OPENROUTER_REFRESH_BTN"] = QPushButton("Refresh models")
        config_widgets["OPENROUTER_REFRESH_BTN"].setToolTip(
            "Fetch latest models from the selected AI provider"
        )
        config_widgets["OPENROUTER_REFRESH_BTN"].setVisible(True)

        config_widgets["DEFAULT_MODEL_TYPE"] = QComboBox()
        # Start with explicit no-selection placeholder; provider change will populate
        try:
            from ui.strings import NO_MODEL_SELECTED
            config_widgets["DEFAULT_MODEL_TYPE"].addItem(NO_MODEL_SELECTED)
        except Exception:
            from ui.strings import NO_MODEL_SELECTED
            config_widgets["DEFAULT_MODEL_TYPE"].addItems([NO_MODEL_SELECTED])
        label_model_type = QLabel("Default Model Type: ")
        label_model_type.setToolTip(tooltips["DEFAULT_MODEL_TYPE"])
        # Row 1: Model Dropdown
        ai_layout.addRow(label_model_type, config_widgets["DEFAULT_MODEL_TYPE"])
        
        # Free-only filter (visible for all providers)
        config_widgets["OPENROUTER_SHOW_FREE_ONLY"] = QCheckBox("Free only")
        config_widgets["OPENROUTER_SHOW_FREE_ONLY"].setToolTip(
            "Show only models with free pricing (0 cost)."
        )
        config_widgets["OPENROUTER_SHOW_FREE_ONLY"].setVisible(True)
        
        # Vision-only filter (visible for all providers)
        config_widgets["SHOW_VISION_ONLY"] = QCheckBox("Vision only")
        config_widgets["SHOW_VISION_ONLY"].setToolTip(
            "Show only models that support image/vision inputs."
        )
        config_widgets["SHOW_VISION_ONLY"].setVisible(True)
        
        # Row 2: Controls (Refresh + Filters) - grouped in a horizontal layout
        _controls_row_layout = QHBoxLayout()
        _controls_row_layout.addWidget(config_widgets["OPENROUTER_REFRESH_BTN"])
        _controls_row_layout.addWidget(config_widgets["OPENROUTER_SHOW_FREE_ONLY"])
        _controls_row_layout.addWidget(config_widgets["SHOW_VISION_ONLY"])
        _controls_row_layout.addStretch() # Push to left
        
        # indented under the field column
        ai_layout.addRow("", _controls_row_layout)

        # Connect the AI provider selection to update model types
        # Note: These connections will be set up in CrawlerControllerWindow after UIStateHandler is created
        # The callbacks will be connected to UIStateHandler methods
        pass

        # Advanced manual model id entry removed; use dropdown-only selection

        # Enable Image Context has been moved to Image Preprocessing section



        # Crawler Available Actions (checkable list, managed via CLI: actions list/add/edit/remove)
        from ui.available_actions_widget import AvailableActionsWidget
        # Get actions service for the widget
        actions_service = None
        if config_handler:
            try:
                actions_service = config_handler._get_actions_service()
            except Exception as e:
                pass
        
        config_widgets["CRAWLER_AVAILABLE_ACTIONS"] = AvailableActionsWidget(
            actions_service=actions_service,
            parent=ai_group
        )
        label_available_actions = QLabel("Available Actions: ")
        available_actions_tooltip = (
            "Select which actions the crawler can use. "
            "Unchecked actions will be disabled for the AI model. "
            "Manage actions via CLI: 'python run_cli.py actions list/add/edit/remove'. "
            "Only enabled actions will be shown to the AI model."
        )
        label_available_actions.setToolTip(available_actions_tooltip)
        config_widgets["CRAWLER_AVAILABLE_ACTIONS"].setToolTip(available_actions_tooltip)
        ai_layout.addRow(label_available_actions, config_widgets["CRAWLER_AVAILABLE_ACTIONS"])
        
        # Prompt layout with Reset button
        prompt_container = QWidget()
        prompt_sub_layout = QVBoxLayout(prompt_container)
        prompt_sub_layout.setContentsMargins(0, 0, 0, 0)
        
        config_widgets["CRAWLER_ACTION_DECISION_PROMPT"] = QTextEdit()
        config_widgets["CRAWLER_ACTION_DECISION_PROMPT"].setMinimumHeight(120)
        config_widgets["CRAWLER_ACTION_DECISION_PROMPT"].setMaximumHeight(180)
        config_widgets["CRAWLER_ACTION_DECISION_PROMPT"].setReadOnly(False)
        config_widgets["CRAWLER_ACTION_DECISION_PROMPT"].setStyleSheet("""
            QTextEdit {
                background-color: #333333;
                color: #FFFFFF;
                border: 1px solid #555555;
            }
        """)
        prompt_sub_layout.addWidget(config_widgets["CRAWLER_ACTION_DECISION_PROMPT"])
        
        reset_prompt_btn = QPushButton("Reset to Default")
        reset_prompt_btn.setFixedWidth(120)
        reset_prompt_btn.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: #FFFFFF;
                border: 1px solid #555555;
                padding: 4px;
                font-size: 8pt;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        config_widgets["RESET_ACTION_DECISION_PROMPT_BTN"] = reset_prompt_btn
        prompt_sub_layout.addWidget(reset_prompt_btn, 0, Qt.AlignmentFlag.AlignRight)
        
        label_action_prompt = QLabel("Action Decision Prompt: ")
        action_prompt_tooltip = (
            "Custom instructions for the AI agent (editable). "
            "The JSON schema and available actions list are automatically appended by the system. "
            "Editable in UI or via CLI: 'python run_cli.py prompts list/add/edit/remove'. "
            "Name: ACTION_DECISION_PROMPT. Changes are saved to SQLite database."
        )
        label_action_prompt.setToolTip(action_prompt_tooltip)
        config_widgets["CRAWLER_ACTION_DECISION_PROMPT"].setToolTip(action_prompt_tooltip)
        ai_layout.addRow(label_action_prompt, prompt_container)



        layout.addRow(ai_group)
        return ai_group

    @staticmethod
    def create_image_preprocessing_group(
        layout: QFormLayout,
        config_widgets: Dict[str, Any],
        tooltips: Dict[str, str],
    ) -> QWidget:
        """Create the Image Preprocessing settings group."""
        from PySide6.QtWidgets import QHBoxLayout
        from ui.strings import IMAGE_CONTEXT_ENABLED_TOOLTIP
        
        group = CollapsibleBox("Image Preprocessing")
        form = QFormLayout()
        group.content_layout.addLayout(form)

        # Context Sources - HYBRID (XML+OCR) is always enabled, IMAGE is optional
        # Info label about HYBRID
        hybrid_info = QLabel("XML + OCR context always enabled")
        hybrid_info.setToolTip("HYBRID context provides both element hierarchy (XML) and visible text (OCR) for reliable element targeting.")
        hybrid_info.setStyleSheet("color: #888; font-style: italic;")
        
        # XML Snippet Length (still configurable)
        from config.numeric_constants import XML_SNIPPET_MAX_LEN_MIN, XML_SNIPPET_MAX_LEN_MAX
        config_widgets["XML_SNIPPET_MAX_LEN"] = QSpinBox()
        config_widgets["XML_SNIPPET_MAX_LEN"].setRange(XML_SNIPPET_MAX_LEN_MIN, XML_SNIPPET_MAX_LEN_MAX)
        config_widgets["XML_SNIPPET_MAX_LEN"].setToolTip(tooltips.get("XML_SNIPPET_MAX_LEN", "Max characters for XML snippet"))
        config_widgets["XML_SNIPPET_MAX_LEN"].setFixedWidth(80)
        
        label_xml_len = QLabel("XML Max Len:")
        label_xml_len.setToolTip(tooltips.get("XML_SNIPPET_MAX_LEN", "Max characters for XML snippet"))
        
        # Image Source - optional toggle
        config_widgets["CONTEXT_SOURCE_IMAGE"] = QCheckBox("Enable Image Context")
        config_widgets["CONTEXT_SOURCE_IMAGE"].setToolTip("Include screenshots in the AI context (for vision-capable models like Gemini Pro Vision).")

        # Warning label (always shown with fixed message)
        config_widgets["IMAGE_CONTEXT_WARNING"] = QLabel("⚠️ No images will be sent if selected model doesn't support images")
        config_widgets["IMAGE_CONTEXT_WARNING"].setStyleSheet(
            "color: #ff6b35; font-weight: bold; font-size: 9pt;"
        )
        config_widgets["IMAGE_CONTEXT_WARNING"].setToolTip(
            "The checkbox can be enabled, but images will only be sent if your selected AI model supports vision/image inputs."
        )
        config_widgets["IMAGE_CONTEXT_WARNING"].setVisible(True)  # Always visible

        # Layout
        context_row1 = QHBoxLayout()
        context_row1.addWidget(hybrid_info)
        context_row1.addSpacing(20)
        context_row1.addWidget(label_xml_len)
        context_row1.addWidget(config_widgets["XML_SNIPPET_MAX_LEN"])
        context_row1.addStretch()
        
        context_row2 = QHBoxLayout()
        context_row2.addWidget(config_widgets["CONTEXT_SOURCE_IMAGE"])
        context_row2.addWidget(config_widgets["IMAGE_CONTEXT_WARNING"])
        context_row2.addStretch()
        
        form.addRow(context_row1)
        form.addRow(context_row2)

        # Store references to preprocessing option widgets and labels for visibility control
        preprocessing_widgets = []
        preprocessing_labels = []

        # Max width - hidden from UI, configurable via CLI
        from config.numeric_constants import IMAGE_MAX_WIDTH_MIN, IMAGE_MAX_WIDTH_MAX
        config_widgets["IMAGE_MAX_WIDTH"] = QSpinBox()
        config_widgets["IMAGE_MAX_WIDTH"].setRange(IMAGE_MAX_WIDTH_MIN, IMAGE_MAX_WIDTH_MAX)
        # Not added to UI (form.addRow is skipped)

        # Format - hidden from UI, configurable via CLI
        config_widgets["IMAGE_FORMAT"] = QComboBox()
        config_widgets["IMAGE_FORMAT"].addItems(["JPEG", "WEBP", "PNG"])
        # Not added to UI (form.addRow is skipped)

        # Quality - hidden from UI, configurable via CLI
        from config.numeric_constants import IMAGE_QUALITY_MIN, IMAGE_QUALITY_MAX
        config_widgets["IMAGE_QUALITY"] = QSpinBox()
        config_widgets["IMAGE_QUALITY"].setRange(IMAGE_QUALITY_MIN, IMAGE_QUALITY_MAX)
        # Not added to UI (form.addRow is skipped)

        # Store references for visibility control (attached to group as custom property)
        group.preprocessing_widgets = preprocessing_widgets
        group.preprocessing_labels = preprocessing_labels

        layout.addRow(group)
        return group







    @staticmethod
    def create_crawler_settings_group(
        layout: QFormLayout, config_widgets: Dict[str, Any], tooltips: Dict[str, str]
    ) -> QWidget:
        """Create the Crawler settings group."""
        crawler_group = CollapsibleBox("Crawler Settings")
        crawler_layout = QFormLayout()
        crawler_group.content_layout.addLayout(crawler_layout)

        config_widgets["CRAWL_MODE"] = QComboBox()
        config_widgets["CRAWL_MODE"].addItems(["steps", "time"])
        label_crawl_mode = QLabel("Crawl Mode: ")
        label_crawl_mode.setToolTip(tooltips["CRAWL_MODE"])
        crawler_layout.addRow(label_crawl_mode, config_widgets["CRAWL_MODE"])

        from config.numeric_constants import MAX_CRAWL_STEPS_MIN, MAX_CRAWL_STEPS_MAX
        config_widgets["MAX_CRAWL_STEPS"] = QSpinBox()
        config_widgets["MAX_CRAWL_STEPS"].setRange(MAX_CRAWL_STEPS_MIN, MAX_CRAWL_STEPS_MAX)
        label_max_crawl_steps = QLabel("Max Steps: ")
        label_max_crawl_steps.setToolTip(tooltips["MAX_CRAWL_STEPS"])
        crawler_layout.addRow(label_max_crawl_steps, config_widgets["MAX_CRAWL_STEPS"])

        from config.numeric_constants import MAX_CRAWL_DURATION_MIN_SECONDS, MAX_CRAWL_DURATION_MAX_SECONDS
        config_widgets["MAX_CRAWL_DURATION_SECONDS"] = QSpinBox()
        config_widgets["MAX_CRAWL_DURATION_SECONDS"].setRange(MAX_CRAWL_DURATION_MIN_SECONDS, MAX_CRAWL_DURATION_MAX_SECONDS)
        label_max_crawl_duration = QLabel("Max Duration (s): ")
        label_max_crawl_duration.setToolTip(tooltips["MAX_CRAWL_DURATION_SECONDS"])
        crawler_layout.addRow(
            label_max_crawl_duration, config_widgets["MAX_CRAWL_DURATION_SECONDS"]
        )

        config_widgets["WAIT_AFTER_ACTION"] = QSpinBox()
        config_widgets["WAIT_AFTER_ACTION"].setRange(0, 60)
        label_wait_after_action = QLabel("Wait After Action (s): ")
        label_wait_after_action.setToolTip(tooltips["WAIT_AFTER_ACTION"])
        crawler_layout.addRow(
            label_wait_after_action, config_widgets["WAIT_AFTER_ACTION"]
        )

        config_widgets["STABILITY_WAIT"] = QSpinBox()
        config_widgets["STABILITY_WAIT"].setRange(0, 60)
        label_stability_wait = QLabel("Stability Wait (s): ")
        label_stability_wait.setToolTip(tooltips["STABILITY_WAIT"])
        crawler_layout.addRow(label_stability_wait, config_widgets["STABILITY_WAIT"])

        from config.numeric_constants import APP_LAUNCH_WAIT_TIME_MIN, APP_LAUNCH_WAIT_TIME_MAX
        config_widgets["APP_LAUNCH_WAIT_TIME"] = QSpinBox()
        config_widgets["APP_LAUNCH_WAIT_TIME"].setRange(APP_LAUNCH_WAIT_TIME_MIN, APP_LAUNCH_WAIT_TIME_MAX)
        label_app_launch_wait_time = QLabel("App Launch Wait Time (s): ")
        label_app_launch_wait_time.setToolTip(tooltips["APP_LAUNCH_WAIT_TIME"])
        crawler_layout.addRow(
            label_app_launch_wait_time, config_widgets["APP_LAUNCH_WAIT_TIME"]
        )

        # Visual Similarity Threshold
        from config.numeric_constants import VISUAL_SIMILARITY_THRESHOLD_MIN, VISUAL_SIMILARITY_THRESHOLD_MAX
        config_widgets["VISUAL_SIMILARITY_THRESHOLD"] = QSpinBox()
        config_widgets["VISUAL_SIMILARITY_THRESHOLD"].setRange(VISUAL_SIMILARITY_THRESHOLD_MIN, VISUAL_SIMILARITY_THRESHOLD_MAX)
        label_visual_similarity = QLabel("Visual Similarity Threshold: ")
        label_visual_similarity.setToolTip(tooltips["VISUAL_SIMILARITY_THRESHOLD"])
        crawler_layout.addRow(
            label_visual_similarity, config_widgets["VISUAL_SIMILARITY_THRESHOLD"]
        )

        # Allowed External Packages - Use dedicated widget with CRUD support
        from ui.allowed_packages_widget import AllowedPackagesWidget
        from config.app_config import Config
        config = Config()
        config_widgets["ALLOWED_EXTERNAL_PACKAGES_WIDGET"] = AllowedPackagesWidget(config)
        # Store a reference to the widget for compatibility with config manager
        config_widgets["ALLOWED_EXTERNAL_PACKAGES"] = config_widgets["ALLOWED_EXTERNAL_PACKAGES_WIDGET"]
        label_allowed_packages = QLabel("Allowed External Packages: ")
        label_allowed_packages.setToolTip(tooltips["ALLOWED_EXTERNAL_PACKAGES"])
        config_widgets["ALLOWED_EXTERNAL_PACKAGES_WIDGET"].setToolTip(tooltips["ALLOWED_EXTERNAL_PACKAGES"])
        crawler_layout.addRow(label_allowed_packages, config_widgets["ALLOWED_EXTERNAL_PACKAGES_WIDGET"])

        # Step-by-Step Mode checkbox (persisted)
        config_widgets["STEP_BY_STEP_MODE"] = QCheckBox()
        config_widgets["STEP_BY_STEP_MODE"].setToolTip("Pause after each step to inspect state. Useful for debugging.")
        label_step_mode = QLabel("Step-by-Step Mode: ")
        label_step_mode.setToolTip("Enable to pause after each crawler step for inspection")
        crawler_layout.addRow(label_step_mode, config_widgets["STEP_BY_STEP_MODE"])

        layout.addRow(crawler_group)
        return crawler_group


    @staticmethod
    def create_recording_group(
        layout: QFormLayout, config_widgets: Dict[str, Any], tooltips: Dict[str, str]
    ) -> QWidget:
        """Create the Recording group for media capture settings."""
        recording_group = CollapsibleBox("Recording")
        recording_layout = QFormLayout()
        recording_group.content_layout.addLayout(recording_layout)

        config_widgets["ENABLE_VIDEO_RECORDING"] = QCheckBox()
        label_enable_video = QLabel("Enable Video Recording: ")
        label_enable_video.setToolTip(tooltips["ENABLE_VIDEO_RECORDING"])
        recording_layout.addRow(
            label_enable_video, config_widgets["ENABLE_VIDEO_RECORDING"]
        )

        layout.addRow(recording_group)
        return recording_group

    @staticmethod
    def create_error_handling_group(
        layout: QFormLayout, config_widgets: Dict[str, Any], tooltips: Dict[str, str]
    ) -> QWidget:
        """Create the Error Handling group for failure threshold settings."""
        error_handling_group = CollapsibleBox("Error Handling")
        error_handling_layout = QFormLayout()
        error_handling_group.content_layout.addLayout(error_handling_layout)

        from config.numeric_constants import MAX_CONSECUTIVE_FAILURES_MIN, MAX_CONSECUTIVE_FAILURES_MAX
        config_widgets["MAX_CONSECUTIVE_AI_FAILURES"] = QSpinBox()
        config_widgets["MAX_CONSECUTIVE_AI_FAILURES"].setRange(MAX_CONSECUTIVE_FAILURES_MIN, MAX_CONSECUTIVE_FAILURES_MAX)
        label_max_ai_failures = QLabel("Max Consecutive AI Failures: ")
        label_max_ai_failures.setToolTip(tooltips["MAX_CONSECUTIVE_AI_FAILURES"])
        error_handling_layout.addRow(
            label_max_ai_failures, config_widgets["MAX_CONSECUTIVE_AI_FAILURES"]
        )

        config_widgets["MAX_CONSECUTIVE_MAP_FAILURES"] = QSpinBox()
        config_widgets["MAX_CONSECUTIVE_MAP_FAILURES"].setRange(MAX_CONSECUTIVE_FAILURES_MIN, MAX_CONSECUTIVE_FAILURES_MAX)
        label_max_map_failures = QLabel("Max Consecutive Map Failures: ")
        label_max_map_failures.setToolTip(tooltips["MAX_CONSECUTIVE_MAP_FAILURES"])
        error_handling_layout.addRow(
            label_max_map_failures, config_widgets["MAX_CONSECUTIVE_MAP_FAILURES"]
        )

        layout.addRow(error_handling_group)
        return error_handling_group

    @staticmethod
    def create_privacy_network_group(
        layout: QFormLayout, config_widgets: Dict[str, Any], tooltips: Dict[str, str]
    ) -> QWidget:
        """Create the Privacy & Network group for traffic capture-related settings."""
        privacy_group = CollapsibleBox("Privacy & Network")
        privacy_layout = QFormLayout()
        privacy_group.content_layout.addLayout(privacy_layout)

        # Traffic capture toggles moved from Feature Toggles
        config_widgets["ENABLE_TRAFFIC_CAPTURE"] = QCheckBox()
        label_enable_traffic_capture = QLabel("Enable Traffic Capture: ")
        label_enable_traffic_capture.setToolTip(tooltips["ENABLE_TRAFFIC_CAPTURE"])
        privacy_layout.addRow(
            label_enable_traffic_capture, config_widgets["ENABLE_TRAFFIC_CAPTURE"]
        )

        layout.addRow(privacy_group)
        return privacy_group

    @staticmethod
    def _create_api_key_field_with_toggle(
        config_widgets: Dict[str, Any],
        key_name: str,
        placeholder: str,
        label_text: str,
        tooltip: str,
    ) -> Tuple[QLineEdit, QWidget, QLabel]:
        """
        Create an API key input field with toggle visibility button.
        
        Args:
            config_widgets: Dictionary to store widgets
            key_name: Key name for the widget (e.g., "OPENROUTER_API_KEY")
            placeholder: Placeholder text for the input field
            label_text: Label text for the field
            tooltip: Tooltip text for the field
            
        Returns:
            Tuple of (QLineEdit, QWidget container, QLabel)
        """
        # Create the API key input field
        api_key_field = QLineEdit()
        api_key_field.setPlaceholderText(placeholder)
        api_key_field.setEchoMode(QLineEdit.EchoMode.Password)
        config_widgets[key_name] = api_key_field
        
        # Create eye icon button to toggle password visibility
        toggle_password_btn = QPushButton()
        # Fixed size removed to allow text fallback to fit
        toggle_password_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_password_btn.setToolTip("Show/Hide API Key")
        toggle_password_btn.setFlat(True)
        
        # Set initial icon (eye icon for hidden password)
        eye_icon = QIcon.fromTheme("view-hidden", QIcon())
        if eye_icon.isNull():
            # Fallback to text if theme icon not available
            toggle_password_btn.setText("Show")
            toggle_password_btn.setFixedWidth(45) # Sufficient width for text
        else:
            toggle_password_btn.setIcon(eye_icon)
            toggle_password_btn.setFixedSize(30, 30)
        
        # Create container widget with horizontal layout
        api_key_container = QWidget()
        api_key_layout = QHBoxLayout(api_key_container)
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        api_key_layout.setSpacing(5)
        api_key_layout.addWidget(api_key_field)
        api_key_layout.addWidget(toggle_password_btn)
        
        # Toggle password visibility on button click
        def toggle_password_visibility():
            if api_key_field.echoMode() == QLineEdit.EchoMode.Password:
                api_key_field.setEchoMode(QLineEdit.EchoMode.Normal)
                # Change to eye-slash icon when visible
                eye_slash_icon = QIcon.fromTheme("view-visible", QIcon())
                if eye_slash_icon.isNull():
                    toggle_password_btn.setText("Hide")
                    toggle_password_btn.setFixedWidth(45)
                    toggle_password_btn.setIcon(QIcon()) # Clear icon
                else:
                    toggle_password_btn.setText("") # Clear text
                    toggle_password_btn.setIcon(eye_slash_icon)
                    toggle_password_btn.setFixedSize(30, 30)
            else:
                api_key_field.setEchoMode(QLineEdit.EchoMode.Password)
                # Change to eye icon when hidden
                eye_icon = QIcon.fromTheme("view-hidden", QIcon())
                if eye_icon.isNull():
                    toggle_password_btn.setText("Show")
                    toggle_password_btn.setFixedWidth(45)
                    toggle_password_btn.setIcon(QIcon()) # Clear icon
                else:
                    toggle_password_btn.setText("") # Clear text
                    toggle_password_btn.setIcon(eye_icon)
                    toggle_password_btn.setFixedSize(30, 30)
        
        toggle_password_btn.clicked.connect(toggle_password_visibility)
        
        # Create label
        label = QLabel(label_text)
        label.setToolTip(tooltip)
        
        return api_key_field, api_key_container, label

    @staticmethod
    def create_api_keys_group(
        layout: QFormLayout,
        config_widgets: Dict[str, Any],
        tooltips: Dict[str, str],
        config_handler: Any,
    ) -> QWidget:
        """Create the API Keys & Credentials settings group."""
        from ui.strings import (
            API_KEYS_GROUP,
            OPENROUTER_API_KEY_PLACEHOLDER,
            GEMINI_API_KEY_PLACEHOLDER,
            MOBSF_API_KEY_PLACEHOLDER,
        )
        
        # Rename group to reflect it contains more than just API keys
        api_keys_group = CollapsibleBox("API Keys & Credentials")
        api_keys_layout = QFormLayout()
        api_keys_group.content_layout.addLayout(api_keys_layout)
        
        # --- API Keys ---
        
        # OpenRouter API Key
        _, openrouter_container, openrouter_label = ComponentFactory._create_api_key_field_with_toggle(
            config_widgets,
            "OPENROUTER_API_KEY",
            OPENROUTER_API_KEY_PLACEHOLDER,
            "OpenRouter API Key: ",
            tooltips.get("OPENROUTER_API_KEY", ""),
        )
        api_keys_layout.addRow(openrouter_label, openrouter_container)
        
        # Gemini API Key
        _, gemini_container, gemini_label = ComponentFactory._create_api_key_field_with_toggle(
            config_widgets,
            "GEMINI_API_KEY",
            GEMINI_API_KEY_PLACEHOLDER,
            "Gemini API Key: ",
            tooltips.get("GEMINI_API_KEY", ""),
        )
        api_keys_layout.addRow(gemini_label, gemini_container)
        
        # MobSF API Key
        _, mobsf_container, mobsf_label = ComponentFactory._create_api_key_field_with_toggle(
            config_widgets,
            "MOBSF_API_KEY",
            MOBSF_API_KEY_PLACEHOLDER,
            "MobSF API Key: ",
            tooltips.get("MOBSF_API_KEY", ""),
        )
        api_keys_layout.addRow(mobsf_label, mobsf_container)
        
        # Store references for visibility control
        config_widgets["MOBSF_API_KEY_LABEL"] = mobsf_label
        config_widgets["MOBSF_API_KEY_CONTAINER"] = mobsf_container

        # PCAPDroid API Key
        _, pcap_container, pcap_label = ComponentFactory._create_api_key_field_with_toggle(
            config_widgets,
            "PCAPDROID_API_KEY",
            "Enter PCAPDroid API Key...",
            "PCAPDroid API Key: ",
            "API Key for PCAPDroid traffic capture integration",
        )
        api_keys_layout.addRow(pcap_label, pcap_container)
        
        # --- Ollama Configuration ---
        
        ollama_url_field = QLineEdit()
        ollama_url_field.setPlaceholderText("http://localhost:11434")
        config_widgets["OLLAMA_BASE_URL"] = ollama_url_field
        ollama_label = QLabel("Ollama Base URL: ")
        ollama_label.setToolTip("Base URL for local Ollama instance")
        api_keys_layout.addRow(ollama_label, ollama_url_field)

        # --- Gmail Credentials ---
        
        # Gmail App Password
        _, gmail_pwd_container, gmail_pwd_label = ComponentFactory._create_api_key_field_with_toggle(
            config_widgets,
            "GMAIL_APP_PASSWORD",
            "Enter App Password",
            "Gmail App Password: ",
            "App Password for Gmail IMAP access (generate in Google Account Security settings)",
        )
        api_keys_layout.addRow(gmail_pwd_label, gmail_pwd_container)
        
        # Note: GMAIL_USER is determined from TEST_EMAIL if not explicitly set

        # --- Test Credentials ---
        
        # Test Email
        test_email_field = QLineEdit()
        test_email_field.setPlaceholderText("test@example.com")
        config_widgets["TEST_EMAIL"] = test_email_field
        test_email_label = QLabel("Test Account Email: ")
        test_email_label.setToolTip("Email address for AI to use during login/signup flows")
        api_keys_layout.addRow(test_email_label, test_email_field)
        
        # Test Password
        _, test_pwd_container, test_pwd_label = ComponentFactory._create_api_key_field_with_toggle(
            config_widgets,
            "TEST_PASSWORD",
            "Enter test account password",
            "Test Account Password: ",
            "Password for AI to use during login/signup flows",
        )
        api_keys_layout.addRow(test_pwd_label, test_pwd_container)
        
        # Test Name
        test_name_field = QLineEdit()
        test_name_field.setPlaceholderText("Test User")
        config_widgets["TEST_NAME"] = test_name_field
        test_name_label = QLabel("Test Account Name: ")
        test_name_label.setToolTip("Name for AI to use during form filling")
        api_keys_layout.addRow(test_name_label, test_name_field)
        
        # --- Load Values ---
        
        keys_to_load = [
            "OPENROUTER_API_KEY", "GEMINI_API_KEY", "MOBSF_API_KEY", 
            "PCAPDROID_API_KEY", "OLLAMA_BASE_URL", 
            "TEST_EMAIL", "TEST_PASSWORD", "TEST_NAME",
            "GMAIL_APP_PASSWORD"
        ]
        
        for key in keys_to_load:
            try:
                val = config_handler.config.get(key)
                if val:
                    widget = config_widgets.get(key)
                    if isinstance(widget, QLineEdit):
                        widget.setText(str(val))
            except Exception:
                pass
        
        layout.addRow(api_keys_group)
        return api_keys_group

    @staticmethod
    def create_mobsf_settings_group(
        layout: QFormLayout,
        config_widgets: Dict[str, Any],
        tooltips: Dict[str, str],
        config_handler: Any,
    ) -> QWidget:
        """Create the MobSF settings group."""
        mobsf_group = CollapsibleBox("MobSF Static Analysis")
        mobsf_layout = QFormLayout()
        mobsf_group.content_layout.addLayout(mobsf_layout)

        # MobSF Enable Checkbox
        config_widgets["ENABLE_MOBSF_ANALYSIS"] = QCheckBox()
        label_enable_mobsf = QLabel("Enable MobSF Analysis: ")
        label_enable_mobsf.setToolTip(tooltips["ENABLE_MOBSF_ANALYSIS"])
        mobsf_layout.addRow(label_enable_mobsf, config_widgets["ENABLE_MOBSF_ANALYSIS"])

        # Get current enabled state (default to False if not set)
        is_mobsf_enabled = getattr(
            config_handler.config, "ENABLE_MOBSF_ANALYSIS", False
        )
        config_widgets["ENABLE_MOBSF_ANALYSIS"].setChecked(is_mobsf_enabled)

        # AI Run Report Enable Checkbox
        config_widgets["ENABLE_AI_RUN_REPORT"] = QCheckBox()
        label_enable_ai_report = QLabel("Enable AI Run Report: ")
        label_enable_ai_report.setToolTip(tooltips["ENABLE_AI_RUN_REPORT"])
        mobsf_layout.addRow(label_enable_ai_report, config_widgets["ENABLE_AI_RUN_REPORT"])

        # Get current enabled state (default to False if not set)
        is_ai_report_enabled = getattr(
            config_handler.config, "ENABLE_AI_RUN_REPORT", False
        )
        config_widgets["ENABLE_AI_RUN_REPORT"].setChecked(is_ai_report_enabled)

        # API URL field
        from config.urls import ServiceURLs
        config_widgets["MOBSF_API_URL"] = QLineEdit()
        from ui.strings import MOBSF_API_URL_PLACEHOLDER
        config_widgets["MOBSF_API_URL"].setPlaceholderText(MOBSF_API_URL_PLACEHOLDER)
        # Get current API URL from config (default to ServiceURLs.MOBSF if not set)
        mobsf_api_url = config_handler.config.CONFIG_MOBSF_API_URL
        config_widgets["MOBSF_API_URL"].setText(mobsf_api_url)
        label_mobsf_api_url = QLabel("MobSF API URL: ")
        label_mobsf_api_url.setToolTip(tooltips["MOBSF_API_URL"])
        mobsf_layout.addRow(label_mobsf_api_url, config_widgets["MOBSF_API_URL"])
        # Store label reference for visibility control
        config_widgets["MOBSF_API_URL_LABEL"] = label_mobsf_api_url

        # Note: MobSF API Key is now in the API Keys group, but we still need
        # to reference it for visibility control when MobSF is enabled/disabled
        # The actual field is created in create_api_keys_group

        # MobSF test and analysis buttons - assign to main_controller instead of config_handler
        main_controller = config_handler.main_controller
        main_controller.test_mobsf_conn_btn = QPushButton("Test MobSF Connection")
        mobsf_layout.addRow(main_controller.test_mobsf_conn_btn)

        main_controller.run_mobsf_analysis_btn = QPushButton("Run MobSF Analysis")
        mobsf_layout.addRow(main_controller.run_mobsf_analysis_btn)

        # Set initial visibility and button states based on checkbox
        # Hide/show fields and buttons based on checkbox state
        config_widgets["MOBSF_API_URL"].setVisible(is_mobsf_enabled)
        label_mobsf_api_url.setVisible(is_mobsf_enabled)
        # Note: MobSF API Key is in API Keys group and should always be visible
        # (not controlled by MobSF enable checkbox)
        main_controller.test_mobsf_conn_btn.setVisible(is_mobsf_enabled)
        main_controller.run_mobsf_analysis_btn.setVisible(is_mobsf_enabled)
        
        # Also set enabled state for buttons
        main_controller.test_mobsf_conn_btn.setEnabled(is_mobsf_enabled)
        main_controller.run_mobsf_analysis_btn.setEnabled(is_mobsf_enabled)

        # Connect the checkbox to update button state - using a direct slot reference
        # Connect after buttons are created
        config_widgets["ENABLE_MOBSF_ANALYSIS"].stateChanged.connect(
            config_handler._on_mobsf_enabled_state_changed
        )

        layout.addRow(mobsf_group)
        return mobsf_group