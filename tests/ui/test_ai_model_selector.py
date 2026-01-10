"""Tests for AIModelSelector widget."""

import pytest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication, QWidget

from mobile_crawler.ui.widgets.ai_model_selector import AIModelSelector
from mobile_crawler.domain.providers.registry import ProviderRegistry
from mobile_crawler.domain.providers.vision_detector import VisionDetector


@pytest.fixture
def qapp():
    """Create QApplication instance for tests."""
    if not QApplication.instance():
        app = QApplication([])
        yield app
        app.quit()
    else:
        yield QApplication.instance()


@pytest.fixture
def ai_model_selector(qapp):
    """Create AIModelSelector instance for tests."""
    mock_registry = Mock(spec=ProviderRegistry)
    mock_detector = Mock(spec=VisionDetector)
    parent_widget = QWidget()
    selector = AIModelSelector(
        provider_registry=mock_registry,
        vision_detector=mock_detector,
        parent=parent_widget
    )
    yield selector
    # Cleanup
    selector.deleteLater()
    parent_widget.deleteLater()


class TestAIModelSelectorInit:
    """Tests for AIModelSelector initialization."""

    def test_initialization(self, qapp, ai_model_selector):
        """Test that AIModelSelector initializes correctly."""
        assert ai_model_selector.provider_registry is not None
        assert ai_model_selector.vision_detector is not None
        assert ai_model_selector.current_provider() is None
        assert ai_model_selector.current_model() is None


class TestProviderSelection:
    """Tests for provider selection functionality."""

    def test_provider_change_updates_model_list(self, qapp, ai_model_selector):
        """Test that changing provider updates model list."""
        # Mock vision detector to return models
        ai_model_selector.vision_detector.get_vision_models = Mock(return_value=[
            "gemini-pro-vision",
            "gemini-1.5-pro"
        ])

        # Set provider
        ai_model_selector.provider_combo.addItem("gemini")
        ai_model_selector.provider_combo.setCurrentIndex(0)

        assert ai_model_selector.current_provider() == "gemini"
        assert ai_model_selector.model_combo.count() == 3  # 2 models + placeholder

    def test_provider_change_with_no_models(self, qapp, ai_model_selector):
        """Test provider change when no vision models available."""
        ai_model_selector.vision_detector.get_vision_models = Mock(return_value=[])

        ai_model_selector.provider_combo.addItem("gemini")
        ai_model_selector.provider_combo.setCurrentIndex(0)

        assert "No vision models available" in ai_model_selector.model_combo.itemText(0)
        assert "No vision models available" in ai_model_selector.status_label.text()

    def test_provider_change_with_error(self, qapp, ai_model_selector):
        """Test provider change when error occurs."""
        ai_model_selector.vision_detector.get_vision_models = Mock(
            side_effect=Exception("API error")
        )

        ai_model_selector.provider_combo.addItem("gemini")
        ai_model_selector.provider_combo.setCurrentIndex(0)

        assert "Error loading models" in ai_model_selector.model_combo.itemText(0)
        assert "Error" in ai_model_selector.status_label.text()


class TestModelSelection:
    """Tests for model selection functionality."""

    def test_model_selection_emits_signal(self, qapp, ai_model_selector):
        """Test that selecting a model emits signal."""
        # Mock vision detector
        ai_model_selector.vision_detector.get_vision_models = Mock(return_value=[
            "gemini-pro-vision"
        ])

        # Track signal emissions
        signal_emitted = []

        def capture_signal(provider, model):
            signal_emitted.append((provider, model))

        ai_model_selector.model_selected.connect(capture_signal)

        # Set provider and model
        ai_model_selector.provider_combo.addItem("gemini")
        ai_model_selector.provider_combo.setCurrentIndex(0)
        ai_model_selector.model_combo.setCurrentIndex(1)

        # Check signal was emitted
        assert len(signal_emitted) == 1
        assert signal_emitted[0] == ("gemini", "gemini-pro-vision")

    def test_model_selection_updates_status(self, qapp, ai_model_selector):
        """Test that selecting a model updates status."""
        ai_model_selector.vision_detector.get_vision_models = Mock(return_value=[
            "gemini-pro-vision"
        ])

        ai_model_selector.provider_combo.addItem("gemini")
        ai_model_selector.provider_combo.setCurrentIndex(0)
        ai_model_selector.model_combo.setCurrentIndex(1)

        assert "Selected: gemini-pro-vision" in ai_model_selector.status_label.text()
        assert "green" in ai_model_selector.status_label.styleSheet()


class TestRefreshModels:
    """Tests for refreshing models."""

    def test_refresh_button_updates_models(self, qapp, ai_model_selector):
        """Test that refresh button updates model list."""
        # First load
        ai_model_selector.vision_detector.get_vision_models = Mock(return_value=[
            "gemini-pro-vision"
        ])

        ai_model_selector.provider_combo.addItem("gemini")
        ai_model_selector.provider_combo.setCurrentIndex(0)

        # Mock new models
        ai_model_selector.vision_detector.get_vision_models = Mock(return_value=[
            "gemini-pro-vision",
            "gemini-1.5-pro"
        ])

        # Click refresh
        ai_model_selector._refresh_models()

        assert ai_model_selector.model_combo.count() == 3  # 2 models + placeholder


