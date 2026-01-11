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

        # Max Steps
        max_steps_layout = QHBoxLayout()
        max_steps_label = QLabel("Max Steps:")
        max_steps_layout.addWidget(max_steps_label)
        self.max_steps_input = QSpinBox()
        self.max_steps_input.setRange(1, 10000)
        self.max_steps_input.setValue(100)
        self.max_steps_input.setSingleStep(10)
        max_steps_layout.addWidget(self.max_steps_input)
        limits_layout.addLayout(max_steps_layout)

        # Max Duration
        max_duration_layout = QHBoxLayout()
        max_duration_label = QLabel("Max Duration (seconds):")
        max_duration_layout.addWidget(max_duration_label)
        self.max_duration_input = QSpinBox()
        self.max_duration_input.setRange(10, 3600)
        self.max_duration_input.setValue(300)
        self.max_duration_input.setSingleStep(30)
        max_duration_layout.addWidget(self.max_duration_input)
        limits_layout.addLayout(max_duration_layout)

        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)

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

    def _load_settings(self):
        """Load settings from user_config.db."""
        # Load API keys
        gemini_key = self._config_store.get_secret_plaintext("gemini_api_key")
        if gemini_key:
            self.gemini_api_key_input.setText(gemini_key)

        openrouter_key = self._config_store.get_secret_plaintext("openrouter_api_key")
        if openrouter_key:
            self.openrouter_api_key_input.setText(openrouter_key)

        # Load system prompt
        system_prompt = self._config_store.get_setting("system_prompt", default="")
        self.system_prompt_input.setPlainText(system_prompt)

        # Load crawl limits
        max_steps = self._config_store.get_setting("max_steps", default=100)
        self.max_steps_input.setValue(max_steps)

        max_duration = self._config_store.get_setting("max_duration_seconds", default=300)
        self.max_duration_input.setValue(max_duration)

        # Load test credentials
        test_username = self._config_store.get_setting("test_username", default="")
        self.test_username_input.setText(test_username)

        test_password = self._config_store.get_secret_plaintext("test_password")
        if test_password:
            self.test_password_input.setText(test_password)

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

    def get_test_username(self) -> str:
        """Get the current test username value.
        
        Returns:
            Current test username
        """
        return self.test_username_input.text()

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
