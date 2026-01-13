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
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

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
        layout = QVBoxLayout()

        # Group box for API Keys
        api_keys_group = QGroupBox("API Keys")
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

        # Group box for System Prompt
        prompt_group = QGroupBox("System Prompt")
        prompt_layout = QVBoxLayout()

        prompt_label = QLabel("Custom System Prompt:")
        prompt_layout.addWidget(prompt_label)

        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setPlaceholderText(
            "Enter custom system prompt (leave empty to use default)"
        )
        self.system_prompt_input.setMaximumHeight(150)
        prompt_layout.addWidget(self.system_prompt_input)

        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)

        # Group box for Crawl Limits
        limits_group = QGroupBox("Crawl Limits")
        limits_layout = QVBoxLayout()

        # Radio buttons for limit type selection
        self.limit_button_group = QButtonGroup()
        
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
        self.max_duration_input.setEnabled(False)  # Initially disabled
        max_duration_layout.addWidget(self.max_duration_input)
        max_duration_layout.addStretch()
        limits_layout.addLayout(max_duration_layout)

        # Connect radio button signals
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
        self.top_bar_height_input.setToolTip("Exclude the Android status bar from OCR and AI analysis. Typically 80-120px.")
        top_bar_layout.addWidget(self.top_bar_height_input)
        top_bar_layout.addStretch()
        screen_layout.addLayout(top_bar_layout)

        screen_group.setLayout(screen_layout)
        layout.addWidget(screen_group)

        # Group box for Traffic Capture
        traffic_capture_group = QGroupBox("Traffic Capture (PCAPdroid)")
        traffic_capture_layout = QVBoxLayout()

        # Enable traffic capture checkbox
        enable_layout = QHBoxLayout()
        self.enable_traffic_capture_checkbox = QCheckBox("Enable Traffic Capture")
        enable_layout.addWidget(self.enable_traffic_capture_checkbox)
        enable_layout.addStretch()
        traffic_capture_layout.addLayout(enable_layout)

        # PCAPdroid API Key
        pcapdroid_api_key_layout = QHBoxLayout()
        pcapdroid_api_key_label = QLabel("PCAPdroid API Key:")
        pcapdroid_api_key_layout.addWidget(pcapdroid_api_key_label)
        self.pcapdroid_api_key_input = QLineEdit()
        self.pcapdroid_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pcapdroid_api_key_input.setPlaceholderText("Enter PCAPdroid API key")
        self.pcapdroid_api_key_input.setEnabled(False)
        pcapdroid_api_key_layout.addWidget(self.pcapdroid_api_key_input)
        traffic_capture_layout.addLayout(pcapdroid_api_key_layout)

        # Connect checkbox to enable/disable fields
        self.enable_traffic_capture_checkbox.toggled.connect(self._on_traffic_capture_toggled)

        traffic_capture_group.setLayout(traffic_capture_layout)
        layout.addWidget(traffic_capture_group)

        # Group box for Video Recording
        video_recording_group = QGroupBox("Video Recording")
        video_recording_layout = QVBoxLayout()

        # Enable video recording checkbox
        enable_video_layout = QHBoxLayout()
        self.enable_video_recording_checkbox = QCheckBox("Enable Video Recording")
        enable_video_layout.addWidget(self.enable_video_recording_checkbox)
        enable_video_layout.addStretch()
        video_recording_layout.addLayout(enable_video_layout)

        video_recording_group.setLayout(video_recording_layout)
        layout.addWidget(video_recording_group)

        # Group box for MobSF Analysis
        mobsf_group = QGroupBox("MobSF Static Analysis")
        mobsf_layout = QVBoxLayout()

        # Enable MobSF analysis checkbox
        enable_mobsf_layout = QHBoxLayout()
        self.enable_mobsf_analysis_checkbox = QCheckBox("Enable MobSF Analysis")
        enable_mobsf_layout.addWidget(self.enable_mobsf_analysis_checkbox)
        enable_mobsf_layout.addStretch()
        mobsf_layout.addLayout(enable_mobsf_layout)

        # MobSF API URL
        mobsf_url_layout = QHBoxLayout()
        mobsf_url_label = QLabel("MobSF API URL:")
        mobsf_url_layout.addWidget(mobsf_url_label)
        self.mobsf_api_url_input = QLineEdit()
        self.mobsf_api_url_input.setPlaceholderText("http://localhost:8000")
        self.mobsf_api_url_input.setEnabled(False)  # Enabled when checkbox is checked
        mobsf_url_layout.addWidget(self.mobsf_api_url_input)
        mobsf_layout.addLayout(mobsf_url_layout)

        # MobSF API Key
        mobsf_api_key_layout = QHBoxLayout()
        mobsf_api_key_label = QLabel("MobSF API Key:")
        mobsf_api_key_layout.addWidget(mobsf_api_key_label)
        self.mobsf_api_key_input = QLineEdit()
        self.mobsf_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.mobsf_api_key_input.setPlaceholderText("Enter MobSF API key")
        self.mobsf_api_key_input.setEnabled(False)
        mobsf_api_key_layout.addWidget(self.mobsf_api_key_input)
        mobsf_layout.addLayout(mobsf_api_key_layout)

        # Connect checkbox to enable/disable fields
        self.enable_mobsf_analysis_checkbox.toggled.connect(self._on_mobsf_toggled)

        mobsf_group.setLayout(mobsf_layout)
        layout.addWidget(mobsf_group)

        # Group box for Test Credentials
        credentials_group = QGroupBox("Test Credentials")
        credentials_layout = QVBoxLayout()

        # Test Username
        username_layout = QHBoxLayout()
        username_label = QLabel("Test Username:")
        username_layout.addWidget(username_label)
        self.test_username_input = QLineEdit()
        self.test_username_input.setPlaceholderText("Enter test username")
        username_layout.addWidget(self.test_username_input)
        credentials_layout.addLayout(username_layout)

        # Test Password
        password_layout = QHBoxLayout()
        password_label = QLabel("Test Password:")
        password_layout.addWidget(password_label)
        self.test_password_input = QLineEdit()
        self.test_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.test_password_input.setPlaceholderText("Enter test password")
        password_layout.addWidget(self.test_password_input)
        credentials_layout.addLayout(password_layout)

        credentials_group.setLayout(credentials_layout)
        layout.addWidget(credentials_group)

        # Save button
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self._on_save_clicked)
        save_layout.addWidget(self.save_button)
        layout.addLayout(save_layout)

        # Add stretch at bottom
        layout.addStretch()

        # Set the layout for this widget
        self.setLayout(layout)

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
        self.mobsf_api_key_input.setEnabled(checked)

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

        # Load system prompt
        system_prompt = self._config_store.get_setting("system_prompt", default="")
        self.system_prompt_input.setPlainText(system_prompt)

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

        mobsf_api_key = self._config_store.get_secret_plaintext("mobsf_api_key")
        if mobsf_api_key:
            self.mobsf_api_key_input.setText(mobsf_api_key)

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

            # Save system prompt
            system_prompt = self.system_prompt_input.toPlainText().strip()
            if system_prompt:
                self._config_store.set_setting("system_prompt", system_prompt, "string")
            else:
                self._config_store.delete_setting("system_prompt")

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

            mobsf_api_key = self.mobsf_api_key_input.text().strip()
            if mobsf_api_key:
                self._config_store.set_secret_plaintext("mobsf_api_key", mobsf_api_key)
            else:
                self._config_store.delete_secret("mobsf_api_key")

            # Emit signal
            self.settings_saved.emit()

            # Show success message
            QMessageBox.information(
                self,
                "Settings Saved",
                "All settings have been saved successfully."
            )

        except Exception as e:
            # Show error message
            QMessageBox.critical(
                self,
                "Error Saving Settings",
                f"Failed to save settings: {e}"
            )

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

    def get_system_prompt(self) -> str:
        """Get the current system prompt value.
        
        Returns:
            Current system prompt
        """
        return self.system_prompt_input.toPlainText()

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
        return 'steps' if self.steps_radio.isChecked() else 'duration'

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

    def get_mobsf_api_key(self) -> str:
        """Get the current MobSF API key.
        
        Returns:
            MobSF API key
        """
        return self.mobsf_api_key_input.text().strip()

    def reset(self):
        """Reset all settings to default values."""
        self.gemini_api_key_input.clear()
        self.openrouter_api_key_input.clear()
        self.system_prompt_input.clear()
        self.max_steps_input.setValue(100)
        self.max_duration_input.setValue(300)
        self.test_username_input.clear()
        self.test_password_input.clear()

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
                f"Please check that you have entered a valid API key."
            )
            return False
        
        if not api_key.startswith(('sk-', 'AIza', 'pk-')) and provider_name != "OpenRouter":
            # Allow more flexible validation for OpenRouter
            if len(api_key) < 30:
                QMessageBox.warning(
                    self,
                    f"Invalid {provider_name} API Key",
                    f"The {provider_name} API key format appears invalid.\n\n"
                    f"Please check that you have entered a valid API key."
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
                self,
                "Invalid MobSF API URL",
                "MobSF API URL cannot be empty when MobSF analysis is enabled."
            )
            return False
        
        # Basic URL format validation
        if not url.startswith(("http://", "https://")):
            QMessageBox.warning(
                self,
                "Invalid MobSF API URL",
                "MobSF API URL must start with http:// or https://\n\n"
                f"Example: http://localhost:8000"
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
                    "MobSF API URL appears to be malformed.\n\n"
                    f"Example: http://localhost:8000"
                )
                return False
        except Exception:
            QMessageBox.warning(
                self,
                "Invalid MobSF API URL",
                "MobSF API URL appears to be malformed.\n\n"
                f"Example: http://localhost:8000"
            )
            return False
        
        return True