class TestCurrentProvider:
    """Tests for current_provider method."""

    def test_current_provider_returns_none_initially(self, qapp, ai_model_selector):
        """Test that current_provider returns None initially."""
        assert ai_model_selector.current_provider() is None

    def test_current_provider_returns_selected_provider(self, qapp, ai_model_selector):
        """Test that current_provider returns selected provider."""
        ai_model_selector.provider_combo.addItem("gemini")
        ai_model_selector.provider_combo.setCurrentIndex(0)

        assert ai_model_selector.current_provider() == "gemini"


class TestCurrentModel:
    """Tests for current_model method."""

    def test_current_model_returns_none_initially(self, qapp, ai_model_selector):
        """Test that current_model returns None initially."""
        assert ai_model_selector.current_model() is None

    def test_current_model_returns_selected_model(self, qapp, ai_model_selector):
        """Test that current_model returns selected model."""
        ai_model_selector.vision_detector.get_vision_models = Mock(return_value=[
            "gemini-pro-vision"
        ])

        ai_model_selector.provider_combo.addItem("gemini")
        ai_model_selector.provider_combo.setCurrentIndex(0)
        ai_model_selector.model_combo.setCurrentIndex(1)

        assert ai_model_selector.current_model() == "gemini-pro-vision"


class TestSetProvider:
    """Tests for set_provider method."""

    def test_set_provider(self, qapp, ai_model_selector):
        """Test setting a specific provider."""
        ai_model_selector.vision_detector.get_vision_models = Mock(return_value=[])

        ai_model_selector.provider_combo.addItem("gemini")
        ai_model_selector.provider_combo.addItem("openrouter")

        ai_model_selector.set_provider("openrouter")

        assert ai_model_selector.current_provider() == "openrouter"


class TestSetModel:
    """Tests for set_model method."""

    def test_set_model(self, qapp, ai_model_selector):
        """Test setting a specific model."""
        ai_model_selector.vision_detector.get_vision_models = Mock(return_value=[
            "gemini-pro-vision",
            "gemini-1.5-pro"
        ])

        ai_model_selector.provider_combo.addItem("gemini")
        ai_model_selector.set_model("gemini", "gemini-1.5-pro")

        assert ai_model_selector.current_provider() == "gemini"
        assert ai_model_selector.current_model() == "gemini-1.5-pro"


class TestClear:
    """Tests for clear method."""

    def test_clear_resets_state(self, qapp, ai_model_selector):
        """Test that clear resets all state."""
        # Set provider and model
        ai_model_selector.vision_detector.get_vision_models = Mock(return_value=[
            "gemini-pro-vision"
        ])

        ai_model_selector.provider_combo.addItem("gemini")
        ai_model_selector.provider_combo.setCurrentIndex(0)
        ai_model_selector.model_combo.setCurrentIndex(1)

        # Clear
        ai_model_selector.clear()

        assert ai_model_selector.current_provider() is None
        assert ai_model_selector.current_model() is None
        assert "Select a provider" in ai_model_selector.status_label.text()


class TestUIComponents:
    """Tests for UI components."""

    def test_provider_combo_exists(self, qapp, ai_model_selector):
        """Test that provider combo box exists."""
        assert ai_model_selector.provider_combo is not None

    def test_model_combo_exists(self, qapp, ai_model_selector):
        """Test that model combo box exists."""
        assert ai_model_selector.model_combo is not None

    def test_refresh_button_exists(self, qapp, ai_model_selector):
        """Test that refresh button exists."""
        assert ai_model_selector.refresh_button is not None
        assert ai_model_selector.refresh_button.text() == "Refresh Models"

    def test_status_label_exists(self, qapp, ai_model_selector):
        """Test that status label exists."""
        assert ai_model_selector.status_label is not None


class TestModelSorting:
    """Tests for model list sorting."""

    def test_models_sorted_alphabetically(self, qapp, ai_model_selector):
        """Test that models are sorted alphabetically."""
        unsorted_models = [
            "zeta-model",
            "alpha-model",
            "beta-model"
        ]

        ai_model_selector.vision_detector.get_vision_models = Mock(return_value=unsorted_models)

        ai_model_selector.provider_combo.addItem("test")
        ai_model_selector.provider_combo.setCurrentIndex(0)

        # Check models are sorted (skip placeholder at index 0)
        assert ai_model_selector.model_combo.itemText(1) == "alpha-model"
        assert ai_model_selector.model_combo.itemText(2) == "beta-model"
        assert ai_model_selector.model_combo.itemText(3) == "zeta-model"
