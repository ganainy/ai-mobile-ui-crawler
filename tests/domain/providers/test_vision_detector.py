"""Tests for VisionDetector and ProviderRegistry."""

from unittest.mock import MagicMock, patch

import pytest

from mobile_crawler.domain.providers.registry import ProviderRegistry
from mobile_crawler.domain.providers.vision_detector import VisionDetector


class TestProviderRegistry:
    """Tests for ProviderRegistry."""

    def test_init(self):
        """Test registry initialization."""
        registry = ProviderRegistry()
        assert registry._cache == {}

    def test_clear_cache(self):
        registry = ProviderRegistry()
        registry._cache = {'gemini': [], 'openrouter': []}
        registry.clear_cache()
        assert registry._cache == {}

    @patch('google.genai.Client')
    def test_fetch_gemini_models_success(self, mock_genai_client):
        """Test successful Gemini model fetch."""
        # Mock the client and models
        mock_client = MagicMock()
        mock_model1 = MagicMock()
        mock_model1.name = 'models/gemini-1.5-pro'
        mock_model1.display_name = 'Gemini 1.5 Pro'
        mock_model1.description = 'Gemini 1.5 Pro, a multimodal model'
        mock_model1.supported_actions = ['generateContent', 'countTokens', 'createCachedContent']
        mock_model2 = MagicMock()
        mock_model2.name = 'models/gemini-1.5-flash'
        mock_model2.display_name = 'Gemini 1.5 Flash'
        mock_model2.description = 'Gemini 1.5 Flash, our fast multimodal model'
        mock_model2.supported_actions = ['generateContent', 'countTokens', 'createCachedContent']

        mock_client.models.list.return_value = [mock_model1, mock_model2]
        mock_genai_client.return_value = mock_client

        registry = ProviderRegistry()
        models = registry.fetch_gemini_models('test_api_key')

        # 2 from API + 2 Gemini 3 fallback models
        assert len(models) == 4
        # First two are from API (prefix stripped)
        assert models[0]['id'] == 'gemini-1.5-pro'
        assert models[0]['name'] == 'Gemini 1.5 Pro'
        assert models[0]['provider'] == 'google'
        assert models[0]['supports_vision'] is True
        assert 'description' in models[0]
        assert 'supported_actions' in models[0]
        assert models[1]['id'] == 'gemini-1.5-flash'
        # Gemini 3 fallbacks are added when not in API response
        fallback_ids = {m['id'] for m in models[2:]}
        assert 'gemini-3-pro-preview' in fallback_ids
        assert 'gemini-3-flash-preview' in fallback_ids

    @patch('google.genai.Client')
    def test_fetch_gemini_models_failure_fallback(self, mock_genai_client):
        """Test Gemini model fetch raises RuntimeError on API error."""
        mock_genai_client.side_effect = Exception("API error")

        registry = ProviderRegistry()
        with pytest.raises(RuntimeError, match="Failed to fetch Gemini models"):
            registry.fetch_gemini_models('test_api_key')

    @patch('mobile_crawler.domain.providers.registry.requests.get')
    def test_fetch_openrouter_models_success(self, mock_get):
        """Test successful OpenRouter model fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': [
                {
                    'id': 'anthropic/claude-3.5-sonnet',
                    'name': 'Claude 3.5 Sonnet',
                    'architecture': {'input_modalities': ['text', 'image']},
                    'pricing': {'prompt': '0.000003', 'completion': '0.000015', 'image': '0.000003'}
                },
                {
                    'id': 'openai/gpt-4',
                    'name': 'GPT-4',
                    'architecture': {'input_modalities': ['text']},
                    'pricing': {'prompt': '0.00003', 'completion': '0.00006', 'image': '0'}
                }
            ]
        }
        mock_get.return_value = mock_response

        registry = ProviderRegistry()
        models = registry.fetch_openrouter_models('test_api_key')

        assert len(models) == 2
        assert models[0]['id'] == 'anthropic/claude-3.5-sonnet'
        assert models[0]['supports_vision'] is True
        assert models[0]['input_modalities'] == ['text', 'image']
        assert 'pricing' in models[0]
        assert models[0]['pricing']['prompt_per_1M'] == '3.0000'
        assert models[0]['pricing']['completion_per_1M'] == '15.0000'
        assert models[0]['pricing']['image_per_1M'] == '3.0000'
        assert models[1]['id'] == 'openai/gpt-4'
        assert models[1]['supports_vision'] is False

    @patch('mobile_crawler.domain.providers.registry.requests.get')
    def test_fetch_openrouter_models_failure_fallback(self, mock_get):
        """Test OpenRouter model fetch with fallback on error."""
        mock_get.side_effect = Exception("Network error")

        registry = ProviderRegistry()
        models = registry.fetch_openrouter_models('test_api_key')

        # Should return fallback models
        assert len(models) == 4
        assert models[0]['id'] == 'anthropic/claude-3.5-sonnet'
        assert models[0]['supports_vision'] is True

    @patch('mobile_crawler.domain.providers.registry.requests.get')
    def test_fetch_ollama_models_success(self, mock_get):
        """Test successful Ollama model fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'models': [
                {
                    'name': 'llava:latest',
                    'details': {'projector_type': 'mlp'}
                },
                {
                    'name': 'llama3.2:latest',
                    'details': {}
                }
            ]
        }
        mock_get.return_value = mock_response

        registry = ProviderRegistry()
        models = registry.fetch_ollama_models('http://localhost:11434')

        assert len(models) == 2
        assert models[0]['id'] == 'llava:latest'
        assert models[0]['supports_vision'] is True
        assert models[1]['id'] == 'llama3.2:latest'
        assert models[1]['supports_vision'] is False

    @patch('mobile_crawler.domain.providers.registry.requests.get')
    def test_fetch_ollama_models_failure(self, mock_get):
        """Test Ollama model fetch on error."""
        mock_get.side_effect = Exception("Connection error")

        registry = ProviderRegistry()
        models = registry.fetch_ollama_models('http://localhost:11434')

        # Should return empty list (no reliable fallback)
        assert models == []

    def test_is_gemini_vision_model(self):
        """Test Gemini vision model detection."""
        registry = ProviderRegistry()

        # Name-pattern detection (no model object)
        assert registry._is_gemini_vision_model('models/gemini-1.5-pro') is True
        assert registry._is_gemini_vision_model('models/gemini-1.5-flash') is True
        assert registry._is_gemini_vision_model('models/gemini-2.0-pro') is True
        assert registry._is_gemini_vision_model('models/gemini-pro-vision') is True
        assert registry._is_gemini_vision_model('models/gemini-1.0-pro-vision') is True
        assert registry._is_gemini_vision_model('models/gemini-3-pro-preview') is True
        assert registry._is_gemini_vision_model('models/gemini-3-flash-preview') is True
        assert registry._is_gemini_vision_model('models/text-only-model') is False
        # Always-text-only models
        assert registry._is_gemini_vision_model('models/gemini-embedding-001') is False
        assert registry._is_gemini_vision_model('models/gemma-3-27b-it') is False
        assert registry._is_gemini_vision_model('models/imagen-4.0-generate-001') is False
        # TTS/audio models excluded by name pattern
        assert registry._is_gemini_vision_model('models/gemini-2.5-flash-preview-tts') is False
        assert registry._is_gemini_vision_model('models/gemini-2.5-flash-native-audio-latest') is False
        assert registry._is_gemini_vision_model('models/gemini-3.1-flash-live-preview') is False

    def test_is_gemini_vision_model_with_description(self):
        """Test Gemini vision model detection using description metadata."""
        registry = ProviderRegistry()

        # Model with description containing "multimodal" → vision = True
        mock_model_multimodal = MagicMock()
        mock_model_multimodal.description = 'Stable version of Gemini 2.5 Flash, our mid-size multimodal model'
        mock_model_multimodal.supported_actions = ['generateContent', 'countTokens', 'createCachedContent']
        assert registry._is_gemini_vision_model('models/gemini-2.5-flash', model=mock_model_multimodal) is True

        # Model with "image" in description → vision = True
        mock_model_image = MagicMock()
        mock_model_image.description = 'Gemini 3 Pro Image Preview'
        mock_model_image.supported_actions = ['generateContent', 'countTokens']
        assert registry._is_gemini_vision_model('models/gemini-3-pro-image-preview', model=mock_model_image) is True

        # Model with no modality info in description → falls back to name pattern
        mock_model_sparse = MagicMock()
        mock_model_sparse.description = 'Stable release of Gemini 2.5 Pro'
        mock_model_sparse.supported_actions = ['generateContent', 'countTokens', 'createCachedContent']
        assert registry._is_gemini_vision_model('models/gemini-2.5-pro', model=mock_model_sparse) is True

        # Model without generateContent → excluded even if name matches
        mock_model_embed = MagicMock()
        mock_model_embed.description = 'Obtain a distributed representation of text'
        mock_model_embed.supported_actions = ['embedContent', 'countTokens']
        assert registry._is_gemini_vision_model('models/gemini-embedding-001', model=mock_model_embed) is False

        # TTS model with bidiGenerateContent but no createCachedContent → excluded
        mock_model_tts = MagicMock()
        mock_model_tts.description = 'Gemini 2.5 Flash Preview TTS'
        mock_model_tts.supported_actions = ['countTokens', 'generateContent']
        # Note: TTS is also caught by name pattern '-tts', but let's test with a non-TTS name
        # Actually, the supported_actions check for bidiGenerateContent applies when it's present
        # and createCachedContent is absent. This test covers that path.
        mock_model_tts_audio = MagicMock()
        mock_model_tts_audio.description = 'Latest release of Gemini 2.5 Flash Native Audio'
        mock_model_tts_audio.supported_actions = ['countTokens', 'bidiGenerateContent']
        assert registry._is_gemini_vision_model('models/gemini-2.5-flash-native-audio-latest', model=mock_model_tts_audio) is False

        # Model with None description and None supported_actions → name-pattern fallback
        mock_model_none = MagicMock()
        mock_model_none.description = None
        mock_model_none.supported_actions = None
        assert registry._is_gemini_vision_model('models/gemini-2.0-flash', model=mock_model_none) is True

        # Text-only description signal
        mock_model_text_only = MagicMock()
        mock_model_text_only.description = 'A text-only language model for classification tasks'
        mock_model_text_only.supported_actions = ['generateContent', 'countTokens']
        assert registry._is_gemini_vision_model('models/gemini-1.5-flash', model=mock_model_text_only) is False

    def test_is_openrouter_vision_model(self):
        """Test OpenRouter vision model detection."""
        registry = ProviderRegistry()

        # Models with input_modalities including image
        assert registry._is_openrouter_vision_model({
            'id': 'anthropic/claude-3.5-sonnet',
            'name': 'Claude 3.5 Sonnet',
            'architecture': {'input_modalities': ['text', 'image']}
        }) is True

        # Models with input_modalities alternative key
        assert registry._is_openrouter_vision_model({
            'id': 'google/gemini-pro',
            'name': 'Gemini Pro',
            'architecture': {'modalities': ['image', 'text']}
        }) is True

        # Models without modalities but with vision keywords
        assert registry._is_openrouter_vision_model({
            'id': 'gpt-4-vision-preview',
            'name': 'GPT-4 Vision Preview',
            'architecture': {}
        }) is True

        # Models without vision
        assert registry._is_openrouter_vision_model({
            'id': 'openai/gpt-4',
            'name': 'GPT-4',
            'architecture': {'input_modalities': ['text']}
        }) is False

    def test_is_ollama_vision_model(self):
        """Test Ollama vision model detection."""
        registry = ProviderRegistry()

        # Models with vision keywords in name
        assert registry._is_ollama_vision_model({
            'name': 'llava:latest',
            'details': {}
        }) is True

        assert registry._is_ollama_vision_model({
            'name': 'llava-v1.6-34b',
            'details': {}
        }) is True

        # Models with projector in details
        assert registry._is_ollama_vision_model({
            'name': 'custom-model',
            'details': {'projector_type': 'mlp'}
        }) is True

        # Models with clip in details
        assert registry._is_ollama_vision_model({
            'name': 'custom-model',
            'details': {'clip_model': 'ViT-B/32'}
        }) is True

        # Models without vision
        assert registry._is_ollama_vision_model({
            'name': 'llama3.2:latest',
            'details': {}
        }) is False


