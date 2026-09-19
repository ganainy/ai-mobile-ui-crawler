"""Settings panel widget for mobile-crawler GUI."""

import logging
import os
import threading
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mobile_crawler.infrastructure.app_account_store import AppAccount
from mobile_crawler.ui.widgets.status_bar_exclusion_preview import StatusBarExclusionPreview

if TYPE_CHECKING:
    from mobile_crawler.infrastructure.user_config_store import UserConfigStore

logger = logging.getLogger(__name__)


DEFAULT_EXPLORATION_OBJECTIVE = (
    "Explore as much of the application as possible. Your primary goal is to maximize coverage "
    "by discovering and navigating to as many different screens, tabs, and distinct sections "
    "of the app as possible.\n\n"
    "Ensure you:\n"
    "1. Systematically click on menus, navigation bars, buttons, and links to uncover new pages.\n"
    "2. Avoid getting stuck in loops; if you find yourself on a screen you have already visited, "
    "backtrack or explore unexplored interactive elements.\n"
    "3. Actively fill in forms with placeholder data or interact with dialogues if they block access "
    "to deeper parts of the application.\n"
    "4. Keep mapping and discovering new layouts, settings panels, user profiles, and features "
    "to achieve maximum exploration depth and breadth."
)


class SettingsPanel(QWidget):
    """Widget for configuring crawler settings.

    Provides inputs for API keys, system prompt, crawl limits,
    and test credentials. Saves to user_config.db.
    """

    # Signal emitted when settings are saved
    settings_saved = Signal()  # type: ignore
    omniparser_keepalive_pinged = Signal(bool, str, float)  # type: ignore
    reset_layout_requested = Signal()  # type: ignore
    generate_guided_scenarios_requested = Signal()  # type: ignore
    delete_app_account_requested = Signal()  # type: ignore
    _status_bar_preview_captured = Signal(bytes)  # type: ignore
    _status_bar_preview_failed = Signal(str)  # type: ignore

    def __init__(self, config_store: "UserConfigStore", parent=None):
        """Initialize settings panel widget.

        Args:
            config_store: UserConfigStore instance for saving/loading settings
            parent: Parent widget
        """
        super().__init__(parent)
        self._config_store = config_store
        self._keepalive_timer = QTimer(self)
        self._keepalive_timer.timeout.connect(self._on_keepalive_tick)
        self._keepalive_thread: threading.Thread | None = None
        self._keepalive_in_flight = False
        self._crawl_running = False
        self._device_id: str | None = None
        self._status_bar_preview_device_id: str | None = None
        self._status_bar_preview_thread: threading.Thread | None = None
        self._status_bar_preview_in_flight = False
        self._setup_ui()
        self.omniparser_keepalive_pinged.connect(self._on_keepalive_pinged)
        self._status_bar_preview_captured.connect(self._on_status_bar_preview_captured)
        self._status_bar_preview_failed.connect(self._on_status_bar_preview_failed)
        self._load_settings()

    def _setup_ui(self):
        """Set up user interface."""
        main_layout = QVBoxLayout(self)

        # Main Tab Widget
        self.tab_widget = QTabWidget()

        # 1. General Tab (Limits, Screen Config, Credentials)
        self.tab_widget.addTab(self._setup_general_tab(), "General")

        # 2. AI Crawler Tab (Agent Setup, Exploration Objective)
        self.tab_widget.addTab(self._setup_ai_crawler_tab(), "AI Crawler")

        # 3. API Keys & Parsing Tab (AI Provider Keys, UI Parser)
        self.tab_widget.addTab(self._setup_api_keys_tab(), "API Keys & Parsing")

        # 4. Integrations Tab (Traffic, Video, MobSF, Tracing)
        self.tab_widget.addTab(self._setup_integrations_tab(), "Integrations")

        main_layout.addWidget(self.tab_widget, 1)

        # Save button in bottom area (stays visible regardless of tab)
        save_layout = QHBoxLayout()
        self.reset_layout_button = QPushButton("Reset Layout")
        self.reset_layout_button.setMinimumHeight(40)
        self.reset_layout_button.setToolTip(
            "Restore the panel/splitter layout to its default sizes "
            "(double-clicking a splitter handle resets just that one)."
        )
        self.reset_layout_button.clicked.connect(self.reset_layout_requested.emit)
        save_layout.addWidget(self.reset_layout_button)
        save_layout.addStretch()
        self.save_button = QPushButton("Save Settings")
        self.save_button.setMinimumHeight(40)
        self.save_button.setStyleSheet("font-weight: bold;")
        self.save_button.clicked.connect(self._on_save_clicked)
        save_layout.addWidget(self.save_button)
        main_layout.addLayout(save_layout)

    def _setup_general_tab(self) -> QWidget:
        """Create the General settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Group box for Crawl Limits
        limits_group = QGroupBox("Crawl Limits")
        limits_layout = QVBoxLayout()

        # Radio buttons for limit type selection
        self.limit_button_group = QButtonGroup(self)

        # Max Steps option
        max_steps_layout = QHBoxLayout()
        self.steps_radio = QRadioButton()
        self.steps_radio.setChecked(True)
        self.limit_button_group.addButton(self.steps_radio, 0)
        max_steps_layout.addWidget(self.steps_radio)
        max_steps_label = QLabel("Max Steps:")
        max_steps_layout.addWidget(max_steps_label)
        self.max_steps_input = QSpinBox()
        self.max_steps_input.setRange(1, 10000)
        self.max_steps_input.setValue(100)
        self.max_steps_input.setSingleStep(1)
        max_steps_layout.addWidget(self.max_steps_input)
        max_steps_layout.addStretch()
        limits_layout.addLayout(max_steps_layout)

        # Max Duration option
        max_duration_layout = QHBoxLayout()
        self.duration_radio = QRadioButton()
        self.limit_button_group.addButton(self.duration_radio, 1)
        max_duration_layout.addWidget(self.duration_radio)
        max_duration_label = QLabel("Max Duration (seconds):")
        max_duration_layout.addWidget(max_duration_label)
        self.max_duration_input = QSpinBox()
        self.max_duration_input.setRange(10, 3600)
        self.max_duration_input.setValue(300)
        self.max_duration_input.setSingleStep(5)
        self.max_duration_input.setEnabled(False)
        max_duration_layout.addWidget(self.max_duration_input)
        max_duration_layout.addStretch()
        limits_layout.addLayout(max_duration_layout)

        self.steps_radio.toggled.connect(self._on_limit_type_changed)
        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)

        # Group box for Screen Configuration
        screen_group = QGroupBox("Screen Configuration")
        screen_layout = QVBoxLayout()

        top_bar_layout = QHBoxLayout()
        top_bar_label = QLabel("Exclude Top Bar (pixels):")
        top_bar_layout.addWidget(top_bar_label)
        self.top_bar_height_input = QSpinBox()
        self.top_bar_height_input.setRange(0, 500)
        self.top_bar_height_input.setValue(80)
        self.top_bar_height_input.setToolTip(
            "Exclude the Android status bar from OCR and AI analysis. Typically 80-120px."
        )
        top_bar_layout.addWidget(self.top_bar_height_input)
        self.screenshot_refresh_button = QPushButton("Refresh")
        self.screenshot_refresh_button.setToolTip("Take a fresh screenshot from the connected device.")
        self.screenshot_refresh_button.clicked.connect(self._fetch_status_bar_preview)
        top_bar_layout.addWidget(self.screenshot_refresh_button)
        top_bar_layout.addStretch()
        screen_layout.addLayout(top_bar_layout)

        bottom_bar_layout = QHBoxLayout()
        bottom_bar_label = QLabel("Exclude Bottom Bar (pixels):")
        bottom_bar_layout.addWidget(bottom_bar_label)
        self.bottom_bar_height_input = QSpinBox()
        self.bottom_bar_height_input.setRange(0, 500)
        self.bottom_bar_height_input.setValue(0)
        self.bottom_bar_height_input.setToolTip(
            "Exclude the Android navigation bar from OCR and AI analysis. 0 if you use gesture navigation."
        )
        bottom_bar_layout.addWidget(self.bottom_bar_height_input)
        bottom_bar_layout.addStretch()
        screen_layout.addLayout(bottom_bar_layout)

        self.screenshot_preview = StatusBarExclusionPreview()
        self.screenshot_preview.top_exclusion_changed.connect(self.top_bar_height_input.setValue)
        self.top_bar_height_input.valueChanged.connect(self.screenshot_preview.set_top_exclusion_px)
        self.screenshot_preview.bottom_exclusion_changed.connect(self.bottom_bar_height_input.setValue)
        self.bottom_bar_height_input.valueChanged.connect(self.screenshot_preview.set_bottom_exclusion_px)
        preview_row = QHBoxLayout()
        preview_row.addWidget(self.screenshot_preview)
        preview_row.addStretch()
        screen_layout.addLayout(preview_row)

        screen_group.setLayout(screen_layout)
        layout.addWidget(screen_group)

        # Test Credentials group
        credentials_group = QGroupBox("Form Fill Data")
        credentials_layout = QVBoxLayout()
        credentials_layout.setSpacing(12)
        credentials_layout.setContentsMargins(15, 20, 15, 20)

        def create_credential_field(label_text, placeholder, is_password=False):
            field_layout = QVBoxLayout()
            field_layout.setSpacing(4)
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold;")
            field_layout.addWidget(label)
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            edit.setMinimumHeight(30)
            if is_password:
                edit.setEchoMode(QLineEdit.EchoMode.Password)
            field_layout.addWidget(edit)
            return field_layout, edit

        # 1. Address field with German default mock value
        field_layout, self.test_address_input = create_credential_field(
            "Test Address:", "e.g. Kaiserstraße 12, 60311 Frankfurt am Main, Germany"
        )
        self.test_address_input.setText("Kaiserstraße 12, 60311 Frankfurt am Main, Germany")
        self.test_address_input.setToolTip("Default test address used for forms")
        credentials_layout.addLayout(field_layout)

        # 2. Email address field with a hint
        field_layout, self.test_email_input = create_credential_field("Test Email Address:", "Enter test email address")
        self.test_email_input.setText("testuser@example.com")
        self.test_email_input.setToolTip("Enter a real email address if you need to receive verification codes or OTPs")
        email_hint = QLabel("💡 Tip: Provide a real email address if the target app requires email verification/OTP.")
        email_hint.setStyleSheet("color: #aa6600; font-size: 10px; font-style: italic;")
        email_hint.setWordWrap(True)
        field_layout.addWidget(email_hint)
        credentials_layout.addLayout(field_layout)

        # 3. Mobile Number field with a hint
        field_layout, self.test_phone_input = create_credential_field("Test Mobile Number:", "e.g. +49 170 1234567")
        self.test_phone_input.setToolTip("Enter a real mobile number if you need to receive SMS verification/MFA codes")
        phone_hint = QLabel("💡 Tip: Provide a real mobile number if the target app requires SMS MFA/verification.")
        phone_hint.setStyleSheet("color: #aa6600; font-size: 10px; font-style: italic;")
        phone_hint.setWordWrap(True)
        field_layout.addWidget(phone_hint)
        credentials_layout.addLayout(field_layout)

        credentials_group.setLayout(credentials_layout)
        layout.addWidget(credentials_group)

        # Verification Inbox group (Gmail over IMAP)
        inbox_group = QGroupBox("Verification Inbox")
        inbox_layout = QVBoxLayout()
        inbox_layout.setSpacing(8)
        inbox_layout.setContentsMargins(15, 20, 15, 20)

        inbox_hint = QLabel(
            "Gmail inbox the crawler reads over IMAP to get email verification codes and links. "
            "Use a dedicated test account, not your personal one. Create an app password "
            "(Google Account > Security > 2-Step Verification > App passwords) and enable IMAP in Gmail. "
            "Sign-up addresses default to name+<package>@gmail.com."
        )
        inbox_hint.setWordWrap(True)
        inbox_hint.setStyleSheet("color: #666; font-size: 11px;")
        inbox_layout.addWidget(inbox_hint)

        self.verification_inbox_address_input = QLineEdit()
        self.verification_inbox_address_input.setPlaceholderText("name@gmail.com")
        inbox_layout.addWidget(QLabel("Gmail address:"))
        inbox_layout.addWidget(self.verification_inbox_address_input)

        self.verification_inbox_password_input = QLineEdit()
        self.verification_inbox_password_input.setPlaceholderText("App password")
        self.verification_inbox_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        inbox_layout.addWidget(QLabel("App password:"))
        inbox_layout.addWidget(self.verification_inbox_password_input)

        inbox_group.setLayout(inbox_layout)
        layout.addWidget(inbox_group)

        layout.addStretch()
        return self._wrap_in_scroll_area(tab)

    def _setup_ai_crawler_tab(self) -> QWidget:
        """Create the AI Crawler settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # Crawler Agent group
        crawler_group = QGroupBox("Crawler Agent")
        crawler_layout = QVBoxLayout()
        crawler_layout.setSpacing(12)
        crawler_layout.setContentsMargins(15, 20, 15, 20)

        self.crawler_reasoning_checkbox = QCheckBox("Use Reasoning Mode")
        self.crawler_reasoning_checkbox.setToolTip(
            "Enable complex planning with ManagerAgent -> ExecutorAgent cycles (vs direct execution)"
        )
        self.crawler_reasoning_checkbox.setChecked(True)
        crawler_layout.addWidget(self.crawler_reasoning_checkbox)

        self.crawler_streaming_checkbox = QCheckBox("Enable Streaming Output")
        self.crawler_streaming_checkbox.setToolTip("Show real-time agent planning and execution updates")
        crawler_layout.addWidget(self.crawler_streaming_checkbox)

        retry_layout = QHBoxLayout()
        retry_layout.addWidget(QLabel("Agent Retry Count:"))
        self.crawler_retry_count_input = QSpinBox()
        self.crawler_retry_count_input.setRange(0, 10)
        self.crawler_retry_count_input.setValue(2)
        self.crawler_retry_count_input.setToolTip("Number of retries for failed agent operations")
        retry_layout.addWidget(self.crawler_retry_count_input)
        retry_layout.addStretch()
        crawler_layout.addLayout(retry_layout)

        crawler_group.setLayout(crawler_layout)
        layout.addWidget(crawler_group)

        # Exploration Objective group
        objective_group = QGroupBox("Exploration Objective")
        objective_layout = QVBoxLayout()
        objective_layout.setSpacing(8)
        objective_layout.setContentsMargins(15, 20, 15, 20)

        objective_hint = QLabel(
            "This prompt is sent to the agent as the exploration goal. Edit to customize exploration behavior."
        )
        objective_hint.setWordWrap(True)
        objective_hint.setStyleSheet("color: #666; font-size: 11px;")
        objective_layout.addWidget(objective_hint)

        self.exploration_objective_input = QTextEdit()
        self.exploration_objective_input.setMinimumHeight(120)
        objective_layout.addWidget(self.exploration_objective_input)

        # Reset button layout
        reset_layout = QHBoxLayout()
        reset_layout.addStretch()
        self.reset_objective_button = QPushButton("Reset to Default")
        self.reset_objective_button.setToolTip(
            "Reset the exploration objective prompt to the default coverage maximization prompt"
        )
        self.reset_objective_button.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #555;
                color: #ccc;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #333;
                border-color: #777;
                color: #fff;
            }
            QPushButton:pressed {
                background-color: #222;
            }
        """
        )
        self.reset_objective_button.clicked.connect(self._reset_exploration_objective)
        reset_layout.addWidget(self.reset_objective_button)
        objective_layout.addLayout(reset_layout)

        objective_group.setLayout(objective_layout)
        layout.addWidget(objective_group, 1)

        # Guided Scenarios group
        guided_scenarios_group = QGroupBox("Guided Scenarios")
        guided_scenarios_layout = QVBoxLayout()
        guided_scenarios_layout.setSpacing(8)
        guided_scenarios_layout.setContentsMargins(15, 20, 15, 20)

        guided_scenarios_hint = QLabel(
            "An ordered checklist of pages/flows the crawler must visit before free exploration. "
            "Generate it from the app's Play Store listing and website, or edit it by hand. "
            "Persisted per app — reselecting this app later reloads it."
        )
        guided_scenarios_hint.setWordWrap(True)
        guided_scenarios_hint.setStyleSheet("color: #666; font-size: 11px;")
        guided_scenarios_layout.addWidget(guided_scenarios_hint)

        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Website URL:"))
        self.guided_scenarios_url_input = QLineEdit()
        self.guided_scenarios_url_input.setPlaceholderText(
            "Auto-filled from the Play Store listing when available; override here"
        )
        url_layout.addWidget(self.guided_scenarios_url_input)
        guided_scenarios_layout.addLayout(url_layout)

        generate_layout = QHBoxLayout()
        self.generate_guided_scenarios_button = QPushButton("Generate from App Info")
        self.generate_guided_scenarios_button.setToolTip(
            "Fetch the app's Play Store description and website, then ask the AI to propose a checklist. "
            "Replaces the current list."
        )
        self.generate_guided_scenarios_button.clicked.connect(self.generate_guided_scenarios_requested.emit)
        generate_layout.addWidget(self.generate_guided_scenarios_button)
        generate_layout.addStretch()
        guided_scenarios_layout.addLayout(generate_layout)

        self.guided_scenarios_warning_label = QLabel("")
        self.guided_scenarios_warning_label.setWordWrap(True)
        self.guided_scenarios_warning_label.setStyleSheet("color: #d9822b; font-size: 11px;")
        self.guided_scenarios_warning_label.setVisible(False)
        guided_scenarios_layout.addWidget(self.guided_scenarios_warning_label)

        self.guided_scenarios_list = QListWidget()
        self.guided_scenarios_list.setMinimumHeight(140)
        self.guided_scenarios_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.guided_scenarios_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        guided_scenarios_layout.addWidget(self.guided_scenarios_list)

        list_buttons_layout = QHBoxLayout()
        self.guided_scenario_add_button = QPushButton("Add")
        self.guided_scenario_add_button.clicked.connect(self._add_guided_scenario)
        list_buttons_layout.addWidget(self.guided_scenario_add_button)

        self.guided_scenario_remove_button = QPushButton("Remove")
        self.guided_scenario_remove_button.clicked.connect(self._remove_selected_guided_scenario)
        list_buttons_layout.addWidget(self.guided_scenario_remove_button)

        self.guided_scenario_up_button = QPushButton("Move Up")
        self.guided_scenario_up_button.clicked.connect(lambda: self._move_guided_scenario(-1))
        list_buttons_layout.addWidget(self.guided_scenario_up_button)

        self.guided_scenario_down_button = QPushButton("Move Down")
        self.guided_scenario_down_button.clicked.connect(lambda: self._move_guided_scenario(1))
        list_buttons_layout.addWidget(self.guided_scenario_down_button)

        list_buttons_layout.addStretch()
        guided_scenarios_layout.addLayout(list_buttons_layout)

        guided_scenarios_group.setLayout(guided_scenarios_layout)
        layout.addWidget(guided_scenarios_group, 1)

        # App Account group (per selected app)
        app_account_group = QGroupBox("App Account")
        app_account_layout = QVBoxLayout()
        app_account_layout.setSpacing(8)
        app_account_layout.setContentsMargins(15, 20, 15, 20)

        app_account_hint = QLabel(
            "Login the crawler uses for the selected app. Each app has its own account; "
            "there is no global fallback. Leave the username empty for no account."
        )
        app_account_hint.setWordWrap(True)
        app_account_hint.setStyleSheet("color: #666; font-size: 11px;")
        app_account_layout.addWidget(app_account_hint)

        self.app_account_username_input = QLineEdit()
        self.app_account_username_input.setPlaceholderText("Username or email")
        app_account_layout.addWidget(QLabel("Username / Email:"))
        app_account_layout.addWidget(self.app_account_username_input)

        self.app_account_password_input = QLineEdit()
        self.app_account_password_input.setPlaceholderText("Password")
        self.app_account_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        app_account_layout.addWidget(QLabel("Password:"))
        app_account_layout.addWidget(self.app_account_password_input)

        self.app_account_address_input = QLineEdit()
        self.app_account_address_input.setPlaceholderText("Optional email address override")
        app_account_layout.addWidget(QLabel("Address override:"))
        app_account_layout.addWidget(self.app_account_address_input)

        self.app_account_delete_button = QPushButton("Delete Account")
        self.app_account_delete_button.clicked.connect(self.delete_app_account_requested.emit)
        app_account_layout.addWidget(self.app_account_delete_button, alignment=Qt.AlignmentFlag.AlignLeft)

        app_account_group.setLayout(app_account_layout)
        layout.addWidget(app_account_group)

        return self._wrap_in_scroll_area(tab)

    def _setup_api_keys_tab(self) -> QWidget:
        """Create the API Keys & Parsing settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # Group box for API Keys
        api_keys_group = QGroupBox("AI Provider Keys")
        api_keys_layout = QVBoxLayout()

        # Gemini API Key
        gemini_layout = QHBoxLayout()
        gemini_label = QLabel("Gemini API Key:")
        gemini_layout.addWidget(gemini_label)
        self.gemini_api_key_input = QLineEdit()
        self.gemini_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_api_key_input.setPlaceholderText("Enter Gemini API key")
        gemini_layout.addWidget(self.gemini_api_key_input)
        api_keys_layout.addLayout(gemini_layout)

        # OpenRouter API Key
        openrouter_layout = QHBoxLayout()
        openrouter_label = QLabel("OpenRouter API Key:")
        openrouter_layout.addWidget(openrouter_label)
        self.openrouter_api_key_input = QLineEdit()
        self.openrouter_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.openrouter_api_key_input.setPlaceholderText("Enter OpenRouter API key")
        openrouter_layout.addWidget(self.openrouter_api_key_input)
        api_keys_layout.addLayout(openrouter_layout)

        api_keys_group.setLayout(api_keys_layout)
        layout.addWidget(api_keys_group)

        # UI Parser group
        parser_group = QGroupBox("UI Parser")
        parser_layout = QVBoxLayout()

        parser_mode_layout = QHBoxLayout()
        parser_mode_layout.addWidget(QLabel("Parser Mode:"))
        self.ui_parser_mode_combo = QComboBox()
        self.ui_parser_mode_combo.addItems(["boost", "omniparser", "accessibility"])
        self.ui_parser_mode_combo.setCurrentText("boost")
        self.ui_parser_mode_combo.setToolTip(
            "UI parser mode: 'boost' (recommended, accessibility tree first with OmniParser fallback), "
            "'omniparser' (vision-only), or 'accessibility' (a11y-only)."
        )
        parser_mode_layout.addWidget(self.ui_parser_mode_combo)
        parser_mode_layout.addStretch()
        parser_layout.addLayout(parser_mode_layout)
        parser_approach_hint = QLabel(
            "The agent mainly uses Android Accessibility APIs. In 'boost' mode it uses the a11y tree first, "
            "and falls back to OmniParser only when accessibility metadata is missing or weak."
        )
        parser_approach_hint.setWordWrap(True)
        parser_approach_hint.setStyleSheet("color: #666; font-size: 11px;")
        parser_layout.addWidget(parser_approach_hint)

        # Backend selection (Replicate API vs Local Server)
        backend_layout = QHBoxLayout()
        backend_layout.addWidget(QLabel("OmniParser Backend:"))
        self.omniparser_backend_combo = QComboBox()
        self.omniparser_backend_combo.addItems(["replicate", "local"])
        self.omniparser_backend_combo.setCurrentText("replicate")
        self.omniparser_backend_combo.setToolTip(
            "Select where OmniParser runs: 'replicate' (Cloud API) or 'local' (Local FastAPI server)"
        )
        backend_layout.addWidget(self.omniparser_backend_combo)
        backend_layout.addStretch()
        parser_layout.addLayout(backend_layout)

        # Local URL (only visible/enabled when local backend is selected)
        self.local_url_container = QWidget()
        local_url_layout = QHBoxLayout()
        local_url_layout.setContentsMargins(0, 0, 0, 0)
        local_url_layout.addWidget(QLabel("Local OmniParser URL:"))
        self.omniparser_local_url_input = QLineEdit()
        self.omniparser_local_url_input.setText("http://localhost:8001")
        self.omniparser_local_url_input.setPlaceholderText("e.g. http://localhost:8001")
        self.omniparser_local_url_input.setToolTip("Local server URL for OmniParser (must include port)")
        local_url_layout.addWidget(self.omniparser_local_url_input)
        self.local_url_container.setLayout(local_url_layout)
        parser_layout.addWidget(self.local_url_container)

        self.local_timeout_container = QWidget()
        local_timeout_layout = QHBoxLayout()
        local_timeout_layout.setContentsMargins(0, 0, 0, 0)
        local_timeout_layout.addWidget(QLabel("Local Parse Timeout (seconds):"))
        self.omniparser_local_parse_timeout_input = QSpinBox()
        self.omniparser_local_parse_timeout_input.setRange(5, 600)
        self.omniparser_local_parse_timeout_input.setValue(120)
        self.omniparser_local_parse_timeout_input.setSingleStep(5)
        self.omniparser_local_parse_timeout_input.setToolTip(
            "Maximum time to wait for one local OmniParser parse. CPU runs can take 40+ seconds."
        )
        local_timeout_layout.addWidget(self.omniparser_local_parse_timeout_input)
        local_timeout_layout.addStretch()
        self.local_timeout_container.setLayout(local_timeout_layout)
        parser_layout.addWidget(self.local_timeout_container)

        # Replicate API Key (only visible/enabled when replicate backend is selected)
        self.replicate_container = QWidget()
        replicate_layout = QHBoxLayout()
        replicate_layout.setContentsMargins(0, 0, 0, 0)
        replicate_layout.addWidget(QLabel("Replicate API Key:"))
        self.replicate_api_key_input = QLineEdit()
        self.replicate_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.replicate_api_key_input.setPlaceholderText("Enter Replicate API key for OmniParser")
        self.replicate_api_key_input.setToolTip("API key for Replicate (used by OmniParser vision model)")
        replicate_layout.addWidget(self.replicate_api_key_input)
        self.replicate_container.setLayout(replicate_layout)
        parser_layout.addWidget(self.replicate_container)

        # Automatic keep-alive for the Replicate backend
        self.replicate_keepalive_container = QWidget()
        keepalive_layout = QHBoxLayout()
        keepalive_layout.setContentsMargins(0, 0, 0, 0)
        self.omniparser_keepalive_checkbox = QCheckBox("Keep Replicate OmniParser warm automatically")
        self.omniparser_keepalive_checkbox.setToolTip(
            "Periodically send a mock screenshot to Replicate OmniParser so the backend "
            "never fully cold-starts while this app is open."
        )
        self.omniparser_keepalive_checkbox.toggled.connect(self._apply_keepalive_state)
        keepalive_layout.addWidget(self.omniparser_keepalive_checkbox)
        keepalive_layout.addWidget(QLabel("every"))
        self.omniparser_keepalive_interval_input = QSpinBox()
        self.omniparser_keepalive_interval_input.setRange(1, 30)
        self.omniparser_keepalive_interval_input.setValue(3)
        self.omniparser_keepalive_interval_input.setSuffix(" min")
        self.omniparser_keepalive_interval_input.valueChanged.connect(self._apply_keepalive_state)
        keepalive_layout.addWidget(self.omniparser_keepalive_interval_input)
        self.replicate_keepalive_container.setLayout(keepalive_layout)
        parser_layout.addWidget(self.replicate_keepalive_container)

        self.omniparser_keepalive_status_label = QLabel("Keep-alive: idle")
        self.omniparser_keepalive_status_label.setStyleSheet("color: #666; font-size: 11px;")
        self.omniparser_keepalive_status_label.setWordWrap(True)
        parser_layout.addWidget(self.omniparser_keepalive_status_label)

        # Toggle visibility based on selected backend
        def toggle_omniparser_backend(backend):
            self.local_url_container.setVisible(backend == "local")
            self.local_timeout_container.setVisible(backend == "local")
            self.replicate_container.setVisible(backend == "replicate")
            self.replicate_keepalive_container.setVisible(backend == "replicate")
            self.omniparser_keepalive_status_label.setVisible(backend == "replicate")
            self._apply_keepalive_state()

        self.omniparser_backend_combo.currentTextChanged.connect(toggle_omniparser_backend)
        # Initialize default state
        toggle_omniparser_backend(self.omniparser_backend_combo.currentText())

        parser_group.setLayout(parser_layout)
        layout.addWidget(parser_group)

        layout.addStretch()
        return self._wrap_in_scroll_area(tab)

    def _setup_integrations_tab(self) -> QWidget:
        """Create the Integrations tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Traffic Capture
        traffic_capture_group = QGroupBox("Traffic Capture (PCAPdroid)")
        traffic_capture_layout = QVBoxLayout()
        self.enable_traffic_capture_checkbox = QCheckBox("Enable Traffic Capture")
        traffic_capture_layout.addWidget(self.enable_traffic_capture_checkbox)

        pcap_key_layout = QHBoxLayout()
        pcap_key_label = QLabel("API Key:")
        pcap_key_layout.addWidget(pcap_key_label)
        self.pcapdroid_api_key_input = QLineEdit()
        self.pcapdroid_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pcapdroid_api_key_input.setEnabled(False)
        pcap_key_layout.addWidget(self.pcapdroid_api_key_input)
        traffic_capture_layout.addLayout(pcap_key_layout)

        self.enable_traffic_capture_checkbox.toggled.connect(self._on_traffic_capture_toggled)
        traffic_capture_group.setLayout(traffic_capture_layout)
        layout.addWidget(traffic_capture_group)

        # Video Recording
        video_group = QGroupBox("Video Recording")
        video_layout = QVBoxLayout()
        self.enable_video_recording_checkbox = QCheckBox("Enable Video Recording")
        video_layout.addWidget(self.enable_video_recording_checkbox)
        video_group.setLayout(video_layout)
        layout.addWidget(video_group)

        # MobSF Analysis
        mobsf_group = QGroupBox("MobSF Static Analysis")
        mobsf_layout = QVBoxLayout()
        self.enable_mobsf_analysis_checkbox = QCheckBox("Enable MobSF Analysis")
        mobsf_layout.addWidget(self.enable_mobsf_analysis_checkbox)

        self.auto_run_mobsf_after_crawl_checkbox = QCheckBox("Automatically run after each successful crawl")
        self.auto_run_mobsf_after_crawl_checkbox.setEnabled(False)
        mobsf_layout.addWidget(self.auto_run_mobsf_after_crawl_checkbox)

        mobsf_url_layout = QHBoxLayout()
        mobsf_url_layout.addWidget(QLabel("API URL:"))
        self.mobsf_api_url_input = QLineEdit()
        self.mobsf_api_url_input.setPlaceholderText("http://localhost:8001")
        self.mobsf_api_url_input.setEnabled(False)
        mobsf_url_layout.addWidget(self.mobsf_api_url_input)
        mobsf_layout.addLayout(mobsf_url_layout)

        mobsf_hint = QLabel(
            "Run MobSF automatically after each successful crawl, or manually from Run "
            "History by selecting a completed run and clicking 'Run MobSF'."
        )
        mobsf_hint.setWordWrap(True)
        mobsf_hint.setStyleSheet("color: #666; font-size: 11px;")
        mobsf_layout.addWidget(mobsf_hint)

        self.enable_mobsf_analysis_checkbox.toggled.connect(self._on_mobsf_toggled)
        mobsf_group.setLayout(mobsf_layout)
        layout.addWidget(mobsf_group)

        # Agent Execution Tracing
        tracing_group = QGroupBox("Agent Execution Tracing")
        tracing_layout = QVBoxLayout()

        self.enable_tracing_checkbox = QCheckBox("Enable Tracing (OpenTelemetry)")
        self.enable_tracing_checkbox.setToolTip(
            "Enable telemetry tracing for agent steps, tool calls, and token usage metrics."
        )
        tracing_layout.addWidget(self.enable_tracing_checkbox)

        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("Provider:"))
        self.tracing_provider_combo = QComboBox()
        self.tracing_provider_combo.addItems(["phoenix", "langfuse"])
        self.tracing_provider_combo.setToolTip(
            "Tracing provider: 'phoenix' (local dashboard) or 'langfuse' (cloud monitoring)"
        )
        provider_layout.addWidget(self.tracing_provider_combo)
        provider_layout.addStretch()
        tracing_layout.addLayout(provider_layout)

        # Phoenix configuration widget
        self.phoenix_widget = QWidget()
        phoenix_layout = QHBoxLayout(self.phoenix_widget)
        phoenix_layout.setContentsMargins(0, 0, 0, 0)
        phoenix_layout.addWidget(QLabel("Phoenix URL:"))
        self.phoenix_url_input = QLineEdit()
        self.phoenix_url_input.setPlaceholderText("http://localhost:6006")
        self.phoenix_url_input.setToolTip("Arize Phoenix local server URL")
        phoenix_layout.addWidget(self.phoenix_url_input)
        tracing_layout.addWidget(self.phoenix_widget)

        self.phoenix_hint = QLabel(
            "Phoenix does not start automatically. Run `phoenix serve` in a separate "
            "terminal first, then view traces at this URL in your browser."
        )
        self.phoenix_hint.setWordWrap(True)
        self.phoenix_hint.setStyleSheet("color: #666; font-size: 11px;")
        tracing_layout.addWidget(self.phoenix_hint)

        # Langfuse configuration widget
        self.langfuse_widget = QWidget()
        langfuse_layout = QVBoxLayout(self.langfuse_widget)
        langfuse_layout.setContentsMargins(0, 0, 0, 0)

        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel("Host URL:"))
        self.langfuse_host_input = QLineEdit()
        self.langfuse_host_input.setPlaceholderText("https://cloud.langfuse.com")
        host_layout.addWidget(self.langfuse_host_input)
        langfuse_layout.addLayout(host_layout)

        pub_key_layout = QHBoxLayout()
        pub_key_layout.addWidget(QLabel("Public Key:"))
        self.langfuse_pub_key_input = QLineEdit()
        self.langfuse_pub_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.langfuse_pub_key_input.setPlaceholderText("pk-lf-...")
        pub_key_layout.addWidget(self.langfuse_pub_key_input)
        langfuse_layout.addLayout(pub_key_layout)

        secret_key_layout = QHBoxLayout()
        secret_key_layout.addWidget(QLabel("Secret Key:"))
        self.langfuse_secret_key_input = QLineEdit()
        self.langfuse_secret_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.langfuse_secret_key_input.setPlaceholderText("sk-lf-...")
        secret_key_layout.addWidget(self.langfuse_secret_key_input)
        langfuse_layout.addLayout(secret_key_layout)

        langfuse_hint = QLabel(
            "Traces are sent to your Langfuse cloud project. Copy the Host URL, Public Key, "
            "and Secret Key from your Langfuse project settings, then view traces in the "
            "Langfuse dashboard."
        )
        langfuse_hint.setWordWrap(True)
        langfuse_hint.setStyleSheet("color: #666; font-size: 11px;")
        langfuse_layout.addWidget(langfuse_hint)

        tracing_layout.addWidget(self.langfuse_widget)

        # Connect signals
        self.enable_tracing_checkbox.toggled.connect(self._on_tracing_toggled)
        self.tracing_provider_combo.currentTextChanged.connect(self._on_tracing_provider_changed)

        tracing_group.setLayout(tracing_layout)
        layout.addWidget(tracing_group)

        layout.addStretch()
        return self._wrap_in_scroll_area(tab)

    def _wrap_in_scroll_area(self, widget: QWidget) -> QWidget:
        """Wrap a widget in a QScrollArea for handling small screens."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        return scroll

    def _on_limit_type_changed(self, checked: bool):
        """Handle limit type radio button toggle.

        Args:
            checked: Whether steps radio is checked
        """
        if checked:
            # Steps is selected
            self.max_steps_input.setEnabled(True)
            self.max_duration_input.setEnabled(False)
        else:
            # Duration is selected
            self.max_steps_input.setEnabled(False)
            self.max_duration_input.setEnabled(True)

    def _on_traffic_capture_toggled(self, checked: bool):
        """Handle traffic capture checkbox toggle.

        Args:
            checked: Whether traffic capture is enabled
        """
        self.pcapdroid_api_key_input.setEnabled(checked)

    def _on_mobsf_toggled(self, checked: bool):
        """Handle MobSF analysis checkbox toggle.

        Args:
            checked: Whether MobSF analysis is enabled
        """
        self.mobsf_api_url_input.setEnabled(checked)
        self.auto_run_mobsf_after_crawl_checkbox.setEnabled(checked)

    def _on_tracing_toggled(self, checked: bool):
        """Handle tracing enabled checkbox toggle."""
        self.tracing_provider_combo.setEnabled(checked)
        if checked:
            self._on_tracing_provider_changed(self.tracing_provider_combo.currentText())
        else:
            self.phoenix_widget.setEnabled(False)
            self.langfuse_widget.setEnabled(False)
            self.phoenix_hint.setVisible(False)

    def _on_tracing_provider_changed(self, provider: str):
        """Handle tracing provider combobox change."""
        if not self.enable_tracing_checkbox.isChecked():
            self.phoenix_widget.setEnabled(False)
            self.langfuse_widget.setEnabled(False)
            self.phoenix_hint.setVisible(False)
            return

        if provider == "phoenix":
            self.phoenix_widget.setVisible(True)
            self.phoenix_widget.setEnabled(True)
            self.phoenix_hint.setVisible(True)
            self.langfuse_widget.setVisible(False)
            self.langfuse_widget.setEnabled(False)
        else:
            self.phoenix_widget.setVisible(False)
            self.phoenix_widget.setEnabled(False)
            self.phoenix_hint.setVisible(False)
            self.langfuse_widget.setVisible(True)
            self.langfuse_widget.setEnabled(True)

    def _load_settings(self):
        """Load settings from user_config.db."""
        # Load API keys (None if not found or decryption fails)
        gemini_key = self._config_store.get_secret_plaintext("gemini_api_key")
        if gemini_key:
            self.gemini_api_key_input.setText(gemini_key)
        else:
            self.gemini_api_key_input.setText("")  # Clear field if no valid key

        openrouter_key = self._config_store.get_secret_plaintext("openrouter_api_key")
        if openrouter_key:
            self.openrouter_api_key_input.setText(openrouter_key)
        else:
            self.openrouter_api_key_input.setText("")  # Clear field if no valid key

        # Load crawl limits
        max_steps = self._config_store.get_setting("max_steps", default=100)
        self.max_steps_input.setValue(max_steps)

        max_duration = self._config_store.get_setting("max_duration_seconds", default=300)
        self.max_duration_input.setValue(max_duration)

        # Load screen configuration
        top_bar_height = self._config_store.get_setting("top_bar_height", default=80)
        self.top_bar_height_input.setValue(top_bar_height)
        bottom_bar_height = self._config_store.get_setting("bottom_bar_height", default=0)
        self.bottom_bar_height_input.setValue(bottom_bar_height)

        # Load limit type preference (default to steps)
        limit_type = self._config_store.get_setting("limit_type", default="steps")
        if limit_type == "duration":
            self.duration_radio.setChecked(True)
        else:
            self.steps_radio.setChecked(True)

        # Purge the removed global test username/password
        self._config_store.delete_setting("test_username")
        self._config_store.delete_secret("test_password")

        # Load form fill data
        test_address = self._config_store.get_setting(
            "test_address", default="Kaiserstraße 12, 60311 Frankfurt am Main, Germany"
        )
        self.test_address_input.setText(test_address)

        test_email = self._config_store.get_setting("test_email", default="testuser@example.com")
        self.test_email_input.setText(test_email)

        test_phone = self._config_store.get_setting("test_phone", default="")
        self.test_phone_input.setText(test_phone)

        # Load verification inbox
        self.verification_inbox_address_input.setText(
            self._config_store.get_setting("verification_inbox_address", default="") or ""
        )
        self.verification_inbox_password_input.setText(
            self._config_store.get_secret_plaintext("verification_inbox_password") or ""
        )

        # Load traffic capture settings
        enable_traffic_capture = self._config_store.get_setting("enable_traffic_capture", default=False)
        self.enable_traffic_capture_checkbox.setChecked(enable_traffic_capture)
        self._on_traffic_capture_toggled(enable_traffic_capture)

        pcapdroid_api_key = self._config_store.get_secret_plaintext("pcapdroid_api_key")
        if pcapdroid_api_key:
            self.pcapdroid_api_key_input.setText(pcapdroid_api_key)

        # Load video recording settings
        enable_video_recording = self._config_store.get_setting("enable_video_recording", default=False)
        self.enable_video_recording_checkbox.setChecked(enable_video_recording)

        # Load MobSF settings
        enable_mobsf_analysis = self._config_store.get_setting("enable_mobsf_analysis", default=False)
        self.enable_mobsf_analysis_checkbox.setChecked(enable_mobsf_analysis)
        self._on_mobsf_toggled(enable_mobsf_analysis)

        auto_run_mobsf = self._config_store.get_setting("auto_run_mobsf_after_crawl", default=False)
        self.auto_run_mobsf_after_crawl_checkbox.setChecked(auto_run_mobsf)

        mobsf_api_url = self._config_store.get_setting("mobsf_api_url", default="http://localhost:8001")
        self.mobsf_api_url_input.setText(mobsf_api_url)

        # Load Crawler Agent settings
        crawler_reasoning = self._config_store.get_setting("crawler_reasoning_mode", default=True)
        self.crawler_reasoning_checkbox.setChecked(crawler_reasoning)

        crawler_streaming = self._config_store.get_setting("crawler_streaming", default=False)
        self.crawler_streaming_checkbox.setChecked(crawler_streaming)

        crawler_retry_count = self._config_store.get_setting("crawler_retry_count", default=2)
        self.crawler_retry_count_input.setValue(crawler_retry_count)

        # Load UI parser mode and Replicate API key
        ui_parser_mode = self._config_store.get_setting("ui_parser_mode", default="omniparser")
        self.ui_parser_mode_combo.setCurrentText(ui_parser_mode)

        omniparser_backend = self._config_store.get_setting("omniparser_backend", default="replicate")
        self.omniparser_backend_combo.setCurrentText(omniparser_backend)

        omniparser_local_url = self._config_store.get_setting("omniparser_local_url", default="http://localhost:8001")
        # Port 8000 is MobSF's; the old OmniParser default collided with it.
        if omniparser_local_url.rstrip("/") in ("http://localhost:8000", "http://127.0.0.1:8000"):
            omniparser_local_url = "http://localhost:8001"
        self.omniparser_local_url_input.setText(omniparser_local_url)

        omniparser_local_parse_timeout = self._config_store.get_setting(
            "omniparser_local_parse_timeout_seconds", default=120
        )
        self.omniparser_local_parse_timeout_input.setValue(int(omniparser_local_parse_timeout))

        # Trigger visibility update on load
        self.local_url_container.setVisible(omniparser_backend == "local")
        self.local_timeout_container.setVisible(omniparser_backend == "local")
        self.replicate_container.setVisible(omniparser_backend == "replicate")

        replicate_key = self._config_store.get_setting("replicate_api_key", default="")
        if replicate_key:
            self.replicate_api_key_input.setText(replicate_key)

        keepalive_enabled = self._config_store.get_setting("omniparser_keepalive_enabled", default=True)
        self.omniparser_keepalive_checkbox.setChecked(bool(keepalive_enabled))

        keepalive_interval = self._config_store.get_setting("omniparser_keepalive_interval_minutes", default=3)
        self.omniparser_keepalive_interval_input.setValue(int(keepalive_interval))

        self.replicate_keepalive_container.setVisible(omniparser_backend == "replicate")
        self.omniparser_keepalive_status_label.setVisible(omniparser_backend == "replicate")
        self._apply_keepalive_state()

        # Load exploration objective (pre-fill with default if not customized)
        exploration_objective = self._config_store.get_setting("exploration_objective", default="")
        if exploration_objective:
            self.exploration_objective_input.setPlainText(exploration_objective)
        else:
            self.exploration_objective_input.setPlainText(DEFAULT_EXPLORATION_OBJECTIVE)

        # Load Tracing / Observability settings
        enable_tracing = self._config_store.get_setting("enable_tracing", default=False)
        self.enable_tracing_checkbox.setChecked(enable_tracing)

        tracing_provider = self._config_store.get_setting("tracing_provider", default="phoenix")
        self.tracing_provider_combo.setCurrentText(tracing_provider)

        phoenix_url = self._config_store.get_setting("phoenix_url", default="http://localhost:6006")
        self.phoenix_url_input.setText(phoenix_url)

        langfuse_host = self._config_store.get_setting("langfuse_host", default="https://cloud.langfuse.com")
        self.langfuse_host_input.setText(langfuse_host)

        langfuse_pub = self._config_store.get_secret_plaintext("langfuse_public_key")
        if langfuse_pub:
            self.langfuse_pub_key_input.setText(langfuse_pub)

        langfuse_sec = self._config_store.get_secret_plaintext("langfuse_secret_key")
        if langfuse_sec:
            self.langfuse_secret_key_input.setText(langfuse_sec)

        # Update visibility and enable states
        self._on_tracing_toggled(enable_tracing)

    def _on_save_clicked(self):
        """Handle save button click."""
        try:
            # Validate API keys before saving
            gemini_key = self.gemini_api_key_input.text().strip()
            if gemini_key and not self._validate_api_key(gemini_key, "Gemini"):
                return

            openrouter_key = self.openrouter_api_key_input.text().strip()
            if openrouter_key and not self._validate_api_key(openrouter_key, "OpenRouter"):
                return

            # Validate MobSF API URL if MobSF is enabled
            if self.enable_mobsf_analysis_checkbox.isChecked():
                mobsf_url = self.mobsf_api_url_input.text().strip()
                if mobsf_url and not self._validate_mobsf_url(mobsf_url):
                    return

            with self._config_store.batch():
                # Save API keys (encrypted)
                if gemini_key:
                    self._config_store.set_secret_plaintext("gemini_api_key", gemini_key)
                else:
                    self._config_store.delete_secret("gemini_api_key")

                if openrouter_key:
                    self._config_store.set_secret_plaintext("openrouter_api_key", openrouter_key)
                else:
                    self._config_store.delete_secret("openrouter_api_key")

                # Save crawl limits
                self._config_store.set_setting("max_steps", self.max_steps_input.value(), "int")
                self._config_store.set_setting("max_duration_seconds", self.max_duration_input.value(), "int")

                # Save limit type preference
                limit_type = "steps" if self.steps_radio.isChecked() else "duration"
                self._config_store.set_setting("limit_type", limit_type, "string")

                # Save screen configuration
                self._config_store.set_setting("top_bar_height", self.top_bar_height_input.value(), "int")
                self._config_store.set_setting("bottom_bar_height", self.bottom_bar_height_input.value(), "int")

                # Save form fill data
                test_address = self.test_address_input.text().strip()
                if test_address:
                    self._config_store.set_setting("test_address", test_address, "string")
                else:
                    self._config_store.delete_setting("test_address")

                test_email = self.test_email_input.text().strip()
                if test_email:
                    self._config_store.set_setting("test_email", test_email, "string")
                else:
                    self._config_store.delete_setting("test_email")

                test_phone = self.test_phone_input.text().strip()
                if test_phone:
                    self._config_store.set_setting("test_phone", test_phone, "string")
                else:
                    self._config_store.delete_setting("test_phone")

                inbox_address = self.verification_inbox_address_input.text().strip()
                inbox_password = self.verification_inbox_password_input.text().strip()
                if inbox_address:
                    self._config_store.set_setting("verification_inbox_address", inbox_address, "string")
                else:
                    self._config_store.delete_setting("verification_inbox_address")
                if inbox_address and inbox_password:
                    self._config_store.set_secret_plaintext("verification_inbox_password", inbox_password)
                else:
                    self._config_store.delete_secret("verification_inbox_password")

                # Cleanup old config keys
                self._config_store.delete_setting("test_gmail_account")

                # Save traffic capture settings
                enable_traffic_capture = self.enable_traffic_capture_checkbox.isChecked()
                self._config_store.set_setting("enable_traffic_capture", enable_traffic_capture, "bool")

                pcapdroid_api_key = self.pcapdroid_api_key_input.text().strip()
                if pcapdroid_api_key:
                    self._config_store.set_secret_plaintext("pcapdroid_api_key", pcapdroid_api_key)
                else:
                    self._config_store.delete_secret("pcapdroid_api_key")

                # Save video recording settings
                enable_video_recording = self.enable_video_recording_checkbox.isChecked()
                self._config_store.set_setting("enable_video_recording", enable_video_recording, "bool")

                # Save MobSF settings
                enable_mobsf_analysis = self.enable_mobsf_analysis_checkbox.isChecked()
                self._config_store.set_setting("enable_mobsf_analysis", enable_mobsf_analysis, "bool")

                auto_run_mobsf = self.auto_run_mobsf_after_crawl_checkbox.isChecked()
                self._config_store.set_setting("auto_run_mobsf_after_crawl", auto_run_mobsf, "bool")

                mobsf_api_url = self.mobsf_api_url_input.text().strip()
                if mobsf_api_url:
                    self._config_store.set_setting("mobsf_api_url", mobsf_api_url, "string")
                else:
                    self._config_store.set_setting("mobsf_api_url", "http://localhost:8001", "string")

                # Save Crawler Agent settings
                crawler_reasoning = self.crawler_reasoning_checkbox.isChecked()
                self._config_store.set_setting("crawler_reasoning_mode", crawler_reasoning, "bool")

                crawler_streaming = self.crawler_streaming_checkbox.isChecked()
                self._config_store.set_setting("crawler_streaming", crawler_streaming, "bool")

                crawler_retry_count = self.crawler_retry_count_input.value()
                self._config_store.set_setting("crawler_retry_count", crawler_retry_count, "int")

                # Save UI parser mode
                ui_parser_mode = self.ui_parser_mode_combo.currentText()
                self._config_store.set_setting("ui_parser_mode", ui_parser_mode, "string")

                # Save OmniParser backend and local URL settings
                omniparser_backend = self.omniparser_backend_combo.currentText()
                self._config_store.set_setting("omniparser_backend", omniparser_backend, "string")

                omniparser_local_url = self.omniparser_local_url_input.text().strip()
                self._config_store.set_setting("omniparser_local_url", omniparser_local_url, "string")

                omniparser_local_parse_timeout = self.omniparser_local_parse_timeout_input.value()
                self._config_store.set_setting(
                    "omniparser_local_parse_timeout_seconds",
                    omniparser_local_parse_timeout,
                    "int",
                )

                # Save Replicate API key (as regular setting, not secret - for easier debugging)
                replicate_key = self.replicate_api_key_input.text().strip()
                if replicate_key:
                    self._config_store.set_setting("replicate_api_key", replicate_key, "string")
                else:
                    self._config_store.delete_setting("replicate_api_key")

                # Save OmniParser keep-alive settings
                keepalive_enabled = self.omniparser_keepalive_checkbox.isChecked()
                self._config_store.set_setting("omniparser_keepalive_enabled", keepalive_enabled, "bool")

                keepalive_interval = self.omniparser_keepalive_interval_input.value()
                self._config_store.set_setting("omniparser_keepalive_interval_minutes", keepalive_interval, "int")

                # Save exploration objective
                exploration_objective = self.exploration_objective_input.toPlainText().strip()
                if exploration_objective:
                    self._config_store.set_setting("exploration_objective", exploration_objective, "string")
                else:
                    self._config_store.delete_setting("exploration_objective")

                # Save Tracing / Observability settings
                enable_tracing = self.enable_tracing_checkbox.isChecked()
                self._config_store.set_setting("enable_tracing", enable_tracing, "bool")

                tracing_provider = self.tracing_provider_combo.currentText()
                self._config_store.set_setting("tracing_provider", tracing_provider, "string")

                phoenix_url = self.phoenix_url_input.text().strip()
                self._config_store.set_setting("phoenix_url", phoenix_url, "string")

                langfuse_host = self.langfuse_host_input.text().strip()
                self._config_store.set_setting("langfuse_host", langfuse_host, "string")

                langfuse_pub = self.langfuse_pub_key_input.text().strip()
                if langfuse_pub:
                    self._config_store.set_secret_plaintext("langfuse_public_key", langfuse_pub)
                else:
                    self._config_store.delete_secret("langfuse_public_key")

                langfuse_sec = self.langfuse_secret_key_input.text().strip()
                if langfuse_sec:
                    self._config_store.set_secret_plaintext("langfuse_secret_key", langfuse_sec)
                else:
                    self._config_store.delete_secret("langfuse_secret_key")

            # Emit signal
            self.settings_saved.emit()

            # Show success message
            QMessageBox.information(self, "Settings Saved", "All settings have been saved successfully.")

        except Exception as e:
            # Show error message
            QMessageBox.critical(self, "Error Saving Settings", f"Failed to save settings: {e}")

    def _apply_keepalive_state(self) -> None:
        """Start/stop the automatic OmniParser keep-alive timer based on current state."""
        should_run = (
            self.omniparser_keepalive_checkbox.isChecked()
            and self.omniparser_backend_combo.currentText() == "replicate"
            and not self._crawl_running
        )
        if should_run:
            was_active = self._keepalive_timer.isActive()
            interval_ms = self.omniparser_keepalive_interval_input.value() * 60_000
            self._keepalive_timer.start(interval_ms)
            if not was_active:
                # Ping immediately on enable instead of waiting a full interval,
                # so the status label reflects reality right away.
                self._on_keepalive_tick()
        else:
            self._keepalive_timer.stop()

    def _on_keepalive_tick(self) -> None:
        """Send one background keep-alive ping to Replicate OmniParser, if due."""
        if self._keepalive_in_flight or self._crawl_running:
            return
        if self.omniparser_backend_combo.currentText() != "replicate":
            return

        api_key = (
            self.get_replicate_api_key()
            or os.environ.get("REPLICATE_API_KEY")
            or os.environ.get("REPLICATE_API_TOKEN")
            or ""
        )
        if not api_key:
            self.omniparser_keepalive_status_label.setText("Keep-alive: skipped (no Replicate API key)")
            return

        self._keepalive_in_flight = True
        box_threshold = float(self._config_store.get_setting("omniparser_box_threshold", default=0.05))
        self._keepalive_thread = threading.Thread(
            target=self._run_keepalive_ping,
            args=(api_key, box_threshold),
            daemon=True,
        )
        self._keepalive_thread.start()

    def _run_keepalive_ping(self, api_key: str, box_threshold: float) -> None:
        started_at = time.perf_counter()
        try:
            from mobile_crawler.domain.omniparser_warmup import warm_up_remote_omniparser

            warm_up_remote_omniparser(api_key=api_key, box_threshold=box_threshold)
            elapsed = time.perf_counter() - started_at
            self.omniparser_keepalive_pinged.emit(True, f"Keep-alive: ok ({elapsed:.1f}s)", elapsed)
        except Exception as exc:
            elapsed = time.perf_counter() - started_at
            self.omniparser_keepalive_pinged.emit(False, f"Keep-alive: failed ({exc})", elapsed)
        finally:
            self._keepalive_in_flight = False

    def notify_device_changed(self, device_id: str | None) -> None:
        """Tell the panel which device is selected, so it can preview it.

        Called by main_window whenever device selection changes. Auto-fetches
        a calibration screenshot the first time a device becomes available,
        or when the device changes; safe to call repeatedly.
        """
        self._device_id = device_id
        if device_id is None:
            self._status_bar_preview_device_id = None
            self.screenshot_preview.set_placeholder("Connect a device to preview")
            return
        if device_id != self._status_bar_preview_device_id:
            self._fetch_status_bar_preview()

    def _fetch_status_bar_preview(self) -> None:
        """Capture a fresh screenshot from the selected device for the preview."""
        if self._device_id is None:
            self.screenshot_preview.set_placeholder("Connect a device to preview")
            return
        if self._status_bar_preview_in_flight:
            return
        self._status_bar_preview_in_flight = True
        self._status_bar_preview_thread = threading.Thread(
            target=self._run_status_bar_preview_capture,
            args=(self._device_id,),
            daemon=True,
        )
        self._status_bar_preview_thread.start()

    def _run_status_bar_preview_capture(self, device_id: str) -> None:
        import tempfile

        from mobile_crawler.domain.adb_action_executor import ADBActionExecutor

        tmp_path: str | None = None
        try:
            executor = ADBActionExecutor(device_id)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            result = executor.take_screenshot(tmp_path)
            if not result.success:
                self._status_bar_preview_failed.emit(result.error_message or "Screenshot failed")
                return
            with open(tmp_path, "rb") as f:
                image_bytes = f.read()
            self._status_bar_preview_captured.emit(image_bytes)
        except Exception as exc:
            self._status_bar_preview_failed.emit(str(exc))
        finally:
            if tmp_path is not None:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            self._status_bar_preview_in_flight = False

    def _on_status_bar_preview_captured(self, image_bytes: bytes) -> None:
        self._status_bar_preview_device_id = self._device_id
        self.screenshot_preview.set_screenshot(image_bytes)
        self.screenshot_preview.set_top_exclusion_px(self.top_bar_height_input.value())
        self.screenshot_preview.set_bottom_exclusion_px(self.bottom_bar_height_input.value())

    def _on_status_bar_preview_failed(self, message: str) -> None:
        logger.warning(f"Status bar preview screenshot failed: {message}")
        self.screenshot_preview.set_placeholder("Couldn't capture screenshot")

    def _on_keepalive_pinged(self, _success: bool, message: str, _elapsed_seconds: float) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.omniparser_keepalive_status_label.setText(f"{message} at {timestamp}")

    def set_crawl_running(self, running: bool) -> None:
        """Pause/resume the OmniParser keep-alive timer around an active crawl."""
        self._crawl_running = running
        self._apply_keepalive_state()

    def stop_keepalive(self) -> None:
        """Stop the OmniParser keep-alive timer, e.g. on application shutdown."""
        self._keepalive_timer.stop()

    def get_gemini_api_key(self) -> str:
        """Get the current Gemini API key value.

        Returns:
            Current Gemini API key
        """
        return self.gemini_api_key_input.text()

    def get_openrouter_api_key(self) -> str:
        """Get the current OpenRouter API key value.

        Returns:
            Current OpenRouter API key
        """
        return self.openrouter_api_key_input.text()

    def get_max_steps(self) -> int:
        """Get the current max steps value.

        Returns:
            Current max steps
        """
        return self.max_steps_input.value()

    def get_max_duration(self) -> int:
        """Get the current max duration value.

        Returns:
            Current max duration in seconds
        """
        return self.max_duration_input.value()

    def get_limit_mode(self) -> str:
        """Get the current limit mode (steps or duration).

        Returns:
            'steps' or 'duration'
        """
        return "steps" if self.steps_radio.isChecked() else "duration"

    def get_top_bar_height(self) -> int:
        """Get the current top bar height value.

        Returns:
            Current top bar height in pixels
        """
        return self.top_bar_height_input.value()

    def get_bottom_bar_height(self) -> int:
        """Get the current bottom bar height value.

        Returns:
            Current bottom bar height in pixels
        """
        return self.bottom_bar_height_input.value()

    def get_test_address(self) -> str:
        """Get the current test address value."""
        return self.test_address_input.text().strip()

    def get_test_email(self) -> str:
        """Get the current test email value."""
        return self.test_email_input.text().strip()

    def get_test_phone(self) -> str:
        """Get the current test phone value."""
        return self.test_phone_input.text().strip()

    def get_enable_traffic_capture(self) -> bool:
        """Get the current traffic capture enabled state.

        Returns:
            True if traffic capture is enabled
        """
        return self.enable_traffic_capture_checkbox.isChecked()

    def get_enable_video_recording(self) -> bool:
        """Get the current video recording enabled state.

        Returns:
            True if video recording is enabled
        """
        return self.enable_video_recording_checkbox.isChecked()

    def get_enable_mobsf_analysis(self) -> bool:
        """Get the current MobSF analysis enabled state.

        Returns:
            True if MobSF analysis is enabled
        """
        return self.enable_mobsf_analysis_checkbox.isChecked()

    def get_auto_run_mobsf_after_crawl(self) -> bool:
        """Get the current auto-run MobSF after crawl state.

        Returns:
            True if MobSF analysis should run automatically after a successful crawl
        """
        return self.auto_run_mobsf_after_crawl_checkbox.isChecked()

    def get_exploration_objective(self) -> str:
        """Get the current exploration objective / prompt for crawler agent.

        Returns:
            Current exploration objective text (empty string if not set)
        """
        return self.exploration_objective_input.toPlainText().strip()

    def _reset_exploration_objective(self):
        """Reset the exploration objective text edit to the default value."""
        self.exploration_objective_input.setPlainText(DEFAULT_EXPLORATION_OBJECTIVE)

    def _add_guided_scenario(self) -> None:
        """Add a new editable, empty Guided Scenario item and start editing it."""
        item = QListWidgetItem("New scenario")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.guided_scenarios_list.addItem(item)
        self.guided_scenarios_list.setCurrentItem(item)
        self.guided_scenarios_list.editItem(item)

    def _remove_selected_guided_scenario(self) -> None:
        """Remove the currently selected Guided Scenario item(s)."""
        for item in self.guided_scenarios_list.selectedItems():
            self.guided_scenarios_list.takeItem(self.guided_scenarios_list.row(item))

    def _move_guided_scenario(self, direction: int) -> None:
        """Move the currently selected Guided Scenario item up (-1) or down (+1)."""
        row = self.guided_scenarios_list.currentRow()
        if row < 0:
            return
        new_row = row + direction
        if not (0 <= new_row < self.guided_scenarios_list.count()):
            return
        item = self.guided_scenarios_list.takeItem(row)
        self.guided_scenarios_list.insertItem(new_row, item)
        self.guided_scenarios_list.setCurrentRow(new_row)

    def get_guided_scenarios(self) -> list[str]:
        """Get the current Guided Scenarios list, in order.

        Returns:
            Ordered list of non-empty scenario strings
        """
        return [
            self.guided_scenarios_list.item(i).text().strip()
            for i in range(self.guided_scenarios_list.count())
            if self.guided_scenarios_list.item(i).text().strip()
        ]

    def set_guided_scenarios(self, scenarios: list[str]) -> None:
        """Replace the Guided Scenarios list wholesale."""
        self.guided_scenarios_list.clear()
        for scenario in scenarios:
            item = QListWidgetItem(scenario)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.guided_scenarios_list.addItem(item)

    def get_app_account(self) -> AppAccount | None:
        """Get the App Account entered for the selected app, or None if the username is empty."""
        username = self.app_account_username_input.text().strip()
        if not username:
            return None
        return AppAccount(
            username=username,
            password=self.app_account_password_input.text(),
            address_override=self.app_account_address_input.text().strip(),
        )

    def set_app_account(self, account: AppAccount | None) -> None:
        """Show `account` in the App Account fields (None clears them)."""
        self.app_account_username_input.setText(account.username if account else "")
        self.app_account_password_input.setText(account.password if account else "")
        self.app_account_address_input.setText(account.address_override if account else "")

    def get_guided_scenarios_url_override(self) -> str:
        """Get the user-entered website URL override for Guided Scenario generation."""
        return self.guided_scenarios_url_input.text().strip()

    def set_guided_scenarios_url_override(self, url: str) -> None:
        """Set the website URL override field."""
        self.guided_scenarios_url_input.setText(url or "")

    def set_guided_scenarios_warning(self, message: str | None) -> None:
        """Show or clear the Guided Scenarios warning banner (e.g. generation failures)."""
        if message:
            self.guided_scenarios_warning_label.setText(message)
            self.guided_scenarios_warning_label.setVisible(True)
        else:
            self.guided_scenarios_warning_label.setText("")
            self.guided_scenarios_warning_label.setVisible(False)

    def set_generate_guided_scenarios_busy(self, busy: bool) -> None:
        """Disable/relabel the Generate button while a generation request is in flight."""
        self.generate_guided_scenarios_button.setEnabled(not busy)
        self.generate_guided_scenarios_button.setText("Generating..." if busy else "Generate from App Info")

    def get_ui_parser_mode(self) -> str:
        """Get the current UI parser mode.

        Returns:
            UI parser mode: "boost", "omniparser", or "accessibility"
        """
        return self.ui_parser_mode_combo.currentText()

    def get_replicate_api_key(self) -> str:
        """Get the current Replicate API key.

        Returns:
            Replicate API key
        """
        return self.replicate_api_key_input.text().strip()

    def get_omniparser_backend(self) -> str:
        """Get the current OmniParser backend.

        Returns:
            Backend mode: "replicate" or "local"
        """
        return self.omniparser_backend_combo.currentText()

    def get_omniparser_local_url(self) -> str:
        """Get the current OmniParser Local URL.

        Returns:
            Local server URL
        """
        return self.omniparser_local_url_input.text().strip()

    def get_omniparser_local_parse_timeout_seconds(self) -> int:
        """Get the current local OmniParser parse timeout."""
        return self.omniparser_local_parse_timeout_input.value()

    def get_pcapdroid_api_key(self) -> str:
        """Get the current PCAPdroid API key.

        Returns:
            PCAPdroid API key
        """
        return self.pcapdroid_api_key_input.text().strip()

    def get_mobsf_api_url(self) -> str:
        """Get the current MobSF API URL.

        Returns:
            MobSF API URL
        """
        return self.mobsf_api_url_input.text().strip()

    def get_enable_tracing(self) -> bool:
        """Get the current tracing enabled state."""
        return self.enable_tracing_checkbox.isChecked()

    def get_tracing_provider(self) -> str:
        """Get the current tracing provider."""
        return self.tracing_provider_combo.currentText()

    def get_phoenix_url(self) -> str:
        """Get the current Arize Phoenix URL."""
        return self.phoenix_url_input.text().strip()

    def get_langfuse_host(self) -> str:
        """Get the current Langfuse host URL."""
        return self.langfuse_host_input.text().strip()

    def get_langfuse_public_key(self) -> str:
        """Get the current Langfuse public key."""
        return self.langfuse_pub_key_input.text().strip()

    def get_langfuse_secret_key(self) -> str:
        """Get the current Langfuse secret key."""
        return self.langfuse_secret_key_input.text().strip()

    def reset(self):
        """Reset all settings to default values."""
        self.gemini_api_key_input.clear()
        self.openrouter_api_key_input.clear()
        self.replicate_api_key_input.clear()
        self.max_steps_input.setValue(100)
        self.max_duration_input.setValue(300)
        self.test_address_input.setText("Kaiserstraße 12, 60311 Frankfurt am Main, Germany")
        self.test_email_input.setText("testuser@example.com")
        self.test_phone_input.clear()
        self.verification_inbox_address_input.clear()
        self.verification_inbox_password_input.clear()
        self.exploration_objective_input.setPlainText(DEFAULT_EXPLORATION_OBJECTIVE)
        self.ui_parser_mode_combo.setCurrentText("boost")
        self.omniparser_local_parse_timeout_input.setValue(120)
        self.enable_tracing_checkbox.setChecked(False)
        self.tracing_provider_combo.setCurrentText("phoenix")
        self.phoenix_url_input.setText("http://localhost:6006")
        self.langfuse_host_input.setText("https://cloud.langfuse.com")
        self.langfuse_pub_key_input.clear()
        self.langfuse_secret_key_input.clear()

    def _validate_api_key(self, api_key: str, provider_name: str) -> bool:
        """Validate API key format and optionally test connectivity.

        Args:
            api_key: The API key to validate
            provider_name: Name of the provider for error messages

        Returns:
            True if valid, False otherwise
        """
        # Basic format validation
        if len(api_key) < 20:
            QMessageBox.warning(
                self,
                f"Invalid {provider_name} API Key",
                f"The {provider_name} API key appears to be too short.\n\n"
                f"Please check that you have entered a valid API key.",
            )
            return False

        if not api_key.startswith(("sk-", "AIza", "pk-")) and provider_name != "OpenRouter":
            # Allow more flexible validation for OpenRouter
            if len(api_key) < 30:
                QMessageBox.warning(
                    self,
                    f"Invalid {provider_name} API Key",
                    f"The {provider_name} API key format appears invalid.\n\n"
                    f"Please check that you have entered a valid API key.",
                )
                return False

        # For more thorough validation, we could make a test API call here
        # But for now, basic format validation is sufficient

        return True

    def _validate_mobsf_url(self, url: str) -> bool:
        """Validate MobSF API URL format.

        Args:
            url: The URL to validate

        Returns:
            True if valid, False otherwise
        """
        if not url:
            QMessageBox.warning(
                self, "Invalid MobSF API URL", "MobSF API URL cannot be empty when MobSF analysis is enabled."
            )
            return False

        # Basic URL format validation
        if not url.startswith(("http://", "https://")):
            QMessageBox.warning(
                self,
                "Invalid MobSF API URL",
                "MobSF API URL must start with http:// or https://\n\nExample: http://localhost:8001",
            )
            return False

        # Check for basic URL structure
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            if not parsed.netloc:
                QMessageBox.warning(
                    self,
                    "Invalid MobSF API URL",
                    "MobSF API URL appears to be malformed.\n\nExample: http://localhost:8001",
                )
                return False
        except Exception:
            QMessageBox.warning(
                self,
                "Invalid MobSF API URL",
                "MobSF API URL appears to be malformed.\n\nExample: http://localhost:8001",
            )
            return False

        return True
