"""Tests for ProviderRegistry.

Mocks AI provider APIs to avoid making real API calls.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

import pytest

from mobile_crawler.domain.providers.registry import ProviderRegistry, CACHE_EXPIRATION_DAYS


@pytest.fixture
def mock_config_store():
    """Create a mock UserConfigStore."""
    store = Mock()
    store.get_setting.return_value = None
    store.set_setting.return_value = None
    store.delete_setting.return_value = None
    return store


@pytest.fixture
def registry(mock_config_store):
    """Create a ProviderRegistry with mock config store."""
    return ProviderRegistry(config_store=mock_config_store)


@pytest.fixture
def registry_no_store():
    """Create a ProviderRegistry without config store."""
    return ProviderRegistry(config_store=None)


class TestProviderRegistryInitialization:
    """Tests for ProviderRegistry initialization."""

    def test_init_with_config_store(self, mock_config_store):
        """Test initialization with ConfigManager."""
        reg = ProviderRegistry(config_store=mock_config_store)
        assert reg._config_store == mock_config_store
        assert reg._cache == {}

    def test_init_without_config_store(self):
        """Test initialization without config store."""
        reg = ProviderRegistry(config_store=None)
        assert reg._config_store is None
        assert reg._cache == {}

    def test_init_loads_persistent_cache(self, mock_config_store):
        """Test initialization attempts to load persistent cache."""
        mock_config_store.get_setting.return_value = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "models": {"gemini": [{"id": "model1"}]}
        }
        reg = ProviderRegistry(config_store=mock_config_store)
        mock_config_store.get_setting.assert_called_with("model_cache", default=None)
        assert "gemini" in reg._cache


class TestProviderRegistryGemini:
    """Tests for Gemini model fetching."""

    def _mock_genai_module(self):
        """Create a mock google.genai module."""
        mock_genai = Mock()
        mock_client = Mock()
        mock_model = Mock()
        mock_model.name = "models/gemini-1.5-flash"
        mock_model.display_name = "Gemini 1.5 Flash"
        mock_model.description = "Fast multimodal model"
        mock_model.supported_actions = ["generateContent"]
        mock_client.models.list.return_value = [mock_model]
        mock_genai.Client.return_value = mock_client
        return mock_genai

    def test_fetch_gemini_models(self, registry):
        """Test fetch_gemini_models returns model list."""
        mock_genai = self._mock_genai_module()
        with patch.dict('sys.modules', {'google.genai': mock_genai}):
            models = registry.fetch_gemini_models(api_key="test_key")

        assert len(models) > 0
        assert models[0]["id"] == "gemini-1.5-flash"
        assert models[0]["provider"] == "google"
        assert models[0]["supports_vision"] is True

    def test_fetch_gemini_models_caches_result(self, registry):
        """Test fetch_gemini_models caches results."""
        mock_genai = self._mock_genai_module()
        with patch.dict('sys.modules', {'google.genai': mock_genai}):
            models1 = registry.fetch_gemini_models(api_key="test_key")
            models2 = registry.fetch_gemini_models(api_key="test_key")

        # Should only call API once
        mock_genai.Client.return_value.models.list.assert_called_once()

    def test_fetch_gemini_models_adds_preview_models(self, registry):
        """Test fetch_gemini_models manually adds preview models."""
        mock_genai = self._mock_genai_module()
        with patch.dict('sys.modules', {'google.genai': mock_genai}):
            models = registry.fetch_gemini_models(api_key="test_key")

        ids = [m["id"] for m in models]
        assert "gemini-3-pro-preview" in ids
        assert "gemini-3-flash-preview" in ids

    def test_fetch_gemini_models_error(self, registry):
        """Test fetch_gemini_models raises RuntimeError on failure."""
        mock_genai = Mock()
        mock_genai.Client.side_effect = Exception("API error")
        with patch.dict('sys.modules', {'google.genai': mock_genai}):
            with pytest.raises(RuntimeError, match="Failed to fetch Gemini models"):
                registry.fetch_gemini_models(api_key="bad_key")


class TestProviderRegistryOpenRouter:
    """Tests for OpenRouter model fetching."""

    @patch('mobile_crawler.domain.providers.registry.requests.get')
    def test_fetch_openrouter_models(self, mock_get, registry):
        """Test fetch_openrouter_models returns model list."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "anthropic/claude-3.5-sonnet",
                    "name": "Claude 3.5 Sonnet",
                    "architecture": {
                        "input_modalities": ["text", "image"]
                    },
                    "pricing": {
                        "prompt": "0.000003",
                        "completion": "0.000015",
                        "image": "0.000003"
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        models = registry.fetch_openrouter_models(api_key="test_key")

        assert len(models) > 0
        assert models[0]["id"] == "anthropic/claude-3.5-sonnet"
        assert models[0]["supports_vision"] is True
        assert "pricing" in models[0]

    @patch('mobile_crawler.domain.providers.registry.requests.get')
    def test_fetch_openrouter_models_error_returns_fallback(self, mock_get, registry):
        """Test fetch_openrouter_models returns fallback on error."""
        mock_get.side_effect = Exception("Network error")

        models = registry.fetch_openrouter_models(api_key="bad_key")

        # Should return fallback list with known vision models
        assert len(models) > 0
        ids = [m["id"] for m in models]
        assert "anthropic/claude-3.5-sonnet" in ids

    @patch('mobile_crawler.domain.providers.registry.requests.get')
    def test_fetch_openrouter_models_caches_result(self, mock_get, registry):
        """Test fetch_openrouter_models caches results."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        registry.fetch_openrouter_models(api_key="test_key")
        registry.fetch_openrouter_models(api_key="test_key")

        # Should only call API once
        mock_get.assert_called_once()


class TestProviderRegistryOllama:
    """Tests for Ollama model fetching."""

    @patch('mobile_crawler.domain.providers.registry.requests.get')
    def test_fetch_ollama_models(self, mock_get, registry):
        """Test fetch_ollama_models returns model list."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "models": [
                {"name": "llama2", "details": {}},
                {"name": "llava", "details": {}},
            ]
        }
        mock_get.return_value = mock_response

        models = registry.fetch_ollama_models()

        assert len(models) == 2
        assert models[0]["id"] == "llama2"
        assert models[0]["provider"] == "ollama"

    @patch('mobile_crawler.domain.providers.registry.requests.get')
    def test_fetch_ollama_models_error_returns_empty(self, mock_get, registry):
        """Test fetch_ollama_models returns empty list on error."""
        mock_get.side_effect = Exception("Connection refused")

        models = registry.fetch_ollama_models()

        assert models == []

    @patch('mobile_crawler.domain.providers.registry.requests.get')
    def test_fetch_ollama_models_caches_by_url(self, mock_get, registry):
        """Test fetch_ollama_models caches by base URL."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"models": []}
        mock_get.return_value = mock_response

        registry.fetch_ollama_models(base_url="http://localhost:11434")
        registry.fetch_ollama_models(base_url="http://localhost:11434")

        mock_get.assert_called_once()


class TestProviderRegistryVisionDetection:
    """Tests for vision model detection."""

    def test_is_gemini_vision_model_name_pattern(self, registry):
        """Test _is_gemini_vision_model detects vision by name."""
        assert registry._is_gemini_vision_model("gemini-1.5-flash") is True
        assert registry._is_gemini_vision_model("gemini-2.0-pro") is True
        assert registry._is_gemini_vision_model("gemini-3-flash-preview") is True

    def test_is_gemini_vision_model_excludes_text_only(self, registry):
        """Test _is_gemini_vision_model excludes text-only models."""
        assert registry._is_gemini_vision_model("text-bison-001") is False
        assert registry._is_gemini_vision_model("embedding-model") is False

    def test_is_gemini_vision_model_with_api_metadata(self, registry):
        """Test _is_gemini_vision_model uses API metadata."""
        mock_model = Mock()
        mock_model.supported_actions = ["generateContent"]
        mock_model.description = "Multimodal model"
        assert registry._is_gemini_vision_model("gemini-1.5-flash", model=mock_model) is True

    def test_is_openrouter_vision_model(self, registry):
        """Test _is_openrouter_vision_model detects vision models."""
        model = {
            "architecture": {"input_modalities": ["text", "image"]},
            "id": "claude-3",
            "name": "Claude 3"
        }
        assert registry._is_openrouter_vision_model(model) is True

    def test_is_openrouter_vision_model_fallback(self, registry):
        """Test _is_openrouter_vision_model falls back to keywords."""
        model = {
            "architecture": {},
            "id": "gpt-4o",
            "name": "GPT-4o"
        }
        assert registry._is_openrouter_vision_model(model) is True

    def test_is_ollama_vision_model(self, registry):
        """Test _is_ollama_vision_model detects vision models."""
        model = {"name": "llava-v1.5", "details": {}}
        assert registry._is_ollama_vision_model(model) is True

    def test_is_ollama_vision_model_not_vision(self, registry):
        """Test _is_ollama_vision_model returns False for non-vision."""
        model = {"name": "llama2", "details": {}}
        assert registry._is_ollama_vision_model(model) is False


class TestProviderRegistryCache:
    """Tests for cache management."""

    def test_clear_cache_all(self, registry):
        """Test clear_cache clears all providers."""
        registry._cache = {"gemini": [{"id": "model1"}], "ollama": [{"id": "model2"}]}
        registry.clear_cache()
        assert registry._cache == {}

    def test_clear_cache_specific_provider(self, registry):
        """Test clear_cache clears specific provider."""
        registry._cache = {"gemini": [{"id": "model1"}], "ollama": [{"id": "model2"}]}
        registry.clear_cache(provider="gemini")
        assert "gemini" not in registry._cache
        assert "ollama" in registry._cache

    def test_clear_cache_persistent(self, registry, mock_config_store):
        """Test clear_cache clears persistent cache."""
        registry._cache = {"gemini": [{"id": "model1"}]}
        registry.clear_cache()
        mock_config_store.delete_setting.assert_called_once_with("model_cache")

    def test_load_persistent_cache_expired(self, registry, mock_config_store):
        """Test _load_persistent_cache ignores expired cache."""
        old_date = (datetime.now(timezone.utc) - timedelta(days=CACHE_EXPIRATION_DAYS + 1)).isoformat()
        mock_config_store.get_setting.return_value = {
            "cached_at": old_date,
            "models": {"gemini": [{"id": "model1"}]}
        }
        registry._load_persistent_cache()
        assert "gemini" not in registry._cache

    def test_load_persistent_cache_valid(self, registry, mock_config_store):
        """Test _load_persistent_cache loads valid cache."""
        recent_date = datetime.now(timezone.utc).isoformat()
        mock_config_store.get_setting.return_value = {
            "cached_at": recent_date,
            "models": {"gemini": [{"id": "model1"}]}
        }
        registry._load_persistent_cache()
        assert "gemini" in registry._cache

    def test_save_persistent_cache(self, registry, mock_config_store):
        """Test _save_persistent_cache saves to config store."""
        registry._cache = {"gemini": [{"id": "model1"}]}
        registry._save_persistent_cache()
        mock_config_store.set_setting.assert_called_once()
        call_args = mock_config_store.set_setting.call_args
        assert call_args[0][0] == "model_cache"

    def test_load_persistent_cache_no_store(self, registry_no_store):
        """Test _load_persistent_cache returns early without store."""
        # Should not raise
        registry_no_store._load_persistent_cache()
        assert registry_no_store._cache == {}