class TestVisionDetector:
    """Tests for VisionDetector."""

    def test_init(self):
        """Test detector initialization."""
        detector = VisionDetector()
        assert detector._registry is not None

    def test_init_with_registry(self):
        """Test detector initialization with custom registry."""
        registry = ProviderRegistry()
        detector = VisionDetector(registry=registry)
        assert detector._registry is registry

    def test_get_vision_models_gemini_no_api_key(self):
        """Test Gemini vision models without API key raises error."""
        detector = VisionDetector()
        with pytest.raises(ValueError, match="API key is required"):
            detector.get_vision_models('gemini')

    def test_get_vision_models_openrouter_no_api_key(self):
        """Test OpenRouter vision models without API key raises error."""
        detector = VisionDetector()
        with pytest.raises(ValueError, match="API key is required"):
            detector.get_vision_models('openrouter')

    def test_get_vision_models_unsupported_provider(self):
        """Test unsupported provider raises error."""
        detector = VisionDetector()
        with pytest.raises(ValueError, match="Unsupported provider"):
            detector.get_vision_models('unknown_provider')

    @patch.object(ProviderRegistry, 'fetch_gemini_models')
    def test_get_vision_models_gemini_success(self, mock_fetch):
        """Test successful Gemini vision model fetch."""
        mock_fetch.return_value = [
            {'id': 'gemini-1.5-pro', 'name': 'Gemini 1.5 Pro', 'provider': 'google', 'supports_vision': True},
            {'id': 'gemini-1.5-flash', 'name': 'Gemini 1.5 Flash', 'provider': 'google', 'supports_vision': True},
            {'id': 'text-only', 'name': 'Text Only', 'provider': 'google', 'supports_vision': False},
        ]

        detector = VisionDetector()
        models = detector.get_vision_models('gemini', api_key='test_key')

        assert len(models) == 2
        assert all(m['supports_vision'] for m in models)
        mock_fetch.assert_called_once_with('test_key')

    @patch.object(ProviderRegistry, 'fetch_openrouter_models')
    def test_get_vision_models_openrouter_success(self, mock_fetch):
        """Test successful OpenRouter vision model fetch."""
        mock_fetch.return_value = [
            {'id': 'claude-3.5-sonnet', 'name': 'Claude 3.5', 'provider': 'openrouter', 'supports_vision': True},
            {'id': 'gpt-4', 'name': 'GPT-4', 'provider': 'openrouter', 'supports_vision': False},
        ]

        detector = VisionDetector()
        models = detector.get_vision_models('openrouter', api_key='test_key')

        assert len(models) == 1
        assert models[0]['id'] == 'claude-3.5-sonnet'

    @patch.object(ProviderRegistry, 'fetch_ollama_models')
    def test_get_vision_models_ollama_success(self, mock_fetch):
        """Test successful Ollama vision model fetch."""
        mock_fetch.return_value = [
            {'id': 'llava:latest', 'name': 'LLaVA', 'provider': 'ollama', 'supports_vision': True},
            {'id': 'llama3.2', 'name': 'Llama 3.2', 'provider': 'ollama', 'supports_vision': False},
        ]

        detector = VisionDetector()
        models = detector.get_vision_models('ollama')

        assert len(models) == 1
        assert models[0]['id'] == 'llava:latest'

    @patch.object(ProviderRegistry, 'fetch_ollama_models')
    def test_get_vision_models_ollama_custom_url(self, mock_fetch):
        """Test Ollama vision model fetch with custom URL."""
        mock_fetch.return_value = []

        detector = VisionDetector()
        detector.get_vision_models('ollama', base_url='http://custom:8080')

        mock_fetch.assert_called_once_with('http://custom:8080')

    @patch.object(VisionDetector, 'get_vision_models')
    def test_get_all_vision_models(self, mock_get):
        """Test getting all vision models from multiple providers."""
        mock_get.side_effect = [
            [{'id': 'gemini-1.5-pro', 'supports_vision': True}],
            [{'id': 'claude-3.5', 'supports_vision': True}],
            [{'id': 'llava', 'supports_vision': True}],
        ]

        detector = VisionDetector()
        result = detector.get_all_vision_models(
            gemini_api_key='gemini_key',
            openrouter_api_key='openrouter_key',
            ollama_base_url='http://localhost:11434'
        )

        assert len(result) == 3
        assert 'gemini' in result
        assert 'openrouter' in result
        assert 'ollama' in result
        assert len(result['gemini']) == 1
        assert len(result['openrouter']) == 1
        assert len(result['ollama']) == 1

    @patch.object(VisionDetector, 'get_vision_models')
    def test_get_all_vision_models_partial_failure(self, mock_get):
        """Test getting all vision models with some failures."""
        mock_get.side_effect = [
            Exception("Gemini API error"),
            [{'id': 'claude-3.5', 'supports_vision': True}],
            [{'id': 'llava', 'supports_vision': True}],
        ]

        detector = VisionDetector()
        result = detector.get_all_vision_models(
            gemini_api_key='gemini_key',
            openrouter_api_key='openrouter_key',
            ollama_base_url='http://localhost:11434'
        )

        assert result['gemini'] == []
        assert len(result['openrouter']) == 1
        assert len(result['ollama']) == 1

    @patch.object(VisionDetector, 'get_vision_models')
    def test_is_model_vision_capable(self, mock_get):
        """Test checking if a specific model supports vision."""
        mock_get.return_value = [
            {'id': 'gemini-1.5-pro', 'supports_vision': True},
            {'id': 'gemini-1.5-flash', 'supports_vision': True},
        ]

        detector = VisionDetector()
        assert detector.is_model_vision_capable('gemini', 'gemini-1.5-pro', api_key='test') is True
        assert detector.is_model_vision_capable('gemini', 'text-only', api_key='test') is False

    @patch.object(VisionDetector, 'get_vision_models')
    def test_is_model_vision_capable_error(self, mock_get):
        """Test checking vision capability with error."""
        mock_get.side_effect = Exception("API error")

        detector = VisionDetector()
        assert detector.is_model_vision_capable('gemini', 'gemini-1.5-pro', api_key='test') is False

    @patch.object(ProviderRegistry, 'fetch_gemini_models')
    def test_get_model_by_id_found(self, mock_fetch):
        """Test getting model by ID when found."""
        mock_fetch.return_value = [
            {'id': 'gemini-1.5-pro', 'name': 'Gemini 1.5 Pro', 'provider': 'google', 'supports_vision': True},
        ]

        detector = VisionDetector()
        model = detector.get_model_by_id('gemini', 'gemini-1.5-pro', api_key='test')

        assert model is not None
        assert model['id'] == 'gemini-1.5-pro'

    @patch.object(ProviderRegistry, 'fetch_gemini_models')
    def test_get_model_by_id_not_found(self, mock_fetch):
        """Test getting model by ID when not found."""
        mock_fetch.return_value = [
            {'id': 'gemini-1.5-pro', 'name': 'Gemini 1.5 Pro', 'provider': 'google', 'supports_vision': True},
        ]

        detector = VisionDetector()
        model = detector.get_model_by_id('gemini', 'unknown-model', api_key='test')

        assert model is None

    def test_get_model_by_id_unsupported_provider(self):
        """Test getting model by ID with unsupported provider."""
        detector = VisionDetector()
        model = detector.get_model_by_id('unknown', 'model-id')

        assert model is None

    def test_clear_cache(self):
        """Test clearing cache."""
        detector = VisionDetector()
        detector._registry._cache = {'test': []}
        detector.clear_cache()
        assert detector._registry._cache == {}
