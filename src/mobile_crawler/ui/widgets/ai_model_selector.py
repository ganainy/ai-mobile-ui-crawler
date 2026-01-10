"""AI model selection widget for mobile-crawler GUI."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton
)
from PySide6.QtCore import Signal, QObject

from mobile_crawler.domain.providers.registry import ProviderRegistry
from mobile_crawler.domain.providers.vision_detector import VisionDetector
from mobile_crawler.domain.model_adapters import ModelAdapter


class AIModelSelector(QObject):
    """Widget for selecting AI provider and vision-capable model.

    Provides provider dropdown and model list filtered to vision-capable.
    Emits a signal when a model is selected.
    """

    # Signal emitted when a model is selected
    model_selected = Signal(str, str)  # type: ignore  # (provider, model)

    def __init__(self, provider_registry: ProviderRegistry, vision_detector: VisionDetector, parent=None):
        """Initialize AI model selector widget.

        Args:
            provider_registry: ProviderRegistry instance for fetching models
            vision_detector: VisionDetector instance for filtering vision models
            parent: Parent widget
        """
        super().__init__(parent)
        self.provider_registry = provider_registry
        self.vision_detector = vision_detector
        self._current_provider: str = None
        self._current_model: str = None
        self._provider_models: dict[str, list[str]] = {}
        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()

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
        model_label = QLabel("Vision Model:")
        layout.addWidget(model_label)

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

    def _on_provider_changed(self, provider: str):
        """Handle provider selection change.

        Args:
            provider: Selected provider name
        """
        if not provider or provider == "Select a provider...":
            self.status_label.setText("Select a provider")
            self.status_label.setStyleSheet("color: gray; font-style: italic;")
            self._current_provider = None
            self._current_model = None
            return

        self._current_provider = provider
        self._update_model_list(provider)

    def _on_model_changed(self, model: str):
        """Handle model selection change.

        Args:
            model: Selected model name
        """
        if not model or model == "Select a model..." or model == "No vision models available":
            self.status_label.setText("Select a model")
            self.status_label.setStyleSheet("color: gray; font-style: italic;")
            self._current_model = None
            return

        self._current_model = model
        self.status_label.setText(f"Selected: {model}")
        self.status_label.setStyleSheet("color: green; font-style: italic;")
        self.model_selected.emit(self._current_provider, model)

    def _update_model_list(self, provider: str):
        """Update model list for selected provider.

        Args:
            provider: Provider name
        """
        self.status_label.setText("Loading models...")
        self.status_label.setStyleSheet("color: orange; font-style: italic;")

        try:
            # Get vision-capable models for provider
            vision_models = self.vision_detector.get_vision_models(provider)

            if vision_models:
                # Sort models alphabetically
                vision_models.sort()

                # Populate model combo box
                self.model_combo.clear()
                self.model_combo.addItem("Select a model...", None)
                for model in vision_models:
                    self.model_combo.addItem(model, model)

                # Store models for this provider
                self._provider_models[provider] = vision_models

                self.status_label.setText(f"Found {len(vision_models)} vision models")
                self.status_label.setStyleSheet("color: green; font-style: italic;")
            else:
                self.model_combo.clear()
                self.model_combo.addItem("No vision models available", None)
                self.status_label.setText("No vision models available")
                self.status_label.setStyleSheet("color: red; font-style: italic;")

        except Exception as e:
            self.model_combo.clear()
            self.model_combo.addItem("Error loading models", None)
            self.status_label.setText(f"Error: {e}")
            self.status_label.setStyleSheet("color: red; font-style: italic;")

    def _refresh_models(self):
        """Refresh model list for current provider."""
        if self._current_provider:
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
            provider: Provider name to set
        """
        # Find provider in combo box
        for i in range(self.provider_combo.count()):
            if self.provider_combo.itemText(i) == provider:
                self.provider_combo.setCurrentIndex(i)
                break

    def set_model(self, provider: str, model: str):
        """Set a specific model.

        Args:
            provider: Provider name
            model: Model name
        """
        # First set provider
        self.set_provider(provider)

        # Then set model
        for i in range(self.model_combo.count()):
            if self.model_combo.itemText(i) == model:
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

    def get_widget(self) -> QWidget:
        """Get the underlying QWidget for embedding.

        Returns:
            The QWidget containing the AI model selector UI
        """
        return self.parent() if hasattr(self, 'parent') and isinstance(self.parent(), QWidget) else None
