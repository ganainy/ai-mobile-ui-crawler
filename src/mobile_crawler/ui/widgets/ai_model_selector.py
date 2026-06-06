"""AI model selection widget for mobile-crawler GUI."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from mobile_crawler.domain.providers.registry import ProviderRegistry
from mobile_crawler.domain.providers.vision_detector import VisionDetector
from mobile_crawler.ui.async_utils import AsyncOperation

if TYPE_CHECKING:
    from mobile_crawler.infrastructure.user_config_store import UserConfigStore


class AIModelSelector(QWidget):
    """Widget for selecting AI provider and model.

    Provides provider dropdown and searchable model list.
    Emits a signal when a model is selected.
    Persists last selected provider and model across sessions.

    Args:
        provider_registry: ProviderRegistry instance for fetching models
        vision_detector: Legacy VisionDetector dependency kept for compatibility
        config_store: UserConfigStore instance for persisting provider/model selection
        parent: Parent widget
    """

    # Signal emitted when a model is selected
    model_selected = Signal(str, str)  # type: ignore  # (provider, model)

    def __init__(self, provider_registry: ProviderRegistry, vision_detector: VisionDetector, config_store: "UserConfigStore", parent=None):
        """Initialize AI model selector widget.

        Args:
            provider_registry: ProviderRegistry instance for fetching models
            vision_detector: Legacy VisionDetector dependency kept for compatibility
            config_store: UserConfigStore instance for persisting provider/model selection
            parent: Parent widget
        """
        super().__init__(parent)
        self.provider_registry = provider_registry
        self.vision_detector = vision_detector
        self._config_store = config_store
        self._current_provider: str = None
        self._current_model: str = None
        self._provider_models: dict[str, list[str]] = {}
        self._provider_model_records: dict[str, list[dict]] = {}
        self._api_key_callback: Callable[[str], str] | None = None
        self._setup_ui()
        self._populate_providers()
        self._load_selection()

    def set_api_key_callback(self, callback: Callable[[str], str]):
        """Set callback for getting API keys by provider name.

        Args:
            callback: Function that takes provider name and returns API key
        """
        self._api_key_callback = callback

        # Defer restoration to allow Qt event loop to process pending events
        # This ensures SettingsPanel has fully loaded API keys before we try to use them
        if hasattr(self, '_saved_provider') and self._saved_provider:
            QTimer.singleShot(0, self._restore_saved_selection)

    def _restore_saved_selection(self):
        """Restore saved provider/model selection after event loop processes."""
        if not hasattr(self, '_saved_provider') or not self._saved_provider:
            return

        self._restoring_selection = True
        try:
            for i in range(self.provider_combo.count()):
                if self.provider_combo.itemData(i) == self._saved_provider:
                    self.provider_combo.setCurrentIndex(i)
                    break
        finally:
            self._restoring_selection = False

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Provider label
        provider_label = QLabel("AI Provider:")
        layout.addWidget(provider_label)

        # Provider dropdown row
        provider_layout = QHBoxLayout()

        self.provider_combo = QComboBox()
        self.provider_combo.setMinimumWidth(200)
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.provider_combo)

        # Refresh button
        self.refresh_button = QPushButton("Refresh Models")
        self.refresh_button.clicked.connect(self._refresh_models)
        provider_layout.addWidget(self.refresh_button)

        layout.addLayout(provider_layout)

        # Model label
        model_label = QLabel("AI Model:")
        layout.addWidget(model_label)

        self.model_search_input = QLineEdit()
        self.model_search_input.setPlaceholderText("Search models...")
        self.model_search_input.textChanged.connect(self._on_model_search_changed)
        layout.addWidget(self.model_search_input)

        # Model dropdown
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(300)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        layout.addWidget(self.model_combo)

        # Status label
        self.status_label = QLabel("Select a provider")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def _load_selection(self):
        """Load previously saved provider and model from config store."""
        saved_provider = self._config_store.get_setting("last_ai_provider", default=None)
        saved_model = self._config_store.get_setting("last_ai_model", default=None)
        self._saved_provider = saved_provider
        self._saved_model = saved_model
        # Note: Don't apply selection here - wait for API key callback to be set
        # The selection will be applied in set_api_key_callback()

    def _populate_providers(self):
        """Populate the provider dropdown with available AI providers."""
        self.provider_combo.clear()
        self.provider_combo.addItem("Select a provider...", None)

        # Add supported providers
        providers = [
            ("Gemini", "gemini"),
            ("OpenRouter", "openrouter"),
            ("Ollama (Local)", "ollama"),
        ]

        for display_name, provider_id in providers:
            self.provider_combo.addItem(display_name, provider_id)

    def _on_provider_changed(self, provider: str):
        """Handle provider selection change.

        Args:
            provider: Selected provider display name
        """
        # Get the actual provider ID from the item data
        provider_id = self.provider_combo.currentData()

        if not provider_id:
            self.status_label.setText("Select a provider")
            self.status_label.setStyleSheet("color: gray; font-style: italic;")
            self._current_provider = None
            self._current_model = None
            self.model_search_input.clear()
            self.model_combo.clear()
            self.model_combo.addItem("Select a model...", None)
            return

        self._current_provider = provider_id
        self._current_model = None
        self.model_search_input.clear()
        # Save provider to config store
        self._config_store.set_setting("last_ai_provider", provider_id, "string")
        self._update_model_list(provider_id)

    def _format_model_display(self, model_id: str, model: dict) -> str:
        """Format model display text with pricing info if available.

        Args:
            model_id: Model identifier
            model: Model dictionary with optional pricing

        Returns:
            Formatted display string
        """
        pricing = model.get('pricing', {})
        if pricing and pricing.get('prompt_per_1M') and pricing.get('prompt_per_1M') != 'N/A':
            return f"{model_id}  (in: ${pricing['prompt_per_1M']}/M  out: ${pricing['completion_per_1M']}/M)"
        return model_id

    def _on_model_changed(self, model_text: str):
        """Handle model selection change.

        Args:
            model_text: Selected model display text
        """
        model_id = self.model_combo.currentData()
        if not model_id:
            self.status_label.setText("Select a model")
            self.status_label.setStyleSheet("color: gray; font-style: italic;")
            self._current_model = None
            return

        self._current_model = model_id
        self._config_store.set_setting("last_ai_model", model_id, "string")
        self.status_label.setText(f"Selected: {model_id}")
        self.status_label.setStyleSheet("color: green; font-style: italic;")
        self.model_selected.emit(self._current_provider, model_id)

    def _update_model_list(self, provider: str):
        """Update model list for selected provider.

        Args:
            provider: Provider name
        """
        self.status_label.setText("Loading models...")
        self.status_label.setStyleSheet("color: orange; font-style: italic;")

        # Get API key for providers that require it
        api_key = None
        if provider in ['gemini', 'openrouter']:
            if self._api_key_callback:
                api_key = self._api_key_callback(provider)

            if not api_key:
                # Only show error dialog if not restoring saved selection
                if not getattr(self, '_restoring_selection', False):
                    QMessageBox.warning(
                        self,
                        "API Key Required",
                        f"Please enter your {provider.title()} API key in the Settings panel below,\n"
                        f"then click 'Save Settings' before selecting this provider."
                    )
                self.model_combo.clear()
                self.model_combo.addItem("API key required", None)
                self.status_label.setText("API key required")
                self.status_label.setStyleSheet("color: red; font-style: italic;")
                return

        self.refresh_button.setEnabled(False)
        self.provider_combo.setEnabled(False)

        # Create async operation
        self._model_thread = AsyncOperation(self._fetch_models, args=(provider, api_key))
        self._model_thread.result_ready.connect(lambda models: self._on_models_success(provider, models))
        self._model_thread.error_occurred.connect(self._on_models_error)
        self._model_thread.finished_signal.connect(self._on_models_finished)
        self._model_thread.start()

    def _fetch_models(self, provider: str, api_key: str | None) -> list[dict]:
        """Fetch all available models for a provider."""
        if provider == "gemini":
            return self.provider_registry.fetch_gemini_models(api_key or "")
        if provider == "openrouter":
            return self.provider_registry.fetch_openrouter_models(api_key or "")
        if provider == "ollama":
            return self.provider_registry.fetch_ollama_models()
        raise ValueError(f"Unsupported provider: {provider}")

    def _on_models_success(self, provider: str, models: list):
        """Handle successful model list retrieval."""
        if models:
            # Build display entries with pricing (sorted alphabetically by id)
            sorted_models = sorted(models, key=lambda m: m.get('id', m.get('name', str(m))) if isinstance(m, dict) else str(m))

            # Store model ids for this provider
            self._provider_model_records[provider] = [
                m if isinstance(m, dict) else {"id": str(m), "name": str(m)}
                for m in sorted_models
            ]
            self._provider_models[provider] = [
                m.get('id', m.get('name', str(m))) if isinstance(m, dict) else str(m)
                for m in sorted_models
            ]
            self._populate_model_combo(provider)

            self.status_label.setText(f"Found {len(sorted_models)} models")
            self.status_label.setStyleSheet("color: green; font-style: italic;")

            # Restore saved model selection if it matches this provider
            if hasattr(self, '_saved_model') and self._saved_model:
                for i in range(self.model_combo.count()):
                    if self.model_combo.itemData(i) == self._saved_model:
                        self.model_combo.setCurrentIndex(i)
                        break
                self._saved_model = None  # Clear after use
        else:
            self._provider_model_records[provider] = []
            self._provider_models[provider] = []
            self.model_combo.clear()
            self.model_combo.addItem("No models available", None)
            self.status_label.setText("No models available")
            self.status_label.setStyleSheet("color: red; font-style: italic;")

    def _populate_model_combo(self, provider: str):
        """Populate model dropdown from cached records and current search text."""
        records = self._provider_model_records.get(provider, [])
        query = self.model_search_input.text().strip().lower()

        def matches(model: dict) -> bool:
            if not query:
                return True
            model_id = str(model.get('id', model.get('name', '')))
            display_text = self._format_model_display(model_id, model)
            haystack = " ".join(
                str(part)
                for part in (
                    model_id,
                    model.get('name', ''),
                    model.get('provider', ''),
                    display_text,
                )
            ).lower()
            return query in haystack

        filtered = [model for model in records if matches(model)]
        previous_model = self._current_model

        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItem("Select a model...", None)
        for model in filtered:
            model_id = model.get('id', model.get('name', str(model)))
            display_text = self._format_model_display(model_id, model)
            self.model_combo.addItem(display_text, model_id)

        if not filtered and query:
            self.model_combo.addItem("No matching models", None)

        if previous_model:
            for i in range(self.model_combo.count()):
                if self.model_combo.itemData(i) == previous_model:
                    self.model_combo.setCurrentIndex(i)
                    break
        self.model_combo.blockSignals(False)

    def _on_model_search_changed(self, _text: str):
        """Filter loaded models by the search text."""
        if not self._current_provider:
            return
        self._populate_model_combo(self._current_provider)
        total = len(self._provider_model_records.get(self._current_provider, []))
        visible = max(self.model_combo.count() - 1, 0)
        if self.model_combo.findData(None) >= 0 and self.model_combo.itemText(1) == "No matching models":
            visible = 0
        if self.model_search_input.text().strip():
            self.status_label.setText(f"Showing {visible} of {total} models")
            self.status_label.setStyleSheet("color: gray; font-style: italic;")
        elif total:
            self.status_label.setText(f"Found {total} models")
            self.status_label.setStyleSheet("color: green; font-style: italic;")

    def _on_models_error(self, error: str):
        """Handle model list retrieval error."""
        self.model_combo.clear()
        self.model_combo.addItem("Error loading models", None)
        self.status_label.setText(f"Error: {error}")
        self.status_label.setStyleSheet("color: red; font-style: italic;")

    def _on_models_finished(self):
        """Re-enable controls after fetch."""
        self.refresh_button.setEnabled(True)
        self.provider_combo.setEnabled(True)

    def _refresh_models(self):
        """Refresh model list for current provider."""
        if self._current_provider:
            # Clear all cache to force fresh fetch
            self.provider_registry.clear_cache()
            self._update_model_list(self._current_provider)

    def current_provider(self) -> str:
        """Get the currently selected provider.

        Returns:
            Currently selected provider or None
        """
        return self._current_provider

    def current_model(self) -> str:
        """Get the currently selected model.

        Returns:
            Currently selected model or None
        """
        return self._current_model

    def set_provider(self, provider: str):
        """Set a specific provider.

        Args:
            provider: Provider id to set
        """
        # Find provider in combo box by data
        for i in range(self.provider_combo.count()):
            if self.provider_combo.itemData(i) == provider:
                self.provider_combo.setCurrentIndex(i)
                break

    def set_model(self, provider: str, model: str):
        """Set a specific model.

        Args:
            provider: Provider name
            model: Model name
        """
        self._saved_model = model

        # First set provider
        self.set_provider(provider)

        # Then set model
        for i in range(self.model_combo.count()):
            if self.model_combo.itemData(i) == model:
                self.model_combo.setCurrentIndex(i)
                break

    def clear(self):
        """Clear current selection."""
        self.provider_combo.setCurrentIndex(0)
        self.model_combo.clear()
        self.model_combo.addItem("Select a model...", None)
        self.status_label.setText("Select a provider")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        self._current_provider = None
        self._current_model = None
        # Clear saved provider and model
        self._config_store.delete_setting("last_ai_provider")
        self._config_store.delete_setting("last_ai_model")
