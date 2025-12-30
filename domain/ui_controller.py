# ui_controller.py - Main UI controller for the Appium Crawler

import logging
import os
import re
import subprocess
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union


from PySide6.QtCore import QProcess, Qt, QThread, QTimer, Signal, QUrl
from PySide6.QtCore import Slot as slot
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QSplitter,
)

try:
    from domain.analysis_viewer import XHTML2PDF_AVAILABLE, RunAnalyzer
except Exception:
    RunAnalyzer = None
    XHTML2PDF_AVAILABLE = False
from ui.log_manager import LogManager
from ui.device_manager import DeviceManager
from ui.report_manager import ReportManager
from ui.agent_manager import AgentManager
from ui.ui_utils import update_screenshot
from ui.logo_widget import LogoWidget
from domain.prompt_builder import PromptBuilder


class CrawlerControllerWindow(QMainWindow):
    """Main window for the Appium Crawler Controller."""

    def __init__(self, config=None, api_dir=None):
        """Initialize the main UI controller window.
        
        Args:
            config: Optional Config instance. If None, creates a new one.
            api_dir: Optional API directory path. If None, uses project root.
        """
        super().__init__()
        
        # Initialize config if not provided
        if config is None:
            from config.app_config import Config
            config = Config()
        self.config = config
        
        # Initialize api_dir if not provided
        if api_dir is None:
            from utils.paths import find_project_root
            from pathlib import Path
            api_dir = str(find_project_root(Path(__file__).resolve().parent))
        self.api_dir = api_dir
        
        # Initialize empty config_widgets dict - will be populated by ComponentFactory
        self.config_widgets = {}
        
        # These will be created by _setup_ui method
        # Initialize as None for now - they'll be set by the UI creation methods
        self.start_stop_btn = None
        self.log_output = None
        self.ai_input_log = None  # New AI Input log
        self.ai_output_log = None # New AI Output log
        self.screenshot_label = None
        self.clear_logs_btn = None
        self.current_health_app_list_file = None
        self.health_apps_data = None
        self.ai_history = []  # Stores list of dicts: {'label': str, 'input': str, 'output': str}
        self.ai_history_dropdown = None

        self._ensure_output_directories_exist()

        # Set the application icon
        self._set_application_icon()
        
        # Set the window title
        self.setWindowTitle("Appium Traverser")

        # Initialize managers
        from ui.config_ui_manager import ConfigManager
        from ui.crawler_ui_manager import CrawlerManager
        from ui.app_scanner_ui import HealthAppScanner
        from ui.mobsf_ui_manager import MobSFUIManager
        
        self.config_manager = ConfigManager(self.config, self)
        self.crawler_manager = CrawlerManager(self)
        self.health_app_scanner = HealthAppScanner(self)
        self.mobsf_ui_manager = MobSFUIManager(self)
        
        # New specialized delegation managers
        self.agent_manager = AgentManager(self.config, self.log_message)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Define tooltips
        self.tooltips = self._create_tooltips()

        # Setup UI panels
        self._setup_ui(main_layout)
        
        # Initialize Log, Device and Report managers after UI setup
        # Initialize Log, Device and Report managers after UI setup
        self.log_manager = LogManager(
            self.log_output, None, self.status_label, 
            self.step_label, self.progress_bar, self
        )
        self.device_manager = DeviceManager(
            self.config_widgets.get("TARGET_DEVICE_UDID"), self.config, self.log_message
        )
        self.report_manager = ReportManager(
            self.config, self.log_message, lambda busy, msg="": self.show_busy(msg) if busy else self.hide_busy()
        )

        # Load configuration
        self.config_manager.load_config()

        # Initialize AgentAssistant after config is loaded (deferred to prevent UI freeze on startup)
        # Use a small delay to allow the window to render first
        QTimer.singleShot(100, lambda: self.agent_manager.init_agent())

        # Attempt to load cached health apps
        self._attempt_load_cached_health_apps()

        # Connect signals to slots
        self._connect_signals()

        # Initialize preview prompt builder and timer
        self._preview_prompt_builder = PromptBuilder(self.config)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(500)  # 500ms debounce
        self._preview_timer.timeout.connect(self.refresh_prompt_preview)
        
        # Setup live preview connections
        self._setup_live_preview_connections()

        # Connect the refresh devices button
        if hasattr(self, "refresh_devices_btn") and self.refresh_devices_btn:
            self.refresh_devices_btn.clicked.connect(self.device_manager.populate_devices)

        # Populate device dropdown on startup
        self.device_manager.populate_devices()

    def _setup_ui(self, main_layout: QHBoxLayout):
        """Setup the UI panels and initialize UIStateHandler."""
        from ui.component_factory import ComponentFactory
        
        # Create left panel
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)

        # Create scrollable area for config inputs
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_content = QWidget()
        scroll_layout = QFormLayout(scroll_content)

        # Store scroll_content in config_manager for later reference
        self.config_manager.scroll_content = scroll_content

        # Create the config inputs sections
        # API Keys group (moved to top - required before AI/MobSF configuration)
        api_keys_group = ComponentFactory.create_api_keys_group(
            scroll_layout, self.config_widgets, self.tooltips, self.config_manager
        )
        api_keys_group.setObjectName("api_keys_group")

        appium_group = ComponentFactory.create_appium_settings_group(
            scroll_layout, self.config_widgets, self.tooltips, self
        )
        appium_group.setObjectName("appium_settings_group")

        app_group = ComponentFactory.create_app_settings_group(
            scroll_layout, self.config_widgets, self.tooltips, self.config_manager
        )
        app_group.setObjectName("app_settings_group")

        ai_group = ComponentFactory.create_ai_settings_group(
            scroll_layout, self.config_widgets, self.tooltips, self.config_manager
        )
        ai_group.setObjectName("ai_settings_group")

        # Image Preprocessing placed directly after AI for clearer perception grouping
        image_prep_group = ComponentFactory.create_image_preprocessing_group(
            scroll_layout, self.config_widgets, self.tooltips
        )
        image_prep_group.setObjectName("image_preprocessing_group")

        crawler_group = ComponentFactory.create_crawler_settings_group(
            scroll_layout, self.config_widgets, self.tooltips
        )
        crawler_group.setObjectName("crawler_settings_group")

        # Privacy & Network settings (traffic capture)
        privacy_network_group = ComponentFactory.create_privacy_network_group(
            scroll_layout, self.config_widgets, self.tooltips
        )
        privacy_network_group.setObjectName("privacy_network_group")

        mobsf_group = ComponentFactory.create_mobsf_settings_group(
            scroll_layout, self.config_widgets, self.tooltips, self.config_manager
        )
        mobsf_group.setObjectName("mobsf_settings_group")

        # Recording group
        recording_group = ComponentFactory.create_recording_group(
            scroll_layout, self.config_widgets, self.tooltips
        )
        recording_group.setObjectName("recording_group")

        # Apply default values
        self.config_manager._apply_defaults_from_config_to_widgets()
        self.config_manager._update_crawl_mode_inputs_state()

        # Store the group widgets for mode switching
        self.ui_groups = {
            "api_keys_group": api_keys_group,
            "appium_settings_group": appium_group,
            "app_settings_group": app_group,
            "ai_settings_group": ai_group,
            "image_preprocessing_group": image_prep_group,
            "crawler_settings_group": crawler_group,
            "privacy_network_group": privacy_network_group,
            "mobsf_settings_group": mobsf_group,
            "recording_group": recording_group,
        }
        # Also store in config_manager for backward compatibility
        self.config_manager.ui_groups = self.ui_groups

        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll)


        # Assign refresh_devices_btn if set by ComponentFactory
        if hasattr(self, "refresh_devices_btn"):
            pass  # Already set by ComponentFactory
        else:
            self.refresh_devices_btn = None

        # Copy UI references from config_manager to self for direct access
        if hasattr(self.config_manager, "health_app_dropdown"):
            self.health_app_dropdown = self.config_manager.health_app_dropdown

        if hasattr(self.config_manager, "refresh_apps_btn"):
            self.refresh_apps_btn = self.config_manager.refresh_apps_btn

        if hasattr(self.config_manager, "app_scan_status_label"):
            self.app_scan_status_label = self.config_manager.app_scan_status_label

        # Create UIStateHandler
        from ui.ui_state_handler import UIStateHandler
        self.ui_state_handler = UIStateHandler(
            main_controller=self,
            config_handler=self.config_manager,
            config_widgets=self.config_widgets,
            ui_groups=self.ui_groups
        )


        # Connect AI provider selection to update model types
        def _on_provider_changed(provider: str):
            self.ui_state_handler._update_model_types(provider)

        self.config_widgets["AI_PROVIDER"].currentTextChanged.connect(_on_provider_changed)

        # Wire up refresh button
        def _on_refresh_clicked():
            try:
                self.ui_state_handler._refresh_models()
            except Exception as e:
                logging.warning(f"Failed to refresh models: {e}")

        self.config_widgets["OPENROUTER_REFRESH_BTN"].clicked.connect(_on_refresh_clicked)

        # Wire up free-only filter to re-populate models
        def _on_free_only_changed(_state: int):
            try:
                # Save the preference first
                free_only = self.config_widgets["OPENROUTER_SHOW_FREE_ONLY"].isChecked()
                self.config_manager.config.set("OPENROUTER_SHOW_FREE_ONLY", free_only)
                
                # Then update the model list
                current_provider = self.config_widgets["AI_PROVIDER"].currentText()
                self.ui_state_handler._update_model_types(current_provider)
            except Exception as e:
                pass

        self.config_widgets["OPENROUTER_SHOW_FREE_ONLY"].stateChanged.connect(
            _on_free_only_changed
        )

        # Wire up vision-only filter to re-populate models
        def _on_vision_only_changed(_state: int):
            try:
                # Update the model list with the new filter state
                current_provider = self.config_widgets["AI_PROVIDER"].currentText()
                self.ui_state_handler._update_model_types(current_provider)
            except Exception as e:
                pass

        self.config_widgets["SHOW_VISION_ONLY"].stateChanged.connect(
            _on_vision_only_changed
        )

        # Connect all widgets to auto-save
        self.config_manager.connect_widgets_for_auto_save()


        # Create right panel
        right_panel = QWidget()
        right_main_layout = QVBoxLayout(right_panel)

        # Step counter and status at the top (small header)
        # Step counter and status at the top (small header)
        header_layout = QHBoxLayout()
        
        self.step_label = QLabel("Step: 0")
        self.status_label = QLabel("Status: Idle")
        self.progress_bar = QProgressBar()
        header_layout.addWidget(self.step_label)
        header_layout.addWidget(self.status_label)
        header_layout.addWidget(self.progress_bar)
        right_main_layout.addLayout(header_layout)

        # Main content area: Logs on left (2/3), Screenshot + Action History stacked on right (1/3)
        content_layout = QHBoxLayout()

        # Logs section - takes 2/3 of width
        # We will use a Vertical Splitter to divide Logs (top) from AI Trace (bottom)
        center_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # --- Top: Logs ---
        log_group = QGroupBox("Logs")
        log_layout = QVBoxLayout(log_group)

        # Add a clear button
        self.clear_logs_btn = QPushButton("Clear Logs")

        log_header_layout = QHBoxLayout()
        log_header_layout.addStretch()
        log_header_layout.addWidget(self.clear_logs_btn)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #333333;")

        log_layout.addLayout(log_header_layout)
        log_layout.addWidget(self.log_output)
        
        # Add Start/Stop button below logs
        self.start_stop_btn = QPushButton("Start Crawler")
        self.start_stop_btn.setToolTip("Start or stop the crawler process")
        # self.start_stop_btn.setMinimumHeight(50) # Removed to match other buttons
        self.start_stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32; 
                color: white; 
                font-weight: bold; 
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        if hasattr(self, 'toggle_crawler_state'):
            self.start_stop_btn.clicked.connect(self.toggle_crawler_state)
            
        # Add pre-check button
        self.pre_check_btn = QPushButton("🔍 Pre-Check Services")
        self.pre_check_btn.setToolTip(
            "Check the status of all required services (Appium, Ollama, MobSF) before starting"
        )
        self.pre_check_btn.clicked.connect(self.perform_pre_crawl_validation)
        
        # Container for buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.start_stop_btn, 3) # Start/Stop takes 3 parts
        buttons_layout.addWidget(self.pre_check_btn, 1) # Pre-check takes 1 part
        
        # Second row of controls (Session & Report & Reset)
        secondary_buttons_layout = QHBoxLayout()
        
        # Open session folder button
        self.open_session_folder_btn = QPushButton("📂 Open Session Folder")
        self.open_session_folder_btn.setToolTip(
            "Open the current session's output folder in the file explorer"
        )
        self.open_session_folder_btn.setEnabled(True)
        self.open_session_folder_btn.clicked.connect(self.open_session_folder)
        secondary_buttons_layout.addWidget(self.open_session_folder_btn, 3) # Takes left half of start button area
        
        # Generate report button
        self.generate_report_btn = QPushButton("📄 Generate Report (PDF)")
        self.generate_report_btn.setToolTip(
            "Generate a PDF report from the current session's activities"
        )
        self.generate_report_btn.clicked.connect(self.generate_report)
        secondary_buttons_layout.addWidget(self.generate_report_btn, 3) # Takes right half of start button area

        # Toggle Settings Button (beside Reset)
        self.toggle_settings_btn = QPushButton("Hide Settings")
        self.toggle_settings_btn.setToolTip("Toggle the visibility of the settings panel")
        # Removing checkable state to avoid "tinted" look
        # self.toggle_settings_btn.setCheckable(True) 
        # self.toggle_settings_btn.setChecked(True)
        
        def _toggle_settings_panel():
            if self.left_panel.isVisible():
                self.left_panel.setVisible(False)
                self.toggle_settings_btn.setText("Show Settings")
            else:
                self.left_panel.setVisible(True)
                self.toggle_settings_btn.setText("Hide Settings")
                
        self.toggle_settings_btn.clicked.connect(_toggle_settings_panel)
        secondary_buttons_layout.addWidget(self.toggle_settings_btn, 1)

        # Reset settings button (Aligned under Pre-Check)
        self.reset_btn = QPushButton("Reset Settings")
        from ui.strings import RESET_TO_DEFAULTS_TOOLTIP
        self.reset_btn.setToolTip(RESET_TO_DEFAULTS_TOOLTIP)
        self.reset_btn.clicked.connect(self.config_manager.reset_settings)
        secondary_buttons_layout.addWidget(self.reset_btn, 1) # Matches Pre-check with padding adjustment or slightly larger

        log_layout.addLayout(buttons_layout)
        log_layout.addLayout(secondary_buttons_layout)
        
        # --- AI Trace (Input/Output) Definition ---
        ai_trace_group = QGroupBox("AI Interaction Inspector")
        ai_trace_layout = QVBoxLayout(ai_trace_group)
        
        # Dropdown for history selection
        history_layout = QHBoxLayout()
        history_label = QLabel("Interaction History:")
        self.ai_history_dropdown = QComboBox()
        self.ai_history_dropdown.setToolTip("Select previous AI interactions to view their details")
        self.ai_history_dropdown.currentIndexChanged.connect(self._on_ai_history_selected)
        
        history_layout.addWidget(history_label)
        history_layout.addWidget(self.ai_history_dropdown, 1) # Give it stretch factor
        self.ai_history_dropdown.setMinimumWidth(350) # Ensure it's wide enough
        history_layout.addStretch()
        
        ai_trace_layout.addLayout(history_layout)
        

        ai_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # AI Input Panel
        ai_input_container = QWidget()
        ai_input_layout = QVBoxLayout(ai_input_container)
        ai_input_layout.setContentsMargins(0, 0, 0, 0)
        ai_input_label = QLabel("AI Input (Prompt/Context)")
        self.ai_input_log = QTextEdit()
        self.ai_input_log.setReadOnly(True)
        self.ai_input_log.setStyleSheet("""
            background-color: #2b2b2b;
            color: #a9b7c6;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 11px;
        """)
        ai_input_layout.addWidget(ai_input_label)
        ai_input_layout.addWidget(self.ai_input_log)
        
        # AI Output Panel
        ai_output_container = QWidget()
        ai_output_layout = QVBoxLayout(ai_output_container)
        ai_output_layout.setContentsMargins(0, 0, 0, 0)
        ai_output_label = QLabel("AI Output (Response)")
        self.ai_output_log = QTextEdit()
        self.ai_output_log.setReadOnly(True)
        self.ai_output_log.setStyleSheet("""
            background-color: #2b2b2b;
            color: #a9b7c6;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 11px;
        """)
        ai_output_layout.addWidget(ai_output_label)
        ai_output_layout.addWidget(self.ai_output_log)
        
        # Add to horizontal splitter
        ai_splitter.addWidget(ai_input_container)
        ai_splitter.addWidget(ai_output_container)
        
        # Set stretch factors for horizontal splitter (50/50)
        ai_splitter.setStretchFactor(0, 1)
        ai_splitter.setStretchFactor(1, 1)
        
        ai_trace_layout.addWidget(ai_splitter)

        # --- Add Widgets to Vertical Splitter ---
        # Add AI Trace to vertical splitter (Top, 2/3 height)
        center_splitter.addWidget(ai_trace_group)
        
        # Add Logs to vertical splitter (Bottom, 1/3 height)
        center_splitter.addWidget(log_group)
        
        # Set initial sizes for vertical splitter
        center_splitter.setStretchFactor(0, 7) # AI Trace 70% (Top)
        center_splitter.setStretchFactor(1, 3) # Logs 30% (Bottom)
        


        # Right side: Screenshot and Action History stacked vertically
        right_side_layout = QVBoxLayout()

        # Screenshot display (top right) - wider than tall
        screenshot_group = QGroupBox("Current Screenshot")
        screenshot_layout = QVBoxLayout(screenshot_group)
        self.screenshot_label = QLabel()
        self.screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screenshot_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.screenshot_label.setMinimumHeight(300)
        self.screenshot_label.setMinimumWidth(300)
        self.screenshot_label.setStyleSheet("""
            border: 1px solid #555555;
            background-color: #2a2a2a;
        """)
        screenshot_layout.addWidget(self.screenshot_label)

        # Action history section removed as requested
        # right_side_layout.addWidget(action_history_group, 1)

        # Add screenshot to right side layout (taking full height now)
        right_side_layout.addWidget(screenshot_group, 1)

        # Add center splitter (left, 2/3) and right side (1/3) to content layout
        content_layout.addWidget(center_splitter, 2)  # Logs/Trace take 2/3 of width
        content_layout.addLayout(right_side_layout, 1)  # Right side takes 1/3 of width

        # Add content layout to main layout
        right_main_layout.addLayout(content_layout, 1)  # Content takes all remaining vertical space

        # Add panels to main layout with stretch factors
        main_layout.addWidget(self.left_panel, 1)
        main_layout.addWidget(right_panel, 2)

        # Shutdown flag path for crawler process
        self._shutdown_flag_file_path = self.config.SHUTDOWN_FLAG_PATH
        log_message = f"Shutdown flag path configured: {self._shutdown_flag_file_path}"
        if hasattr(self, "log_output") and self.log_output:
            self.log_output.append(log_message)
        else:
            pass

        # Busy overlay dialog (initialized lazily)
        self._busy_dialog = None

    def show_busy(self, message: str = "Working...") -> None:
        """Show a modal busy overlay with the given message.
        
        The overlay will:
        - Cover the entire main window with a semi-transparent backdrop
        - Display a centered loading dialog with the message
        - Disable all interactive widgets in the UI
        - Block all user interactions until hidden
        """
        try:
            if self._busy_dialog is None:
                self._busy_dialog = BusyDialog(self)
            self._busy_dialog.set_message(message)
            # Cover the entire main window - ensure it's properly sized
            try:
                # Use frameGeometry to get the full window including title bar
                main_geometry = self.frameGeometry()
                self._busy_dialog.setGeometry(main_geometry)
            except Exception:
                # Fallback: use the main window geometry
                try:
                    self._busy_dialog.setGeometry(self.geometry())
                except Exception:
                    pass
            # Show and raise the dialog to ensure it's visible
            self._busy_dialog.show()
            self._busy_dialog.raise_()
            self._busy_dialog.activateWindow()
            QApplication.processEvents()
        except Exception as e:
            pass

    def hide_busy(self) -> None:
        """Hide the busy overlay if visible.
        
        This will re-enable all widgets that were disabled during loading.
        """
        try:
            if self._busy_dialog:
                # Use close_dialog to properly reset state
                if hasattr(self._busy_dialog, 'close_dialog'):
                    self._busy_dialog.close_dialog()
                else:
                    self._busy_dialog.hide()
                QApplication.processEvents()
        except Exception as e:
            pass


    def _create_tooltips(self) -> Dict[str, str]:
        """Create tooltips for UI elements."""
        from ui.strings import get_tooltips_dict
        return get_tooltips_dict()

    def _setup_live_preview_connections(self):
        """Connect signals for live prompt preview."""
        # 1. Prompt Field
        if "CRAWLER_ACTION_DECISION_PROMPT" in self.config_widgets:
            prompt_widget = self.config_widgets["CRAWLER_ACTION_DECISION_PROMPT"]
            if isinstance(prompt_widget, QTextEdit):
                prompt_widget.textChanged.connect(self._trigger_preview_update)
                
        # 2. Available Actions
        if "CRAWLER_AVAILABLE_ACTIONS" in self.config_widgets:
            actions_widget = self.config_widgets["CRAWLER_AVAILABLE_ACTIONS"]
            if hasattr(actions_widget, 'actionsChanged'):
                actions_widget.actionsChanged.connect(self._trigger_preview_update)
                


    def _trigger_preview_update(self):
        """Trigger a debounced preview update."""
        self._preview_timer.start()

    def refresh_prompt_preview(self):
        """Regenerate the 'Next AI Input' preview based on current UI state."""
        try:
            # Gather current values
            
            # 1. Prompt Template
            prompt_template = ""
            if "CRAWLER_ACTION_DECISION_PROMPT" in self.config_widgets:
                prompt_widget = self.config_widgets["CRAWLER_ACTION_DECISION_PROMPT"]
                if isinstance(prompt_widget, QTextEdit):
                    prompt_template = prompt_widget.toPlainText()
            
            # 2. Available Actions
            available_actions = {}
            if "CRAWLER_AVAILABLE_ACTIONS" in self.config_widgets:
                actions_widget = self.config_widgets["CRAWLER_AVAILABLE_ACTIONS"]
                if hasattr(actions_widget, 'get_enabled_actions'):
                    available_actions = actions_widget.get_enabled_actions()
            


            # Construct Mock Context
            mock_context = {
                'available_actions': available_actions,
                'xml_context': "<!-- XML Context Placeholder (Live Preview) -->\n<root>\n  <node text='Example App UI' />\n</root>",
                'ocr_context': [
                    {'text': 'Example Button', 'bounds': '[100,200][300,400]'},
                    {'text': 'Menu Icon', 'bounds': '[10,10][50,50]'}
                ],
                'action_history': [
                    {
                        'step_number': 1, 
                        'action_description': 'launched_app', 
                        'execution_success': True,
                        'to_screen_id': '0'
                    }
                ],
                'current_screen_actions': [],
                'current_screen_id': '0',
                'visited_screens': [{'screen_id': '0', 'activity_name': 'MainActivity', 'visit_count': 1}]
            }
            
            # Generate Prompt
            # We don't need a static prompt part here, PromptBuilder will generate it
            # using the provided available_actions in mock_context if we logic it right,
            # OR we can let it use self.cfg. But we want the LIVE available actions.
            
            # PromptBuilder.format_prompt uses context['available_actions'] override if present
            # as per my refactor.
            
            preview_text = self._preview_prompt_builder.format_prompt(
                prompt_template=prompt_template,
                context=mock_context
            )
            
            # Update Display
            # Add a visual indicator that this is a PREVIEW
            preview_header = "🔍 LIVE PREVIEW (Based on current settings)\n" + ("-" * 40) + "\n"
            self.update_ai_input(preview_header + preview_text)
            
        except Exception as e:
            self.log_message(f"Error updating prompt preview: {e}", "red")

    def _connect_signals(self):
        """Connect signals to slots safely."""
        try:
            # Connect AI provider/model change to agent reload
            ai_provider_widget = self.config_widgets.get("AI_PROVIDER")
            model_type_widget = self.config_widgets.get("DEFAULT_MODEL_TYPE")
            if ai_provider_widget:
                ai_provider_widget.currentTextChanged.connect(self._on_provider_or_model_changed)
            if model_type_widget:
                model_type_widget.currentTextChanged.connect(self._on_provider_or_model_changed)

            # Connect the health app dropdown change signal
            if self.health_app_dropdown and hasattr(
                self.health_app_dropdown, "currentIndexChanged"
            ):
                self.health_app_dropdown.currentIndexChanged.connect(
                    self.config_manager._on_health_app_selected
                )

            # Connect the refresh apps button - now using self.refresh_apps_btn which has the correct reference
            if self.refresh_apps_btn and hasattr(self.refresh_apps_btn, "clicked"):
                try:
                    self.refresh_apps_btn.clicked.connect(
                        self.health_app_scanner.trigger_scan_for_health_apps
                    )
                except Exception as button_ex:
                    self.log_message(
                        f"ERROR connecting button signal: {button_ex}", "red"
                    )
                    logging.error(
                        f"Exception connecting button signal: {button_ex}",
                        exc_info=True,
                    )
            else:
                self.log_message(
                    "ERROR: refresh_apps_btn not available for connection", "red"
                )
                logging.error("refresh_apps_btn not available for connection")

            # Note: start_btn and stop_btn are already connected in ComponentFactory.create_control_buttons
            # They connect to self.start_crawler and self.stop_crawler (delegate methods)

            if self.clear_logs_btn and hasattr(self.clear_logs_btn, "clicked"):
                self.clear_logs_btn.clicked.connect(self.clear_logs)

            # Connect crawl mode change
            if "CRAWL_MODE" in self.config_widgets and hasattr(
                self.config_widgets["CRAWL_MODE"], "currentTextChanged"
            ):
                self.config_widgets["CRAWL_MODE"].currentTextChanged.connect(
                    self.config_manager._update_crawl_mode_inputs_state
                )

            # The button states are now initialized in the components class

        except Exception as e:
            logging.error(f"Error connecting signals: {e}")

    def _on_provider_or_model_changed(self, _=None):
        """Handle runtime provider/model change (delegated)."""
        provider = self.config_widgets["AI_PROVIDER"].currentText()
        model = self.config_widgets["DEFAULT_MODEL_TYPE"].currentText()
        self.agent_manager.switch_provider_model(provider, model)

    def _init_agent_assistant(self):
        """(Re)initialize the AgentAssistant (delegated)."""
        self.agent_assistant = self.agent_manager.init_agent()

    @slot()
    def clear_logs(self):
        """Clears the log output and AI trace logs."""
        if self.log_output:
            self.log_output.clear()
        
        if self.ai_input_log:
            self.ai_input_log.clear()
            self.ai_input_log.setPlaceholderText("Waiting for AI Input...")
            
        if self.ai_output_log:
            self.ai_output_log.clear()
            self.ai_output_log.setPlaceholderText("Waiting for AI Output/Response...")
            
        # Clear history
        self.ai_history = []
        if self.ai_history_dropdown:
            self.ai_history_dropdown.clear()
            
        self.log_message("Logs and AI Trace cleared.", "green")

    def update_ai_input(self, content: Union[str, Dict[str, str]]):
        """Update the AI Input log and create a new history entry.
        
        Args:
            content: The text (str) or structured data (dict) to display.
        """
        # Capture current screenshot path if available
        current_screenshot_path = None
        if hasattr(self, 'crawler_manager') and self.crawler_manager.current_screenshot:
            current_screenshot_path = self.crawler_manager.current_screenshot
            
        # Create new history entry
        step_num = len(self.ai_history) + 1
        new_entry = {
            'label': f"Interaction #{step_num}",
            'input': content, # Store whatever we got (dict or str)
            'output': "",  # Output will arrive later
            'screenshot': current_screenshot_path
        }
        
        # Check if user was viewing the latest interaction before adding new one
        was_viewing_latest = False
        if self.ai_history_dropdown:
            current_idx = self.ai_history_dropdown.currentIndex()
            # User is viewing latest if current index is the last item (or dropdown is empty)
            was_viewing_latest = (current_idx == len(self.ai_history) - 1) or len(self.ai_history) == 0
        
        self.ai_history.append(new_entry)
        
        # Update dropdown
        if self.ai_history_dropdown:
            self.ai_history_dropdown.blockSignals(True)
            self.ai_history_dropdown.addItem(new_entry['label'])
            
            # Only auto-switch to latest if user was already viewing the most recent interaction
            # This prevents interrupting user who is reviewing an older interaction
            if was_viewing_latest:
                self.ai_history_dropdown.setCurrentIndex(len(self.ai_history) - 1)
                # Update view only if we switched
                self._display_ai_input(content)
                if self.ai_output_log:
                    self.ai_output_log.clear()
            
            self.ai_history_dropdown.blockSignals(False)

    def _display_ai_input(self, content: Union[str, Dict[str, str]]):
        """Helper to render AI input with proper formatting."""
        if not self.ai_input_log:
            return

        # Try to parse string content as JSON or dict
        if isinstance(content, str):
            content = content.strip()
            # If it looks like a dict representation, try to eval or load it
            import json
            import ast
            try:
                # Try JSON first
                parsed = json.loads(content)
                content = parsed
            except json.JSONDecodeError:
                try:
                    # Try literal eval for python dict strings
                    if content.startswith("{") and content.endswith("}"):
                        parsed = ast.literal_eval(content)
                        content = parsed
                except Exception:
                    pass

        if isinstance(content, dict):
             # check for split visualization format
            if 'static_part' in content and 'dynamic_part' in content:
                # Structured content - use HTML for coloring
                static_part = content['static_part']
                dynamic_part = content['dynamic_part']
                
                # Escape HTML characters
                import html
                static_html = html.escape(static_part).replace('\n', '<br>')
                dynamic_html = html.escape(dynamic_part).replace('\n', '<br>')
                
                # Construct HTML: Static in gray, Dynamic in default/white
                html_content = f"""
                <div style="font-family: 'Consolas', 'Monaco', monospace; white-space: pre-wrap;">
                    <span style="color: #666666;">{static_html}</span>
                    <br><br>
                    <span style="color: #a9b7c6; font-weight: bold;">{dynamic_html}</span>
                </div>
                """
                self.ai_input_log.setHtml(html_content)
                return
            
            # Check for "full_prompt" key (seen in logs)
            if 'full_prompt' in content:
                # If it's just one big prompt string, display it cleanly
                # It might be double encoded
                raw_prompt = content['full_prompt']
                # recursively try to clean it if it looks like a stringified string
                self.ai_input_log.setText(str(raw_prompt))
                return

            # Otherwise, pretty print the dict
            import json
            try:
                pretty_json = json.dumps(content, indent=2)
                self.ai_input_log.setText(pretty_json)
            except Exception:
                self.ai_input_log.setText(str(content))
        else:
            # Clean up raw text if it has excessive escapes
            text_content = str(content)
            # Basic unescape if it looks like a python string literal
            if text_content.startswith("'") and text_content.endswith("'"):
                 text_content = text_content[1:-1].replace("\\n", "\n").replace('\\"', '"')
            elif text_content.startswith('"') and text_content.endswith('"'):
                 text_content = text_content[1:-1].replace("\\n", "\n").replace('\\"', '"')

            self.ai_input_log.setText(text_content)
            
        # Reset cursor
        cursor = self.ai_input_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        self.ai_input_log.setTextCursor(cursor)

    def update_ai_output(self, content: str):
        """Update the AI Output log for the latest interaction.
        
        Args:
            content: The text/JSON to display in the AI Output section.
        """
        # Try to format as JSON if possible and extract token info
        display_content = content
        token_info_header = ""
        import json
        try:
            if content and isinstance(content, str) and (content.strip().startswith("{") or content.strip().startswith("[")):
                parsed = json.loads(content)
                
                # Extract token count from _meta if available
                if isinstance(parsed, dict) and '_meta' in parsed:
                    meta = parsed['_meta']
                    if 'token_count' in meta:
                        token_count = meta['token_count']
                        # Format token info header
                        token_info_header = f"📊 Tokens Used: {token_count:,}\n" + ("─" * 50) + "\n\n"
                
                display_content = json.dumps(parsed, indent=2)
        except Exception:
            pass

        # Prepend token info if available
        if token_info_header:
            display_content = token_info_header + display_content

        if not self.ai_history:
            # Received output without input? Create a placeholder entry
             self.ai_history.append({
                'label': "Interaction #1 (Output Only)",
                'input': "(No input recorded)",
                'output': display_content, # Store formatted
                'screenshot': None
            })
             if self.ai_history_dropdown:
                self.ai_history_dropdown.blockSignals(True)
                self.ai_history_dropdown.addItem(self.ai_history[-1]['label'])
                self.ai_history_dropdown.setCurrentIndex(0)
                self.ai_history_dropdown.blockSignals(False)
        else:
            # Update the latest entry
            self.ai_history[-1]['output'] = display_content

        # Check if we are currently viewing the latest item
        is_latest_selected = True
        if self.ai_history_dropdown:
             current_idx = self.ai_history_dropdown.currentIndex()
             if current_idx != len(self.ai_history) - 1:
                 is_latest_selected = False
        
        # Only update view if we are looking at the latest item
        if is_latest_selected:
            if self.ai_output_log:
                self.ai_output_log.setText(display_content)
                cursor = self.ai_output_log.textCursor()
                cursor.movePosition(cursor.MoveOperation.Start)
                self.ai_output_log.setTextCursor(cursor)

    @slot(int)
    def _on_ai_history_selected(self, index: int):
        """Handle selection from history dropdown."""
        if index < 0 or index >= len(self.ai_history):
            return
            
        entry = self.ai_history[index]
        
        if self.ai_input_log:
            self._display_ai_input(entry['input'])
            
        if self.ai_output_log:
            self.ai_output_log.setText(entry['output'])
            # Reset cursor
            cursor = self.ai_output_log.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            self.ai_output_log.setTextCursor(cursor)
            
        # Update screenshot if available for this step
        if entry.get('screenshot'):
            self.update_screenshot(entry['screenshot'])

    def _attempt_load_cached_health_apps(self):
        """Tries to load health apps from the cached file path if it exists."""
        try:
            # If a health app list file is specified in the config
            if self.current_health_app_list_file:
                # Check if it's a relative path (doesn't start with drive letter or /)
                if not os.path.isabs(self.current_health_app_list_file):
                    # Convert to absolute path relative to the app directory
                    abs_path = os.path.join(
                        self.api_dir, self.current_health_app_list_file
                    )
                    self.current_health_app_list_file = abs_path

                if os.path.exists(self.current_health_app_list_file):
                    self.health_app_scanner._load_health_apps_from_file(
                        self.current_health_app_list_file
                    )
                    return
                else:
                    self.log_message(
                        f"Configured health app file not found: {self.current_health_app_list_file}",
                        "orange",
                    )

                    # No longer support generic alias files; proceed to resolve device-specific path

            # If we reach here, we need to find the health app file for the current device
            self.log_message(
                "Looking for health app list for the current device...", "blue"
            )
            device_id = self.health_app_scanner._get_current_device_id()
            device_file_path = self.health_app_scanner._get_device_health_app_file_path(
                device_id
            )

            if os.path.exists(device_file_path):
                self.log_message(
                    f"Found health app list for device {device_id}: {device_file_path}",
                    "green",
                )
                self.current_health_app_list_file = device_file_path
                self.health_app_scanner._load_health_apps_from_file(device_file_path)

                # Persist device-specific path in config
                # Use a relative path based on UI scanner's api_dir when available
                try:
                    rel_path = os.path.relpath(device_file_path, self.health_app_scanner.api_dir)
                except Exception:
                    rel_path = device_file_path
                self.config.update_setting_and_save(
                    "CURRENT_HEALTH_APP_LIST_FILE",
                    rel_path,
                )
                return

            # If no file exists for this device
            self.log_message(
                f"No health app list found for device {device_id}. Scan needed.",
                "orange",
            )
            # Store the path where the file would be created
            self.current_health_app_list_file = device_file_path

            # Persist expected device-specific path in config
            try:
                rel_path = os.path.relpath(device_file_path, self.health_app_scanner.api_dir)
            except Exception:
                rel_path = device_file_path
            self.config.update_setting_and_save(
                "CURRENT_HEALTH_APP_LIST_FILE",
                rel_path,
            )

            # Clear dropdown if no valid cache
            if self.health_app_dropdown and hasattr(self.health_app_dropdown, "clear"):
                try:
                    self.health_app_dropdown.clear()
                    self.health_app_dropdown.addItem(
                        "Select target app (Scan first)", None
                    )
                except Exception as e:
                    logging.error(f"Error updating health app dropdown: {e}")
            self.health_apps_data = []
        except Exception as e:
            logging.error(f"Error loading cached health apps: {e}", exc_info=True)
            self.log_message(f"Error loading cached health apps: {e}", "red")

    def _set_application_icon(self):
        """Set the application icon for window and taskbar."""
        try:
            # Get the application icon using LogoWidget
            app_icon = LogoWidget.get_icon(self.api_dir)

            if app_icon:
                # Set window icon (appears in taskbar)
                self.setWindowIcon(app_icon)
                # Set application icon (used by Windows taskbar)
                QApplication.setWindowIcon(app_icon)
            else:
                logging.warning("Failed to get application icon")
        except Exception as e:
            logging.error(f"Failed to set application icon: {e}")

    def _ensure_output_directories_exist(self):
        """Ensure that all necessary output directories exist."""
        try:
            # The config class now handles creating session-specific directories
            # We just need to ensure the base output directory exists
            output_base_dir = getattr(
                self.config,
                "OUTPUT_DATA_DIR",
                os.path.join(self.api_dir, "output_data"),
            )

            # Handle case where OUTPUT_DATA_DIR might be None
            if output_base_dir is None:
                output_base_dir = os.path.join(self.api_dir, "output_data")
                self.config.update_setting_and_save(
                    "OUTPUT_DATA_DIR", output_base_dir
                )

            # Create base output directory if it doesn't exist
            if not os.path.exists(output_base_dir):
                os.makedirs(output_base_dir)
                self.log_message(
                    f"Created base output directory: {output_base_dir}", "blue"
                )

            # The config class will create session-specific directories when paths are resolved
            # Update config with relative paths if using absolute paths
            self._update_relative_paths_in_config()

            # Persists automatically via SQLite-backed Config

        except Exception as e:
            logging.error(f"Error creating output directories: {e}", exc_info=True)
            if hasattr(self, "log_output") and self.log_output:
                self.log_message(f"Error creating output directories: {e}", "red")

    def _update_relative_paths_in_config(self):
        """Update any absolute paths in config to use relative paths."""
        try:
            # Define the paths to check and update
            path_settings = [
                "APP_INFO_OUTPUT_DIR",
                "SCREENSHOTS_DIR",
                "TRAFFIC_CAPTURE_OUTPUT_DIR",
                "LOG_DIR",
                "DB_NAME",
                "CURRENT_HEALTH_APP_LIST_FILE",
            ]

            # Process each path setting
            for setting_name in path_settings:
                current_value = self.config.get(setting_name, None)
                if current_value and os.path.isabs(current_value):
                    # Try to make it relative to the api_dir
                    try:
                        rel_path = os.path.relpath(current_value, self.api_dir)
                        # Only update if it's inside the api_dir hierarchy
                        if not rel_path.startswith(".."):
                            self.config.update_setting_and_save(
                                setting_name, rel_path
                            )
                    except ValueError:
                        # Different drives, can't make relative
                        pass

        except Exception as e:
            logging.error(
                f"Error updating relative paths in config: {e}", exc_info=True
            )

    def log_message(self, message: str, color: str = "white"):
        """Append a message to the log (delegated)."""
        if hasattr(self, 'log_manager'):
            self.log_manager.log_message(message, color)
        else:
            # Fallback for early logs during init
            pass


    def update_screenshot(self, file_path: str, is_blocked: bool = False) -> None:
        """Update the screenshot displayed in the UI."""
        try:
            if self.screenshot_label and hasattr(self.screenshot_label, "setPixmap"):
                update_screenshot(self.screenshot_label, file_path, is_blocked=is_blocked)
            else:
                logging.warning(
                    f"Screenshot label not properly initialized for update from: {file_path}"
                )
        except Exception as e:
            logging.error(f"Error updating screenshot: {e}")

    def closeEvent(self, event):
        """Handle the window close event."""
        # Stop crawler process if running
        if hasattr(self, "crawler_manager"):
            self.crawler_manager.stop_crawler()

        # Stop app scan process if running
        if hasattr(self.health_app_scanner, "find_apps_process"):
            find_apps_process = self.health_app_scanner.find_apps_process
            if (
                find_apps_process
                and find_apps_process.state() != QProcess.ProcessState.NotRunning
            ):
                self.log_message(
                    "Closing UI: Terminating app scan process...", "orange"
                )
                find_apps_process.terminate()
                if not find_apps_process.waitForFinished(5000):
                    self.log_message(
                        "App scan process did not terminate gracefully. Killing...",
                        "red",
                    )
                    find_apps_process.kill()

        # Stop MobSF test process if running
        if hasattr(self.mobsf_ui_manager, "mobsf_test_process"):
            mobsf_process = self.mobsf_ui_manager.mobsf_test_process
            if (
                mobsf_process
                and mobsf_process.state() != QProcess.ProcessState.NotRunning
            ):
                self.log_message(
                    "Closing UI: Terminating MobSF test process...", "orange"
                )
                mobsf_process.terminate()
                if not mobsf_process.waitForFinished(5000):
                    self.log_message(
                        "MobSF test process did not terminate gracefully. Killing...",
                        "red",
                    )
                    mobsf_process.kill()

        super().closeEvent(event)

    # Configuration synchronization method
    def _sync_user_config_files(self):
        """Synchronize user configuration files.
        
        This method is used as a callback when configuration settings are updated.
        Currently, synchronization is handled automatically by the config system,
        so this is a no-op method maintained for API compatibility.
        """
        # Configuration synchronization is now handled automatically by the config system
        # This method is kept for backward compatibility with existing callbacks
        pass
    
    # Delegate methods to appropriate managers
    @slot()
    def perform_pre_crawl_validation(self):
        """Perform pre-crawl validation checks."""
        if hasattr(self, 'crawler_manager') and self.crawler_manager:
            self.crawler_manager.perform_pre_crawl_validation()
        else:
            self.log_message("ERROR: Crawler manager not initialized", "red")
    
    @slot()
    def toggle_crawler_state(self):
        """Toggle crawler state between running and stopped."""
        if hasattr(self, 'crawler_manager') and self.crawler_manager:
            if self.crawler_manager.is_crawler_running():
                self.crawler_manager.stop_crawler()
            else:
                self.crawler_manager.start_crawler()
        else:
            self.log_message("ERROR: Crawler manager not initialized", "red")
    
    @slot()
    def generate_report(self):
        """Generate a PDF report (delegated)."""
        self.report_manager.generate_report()

    @slot()
    def open_session_folder(self):
        """Open the current session folder in file explorer (delegated)."""
        if hasattr(self, 'crawler_manager') and self.crawler_manager:
            self.crawler_manager.open_session_folder()
        else:
            self.log_message("ERROR: Crawler manager not initialized", "red")

    # _get_connected_devices removed as it's now handled by DeviceManager/DeviceDetection

    def _populate_device_dropdown(self):
        """Populate the device dropdown (delegated)."""
        self.device_manager.populate_devices()


if __name__ == "__main__":
    # Import LoggerManager for proper logging setup
    from utils.utils import LoggerManager

    # GUI initialization is now handled in interfaces/gui.py
    # This file contains the controller class only

