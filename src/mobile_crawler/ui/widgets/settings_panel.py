"""Settings panel widget for mobile-crawler GUI."""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QGroupBox,
    QPushButton,
    QMessageBox,
    QRadioButton,
    QButtonGroup,
    QCheckBox,
    QTabWidget,
    QScrollArea,
    QComboBox,
)
from PySide6.QtCore import Qt, Signal

if TYPE_CHECKING:
    from mobile_crawler.infrastructure.user_config_store import UserConfigStore


class SettingsPanel(QWidget):
    """Widget for configuring crawler settings.

    Provides inputs for API keys, system prompt, crawl limits,
    and test credentials. Saves to user_config.db.
    """

    # Signal emitted when settings are saved
    settings_saved = Signal()  # type: ignore

    def __init__(self, config_store: "UserConfigStore", parent=None):
        """Initialize settings panel widget.

        Args:
            config_store: UserConfigStore instance for saving/loading settings
            parent: Parent widget
        """
        super().__init__(parent)
        self._config_store = config_store
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Set up user interface."""
        main_layout = QVBoxLayout(self)

        # Main Tab Widget
        self.tab_widget = QTabWidget()

        # 1. General Tab (Limits, Screen Config)
        self.tab_widget.addTab(self._setup_general_tab(), "General")

        # 2. AI & Agent Tab (Provider keys, DroidRun, parser, prompts, test credentials)
        self.tab_widget.addTab(self._setup_ai_tab(), "AI & Agent")

        # 3. Integrations Tab (Traffic, Video, MobSF)
        self.tab_widget.addTab(self._setup_integrations_tab(), "Integrations")

        main_layout.addWidget(self.tab_widget, 1)

        # Save button in bottom area (stays visible regardless of tab)
        save_layout = QHBoxLayout()
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
        self.max_steps_input.setSingleStep(10)
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
        self.max_duration_input.setSingleStep(30)
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
        self.top_bar_height_input.setValue(0)
        self.top_bar_height_input.setToolTip(
            "Exclude the Android status bar from OCR and AI analysis. Typically 80-120px."
        )
        top_bar_layout.addWidget(self.top_bar_height_input)
        top_bar_layout.addStretch()
        screen_layout.addLayout(top_bar_layout)

        screen_group.setLayout(screen_layout)
        layout.addWidget(screen_group)

        layout.addStretch()
        return self._wrap_in_scroll_area(tab)

    def _setup_ai_tab(self) -> QWidget:
        """Create the AI and agent settings tab."""
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

        # Test Credentials group
        credentials_group = QGroupBox("App Test Credentials")
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

        l, self.test_username_input = create_credential_field("Test Username:", "Enter test username")
        credentials_layout.addLayout(l)

        l, self.test_password_input = create_credential_field("Test Password:", "Enter test password", True)
        credentials_layout.addLayout(l)

        credentials_group.setLayout(credentials_layout)
        layout.addWidget(credentials_group)

        # DroidRun Agent group
        droidrun_group = QGroupBox("DroidRun Agent")
        droidrun_layout = QVBoxLayout()
        droidrun_layout.setSpacing(12)
        droidrun_layout.setContentsMargins(15, 20, 15, 20)

        self.enable_droidrun_checkbox = QCheckBox("Enable DroidRun AI Agent")
        self.enable_droidrun_checkbox.setToolTip(
            "Use DroidRun's advanced multi-step planning agent instead of single-shot AI responses"
        )
        droidrun_layout.addWidget(self.enable_droidrun_checkbox)

        self.droidrun_reasoning_checkbox = QCheckBox("Use Reasoning Mode")
        self.droidrun_reasoning_checkbox.setToolTip(
            "Enable complex planning with ManagerAgent -> ExecutorAgent cycles (vs direct execution)"
        )
        self.droidrun_reasoning_checkbox.setChecked(True)
        droidrun_layout.addWidget(self.droidrun_reasoning_checkbox)

        max_cycles_layout = QHBoxLayout()
        max_cycles_layout.addWidget(QLabel("Max Planning Cycles:"))
        self.droidrun_max_cycles_input = QSpinBox()
        self.droidrun_max_cycles_input.setRange(1, 20)
        self.droidrun_max_cycles_input.setValue(5)
        self.droidrun_max_cycles_input.setToolTip("Maximum planning/execution cycles for DroidRun agent")
        max_cycles_layout.addWidget(self.droidrun_max_cycles_input)
        max_cycles_layout.addStretch()
        droidrun_layout.addLayout(max_cycles_layout)

        self.droidrun_streaming_checkbox = QCheckBox("Enable Streaming Output")
        self.droidrun_streaming_checkbox.setToolTip("Show real-time agent planning and execution updates")
        droidrun_layout.addWidget(self.droidrun_streaming_checkbox)

        retry_layout = QHBoxLayout()
        retry_layout.addWidget(QLabel("Agent Retry Count:"))
        self.droidrun_retry_count_input = QSpinBox()
        self.droidrun_retry_count_input.setRange(0, 10)
        self.droidrun_retry_count_input.setValue(2)
        self.droidrun_retry_count_input.setToolTip("Number of retries for failed agent operations")
        retry_layout.addWidget(self.droidrun_retry_count_input)
        retry_layout.addStretch()
        droidrun_layout.addLayout(retry_layout)

        droidrun_group.setLayout(droidrun_layout)
        layout.addWidget(droidrun_group)

        # UI Parser group
        parser_group = QGroupBox("UI Parser")
        parser_layout = QVBoxLayout()
        parser_layout.setSpacing(12)
        parser_layout.setContentsMargins(15, 20, 15, 20)

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
            "DroidRun mainly uses Android Accessibility APIs. In 'boost' mode it uses the a11y tree first, "
            "and falls back to OmniParser only when accessibility metadata is missing or weak."
        )
        parser_approach_hint.setWordWrap(True)
        parser_approach_hint.setStyleSheet("color: #666; font-size: 11px;")
        parser_layout.addWidget(parser_approach_hint)

        replicate_layout = QHBoxLayout()
        replicate_layout.addWidget(QLabel("Replicate API Key:"))
        self.replicate_api_key_input = QLineEdit()
        self.replicate_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.replicate_api_key_input.setPlaceholderText("Enter Replicate API key for OmniParser")
        self.replicate_api_key_input.setToolTip("API key for Replicate (used by OmniParser vision model)")
        replicate_layout.addWidget(self.replicate_api_key_input)
        parser_layout.addLayout(replicate_layout)

        parser_group.setLayout(parser_layout)
        layout.addWidget(parser_group)

        # Exploration Objective group
        objective_group = QGroupBox("Exploration Objective")
        objective_layout = QVBoxLayout()
        objective_layout.setSpacing(8)
        objective_layout.setContentsMargins(15, 20, 15, 20)

        objective_hint = QLabel(
            "This prompt is sent to DroidRun as the exploration goal. Edit to customize the exploration behavior."
        )
        objective_hint.setWordWrap(True)
        objective_hint.setStyleSheet("color: #666; font-size: 11px;")
        objective_layout.addWidget(objective_hint)

        self.exploration_objective_input = QTextEdit()
        self.exploration_objective_input.setMaximumHeight(120)
        objective_layout.addWidget(self.exploration_objective_input)

        objective_group.setLayout(objective_layout)
        layout.addWidget(objective_group)

        def on_droidrun_enabled_changed(enabled):
            self.droidrun_reasoning_checkbox.setEnabled(enabled)
            self.droidrun_max_cycles_input.setEnabled(enabled)
            self.droidrun_streaming_checkbox.setEnabled(enabled)
            self.droidrun_retry_count_input.setEnabled(enabled)

        self.enable_droidrun_checkbox.toggled.connect(on_droidrun_enabled_changed)
        on_droidrun_enabled_changed(self.enable_droidrun_checkbox.isChecked())

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

        mobsf_url_layout = QHBoxLayout()
        mobsf_url_layout.addWidget(QLabel("API URL:"))
        self.mobsf_api_url_input = QLineEdit()
        self.mobsf_api_url_input.setPlaceholderText("http://localhost:8000")
        self.mobsf_api_url_input.setEnabled(False)
        mobsf_url_layout.addWidget(self.mobsf_api_url_input)
        mobsf_layout.addLayout(mobsf_url_layout)

        self.enable_mobsf_analysis_checkbox.toggled.connect(self._on_mobsf_toggled)
        mobsf_group.setLayout(mobsf_layout)
        layout.addWidget(mobsf_group)

        # Observability & Tracing
        tracing_group = QGroupBox("Observability & Tracing")
        tracing_layout = QVBoxLayout()

        self.enable_tracing_checkbox = QCheckBox("Enable Tracing (OpenTelemetry)")
        self.enable_tracing_checkbox.setToolTip("Enable telemetry tracing for agent steps, tool calls, and token usage metrics.")
        tracing_layout.addWidget(self.enable_tracing_checkbox)

        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("Provider:"))
        self.tracing_provider_combo = QComboBox()
        self.tracing_provider_combo.addItems(["phoenix", "langfuse"])
        self.tracing_provider_combo.setToolTip("Tracing provider: 'phoenix' (local dashboard) or 'langfuse' (cloud monitoring)")
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

        # Langfuse configuration widget
        self.langfuse_widget = QWidget()
        langfuse_layout = QVBoxLayout(self.langfuse_widget)
        langfuse_layout.setContentsMargins(0, 0, 0, 0)

        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel("Host URL:"))
        self.langfuse_host_input = QLineEdit()
        self.langfuse_host_input.setPlaceholderText("https://us.cloud.langfuse.com")
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

    def _on_tracing_toggled(self, checked: bool):
        """Handle tracing enabled checkbox toggle."""
        self.tracing_provider_combo.setEnabled(checked)
        if checked:
            self._on_tracing_provider_changed(self.tracing_provider_combo.currentText())
        else:
            self.phoenix_widget.setEnabled(False)
            self.langfuse_widget.setEnabled(False)

    def _on_tracing_provider_changed(self, provider: str):
        """Handle tracing provider combobox change."""
        if not self.enable_tracing_checkbox.isChecked():
            self.phoenix_widget.setEnabled(False)
            self.langfuse_widget.setEnabled(False)
            return

        if provider == "phoenix":
            self.phoenix_widget.setVisible(True)
            self.phoenix_widget.setEnabled(True)
            self.langfuse_widget.setVisible(False)
            self.langfuse_widget.setEnabled(False)
        else:
            self.phoenix_widget.setVisible(False)
            self.phoenix_widget.setEnabled(False)
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
        top_bar_height = self._config_store.get_setting("top_bar_height", default=0)
        self.top_bar_height_input.setValue(top_bar_height)

        # Load limit type preference (default to steps)
        limit_type = self._config_store.get_setting("limit_type", default="steps")
        if limit_type == "duration":
            self.duration_radio.setChecked(True)
        else:
            self.steps_radio.setChecked(True)

        # Load test credentials
        test_username = self._config_store.get_setting("test_username", default="")
        self.test_username_input.setText(test_username)

        test_password = self._config_store.get_secret_plaintext("test_password")
        if test_password:
            self.test_password_input.setText(test_password)

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

        mobsf_api_url = self._config_store.get_setting("mobsf_api_url", default="http://localhost:8000")
        self.mobsf_api_url_input.setText(mobsf_api_url)

        # Load DroidRun Agent settings
        enable_droidrun = self._config_store.get_setting("use_droidrun_agent", default=True)
        self.enable_droidrun_checkbox.setChecked(enable_droidrun)

        droidrun_reasoning = self._config_store.get_setting("droidrun_reasoning_mode", default=True)
        self.droidrun_reasoning_checkbox.setChecked(droidrun_reasoning)

        droidrun_max_cycles = self._config_store.get_setting("droidrun_max_cycles", default=5)
        self.droidrun_max_cycles_input.setValue(droidrun_max_cycles)

        droidrun_streaming = self._config_store.get_setting("droidrun_streaming", default=False)
        self.droidrun_streaming_checkbox.setChecked(droidrun_streaming)

        droidrun_retry_count = self._config_store.get_setting("droidrun_retry_count", default=2)
        self.droidrun_retry_count_input.setValue(droidrun_retry_count)

        # Load UI parser mode and Replicate API key
        ui_parser_mode = self._config_store.get_setting("ui_parser_mode", default="boost")
        self.ui_parser_mode_combo.setCurrentText(ui_parser_mode)

        replicate_key = self._config_store.get_setting("replicate_api_key", default="")
        if replicate_key:
            self.replicate_api_key_input.setText(replicate_key)

        # Load exploration objective (pre-fill with default if not customized)
        exploration_objective = self._config_store.get_setting("exploration_objective", default="")
        if exploration_objective:
            self.exploration_objective_input.setPlainText(exploration_objective)
        else:
            self.exploration_objective_input.setPlainText(
                "Explore the app systematically. Navigate through different screens, "
                "interact with UI elements, and discover the app's functionality. "
                "Focus on user flows like registration, login, main features, and settings."
            )

        # Load Tracing / Observability settings
        enable_tracing = self._config_store.get_setting("enable_tracing", default=False)
        self.enable_tracing_checkbox.setChecked(enable_tracing)

        tracing_provider = self._config_store.get_setting("tracing_provider", default="phoenix")
        self.tracing_provider_combo.setCurrentText(tracing_provider)

        phoenix_url = self._config_store.get_setting("phoenix_url", default="http://localhost:6006")
        self.phoenix_url_input.setText(phoenix_url)

        langfuse_host = self._config_store.get_setting("langfuse_host", default="https://us.cloud.langfuse.com")
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

            # Save test credentials
            test_username = self.test_username_input.text().strip()
            if test_username:
                self._config_store.set_setting("test_username", test_username, "string")
            else:
                self._config_store.delete_setting("test_username")

            test_password = self.test_password_input.text().strip()
            if test_password:
                self._config_store.set_secret_plaintext("test_password", test_password)
            else:
                self._config_store.delete_secret("test_password")

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

            mobsf_api_url = self.mobsf_api_url_input.text().strip()
            if mobsf_api_url:
                self._config_store.set_setting("mobsf_api_url", mobsf_api_url, "string")
            else:
                self._config_store.set_setting("mobsf_api_url", "http://localhost:8000", "string")

            # Save DroidRun Agent settings
            enable_droidrun = self.enable_droidrun_checkbox.isChecked()
            self._config_store.set_setting("use_droidrun_agent", enable_droidrun, "bool")

            droidrun_reasoning = self.droidrun_reasoning_checkbox.isChecked()
            self._config_store.set_setting("droidrun_reasoning_mode", droidrun_reasoning, "bool")

            droidrun_max_cycles = self.droidrun_max_cycles_input.value()
            self._config_store.set_setting("droidrun_max_cycles", droidrun_max_cycles, "int")

            droidrun_streaming = self.droidrun_streaming_checkbox.isChecked()
            self._config_store.set_setting("droidrun_streaming", droidrun_streaming, "bool")

            droidrun_retry_count = self.droidrun_retry_count_input.value()
            self._config_store.set_setting("droidrun_retry_count", droidrun_retry_count, "int")

            # Save UI parser mode
            ui_parser_mode = self.ui_parser_mode_combo.currentText()
            self._config_store.set_setting("ui_parser_mode", ui_parser_mode, "string")

            # Save Replicate API key (as regular setting, not secret - for easier debugging)
            replicate_key = self.replicate_api_key_input.text().strip()
            if replicate_key:
                self._config_store.set_setting("replicate_api_key", replicate_key, "string")
            else:
                self._config_store.delete_setting("replicate_api_key")

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

    def get_test_username(self) -> str:
        """Get the current test username value.

        Returns:
            Current test username
        """
        return self.test_username_input.text()

    def get_test_password(self) -> str:
        """Get the current test password value."""
        return self.test_password_input.text()

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

    def get_enable_droidrun_agent(self) -> bool:
        """Get the current DroidRun agent enabled state.

        Returns:
            True if DroidRun agent is enabled
        """
        return self.enable_droidrun_checkbox.isChecked()

    def get_exploration_objective(self) -> str:
        """Get the current exploration objective / prompt for DroidRun.

        Returns:
            Current exploration objective text (empty string if not set)
        """
        return self.exploration_objective_input.toPlainText().strip()

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
        self.test_username_input.clear()
        self.test_password_input.clear()
        self.ui_parser_mode_combo.setCurrentText("boost")
        self.enable_tracing_checkbox.setChecked(False)
        self.tracing_provider_combo.setCurrentText("phoenix")
        self.phoenix_url_input.setText("http://localhost:6006")
        self.langfuse_host_input.setText("https://us.cloud.langfuse.com")
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
                f"MobSF API URL must start with http:// or https://\n\nExample: http://localhost:8000",
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
                    f"MobSF API URL appears to be malformed.\n\nExample: http://localhost:8000",
                )
                return False
        except Exception:
            QMessageBox.warning(
                self,
                "Invalid MobSF API URL",
                f"MobSF API URL appears to be malformed.\n\nExample: http://localhost:8000",
            )
            return False

        return True
