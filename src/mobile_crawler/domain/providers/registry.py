"""Provider registry for fetching and managing AI models."""

import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for fetching available models from AI providers."""

    def __init__(self):
        """Initialize the provider registry."""
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

    def clear_cache(self, provider: Optional[str] = None) -> None:
        """Clear the model cache.

        Args:
            provider: Optional provider name to clear. If None, clears all.
        """
        if provider:
            self._cache.pop(provider, None)
        else:
            self._cache.clear()

    def fetch_gemini_models(self, api_key: str) -> List[Dict[str, Any]]:
        """Fetch available Gemini models.

        Args:
            api_key: Google API key

        Returns:
            List of model dictionaries with 'id' and 'name' keys
        """
        cache_key = 'gemini'
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            import google.genai as genai

            client = genai.Client(api_key=api_key)
            models = client.models.list()

            result = []
            for model in models:
                model_info = {
                    'id': model.name,
                    'name': model.display_name or model.name,
                    'provider': 'google',
                    'supports_vision': self._is_gemini_vision_model(model.name)
                }
                result.append(model_info)

            self._cache[cache_key] = result
            return result

        except Exception as e:
            logger.error(f"Failed to fetch Gemini models: {e}")
            # Return fallback list with known vision models
            return [
                {'id': 'gemini-1.5-pro', 'name': 'Gemini 1.5 Pro', 'provider': 'google', 'supports_vision': True},
                {'id': 'gemini-1.5-flash', 'name': 'Gemini 1.5 Flash', 'provider': 'google', 'supports_vision': True},
                {'id': 'gemini-1.0-pro', 'name': 'Gemini 1.0 Pro', 'provider': 'google', 'supports_vision': True},
            ]

    def fetch_openrouter_models(self, api_key: str) -> List[Dict[str, Any]]:
        """Fetch available OpenRouter models.

        Args:
            api_key: OpenRouter API key

        Returns:
            List of model dictionaries with 'id', 'name', and 'supports_vision' keys
        """
        cache_key = 'openrouter'
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            response = requests.get(
                'https://openrouter.ai/api/v1/models',
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            result = []

            for model in data.get('data', []):
                model_info = {
                    'id': model['id'],
                    'name': model['name'],
                    'provider': 'openrouter',
                    'supports_vision': self._is_openrouter_vision_model(model)
                }
                result.append(model_info)

            self._cache[cache_key] = result
            return result

        except Exception as e:
            logger.error(f"Failed to fetch OpenRouter models: {e}")
            # Return fallback list with known vision models
            return [
                {'id': 'anthropic/claude-3.5-sonnet', 'name': 'Claude 3.5 Sonnet', 'provider': 'openrouter', 'supports_vision': True},
                {'id': 'anthropic/claude-3-opus', 'name': 'Claude 3 Opus', 'provider': 'openrouter', 'supports_vision': True},
                {'id': 'anthropic/claude-3-haiku', 'name': 'Claude 3 Haiku', 'provider': 'openrouter', 'supports_vision': True},
                {'id': 'google/gemini-pro-1.5', 'name': 'Gemini Pro 1.5', 'provider': 'openrouter', 'supports_vision': True},
            ]

    def fetch_ollama_models(self, base_url: str = 'http://localhost:11434') -> List[Dict[str, Any]]:
        """Fetch available Ollama models.

        Args:
            base_url: Ollama API base URL

        Returns:
            List of model dictionaries with 'id', 'name', and 'supports_vision' keys
        """
        cache_key = f'ollama_{base_url}'
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            response = requests.get(f'{base_url}/api/tags', timeout=5)
            response.raise_for_status()

            data = response.json()
            result = []

            for model in data.get('models', []):
                model_name = model['name']
                model_info = {
                    'id': model_name,
                    'name': model_name,
                    'provider': 'ollama',
                    'supports_vision': self._is_ollama_vision_model(model)
                }
                result.append(model_info)

            self._cache[cache_key] = result
            return result

        except Exception as e:
            logger.error(f"Failed to fetch Ollama models: {e}")
            # Return empty list - no reliable fallback for local models
            return []

    def _is_gemini_vision_model(self, model_id: str) -> bool:
        """Check if a Gemini model supports vision.

        Args:
            model_id: Model identifier

        Returns:
            True if model supports vision
        """
        model_lower = model_id.lower()
        
        # Exclude text-only models explicitly
        text_only_patterns = [
            'text-',
            'embedding',
            'aqa',
            'tuning',
        ]
        if any(pattern in model_lower for pattern in text_only_patterns):
            return False
        
        # All Gemini 1.x, 2.x, 3.x and Pro models support vision
        vision_patterns = [
            'gemini-1.',
            'gemini-2.',
            'gemini-3.',
            'gemini-pro',
            'gemini-flash',
            'gemini-ultra',
            'gemini-exp',
        ]
        return any(pattern in model_lower for pattern in vision_patterns)

    def _is_openrouter_vision_model(self, model: Dict[str, Any]) -> bool:
        """Check if an OpenRouter model supports vision.

        Args:
            model: Model dictionary from OpenRouter API

        Returns:
            True if model supports vision
        """
        # Check for vision-related keywords in model ID or name first
        model_id = model.get('id', '').lower()
        model_name = model.get('name', '').lower()

        vision_keywords = [
            'claude-3',
            'gpt-4-vision',
            'gpt-4o',
            'gemini',
            'llava',
            'vision',
            'multimodal',
        ]

        if any(keyword in model_id or keyword in model_name for keyword in vision_keywords):
            return True

        # Check modalities in architecture
        architecture = model.get('architecture', {})
        if isinstance(architecture, dict):
            modalities = architecture.get('modals', architecture.get('modalities', []))
            if isinstance(modalities, list):
                return 'text+image' in modalities or 'image' in modalities

        return False

    def _is_ollama_vision_model(self, model: Dict[str, Any]) -> bool:
        """Check if an Ollama model supports vision.

        Args:
            model: Model dictionary from Ollama API

        Returns:
            True if model supports vision
        """
        model_name = model.get('name', '').lower()
        details = model.get('details', {})

        # Check for vision-related keywords in model name
        vision_keywords = [
            'llava',
            'clip',
            'vision',
            'projector',
            'multimodal',
        ]

        # Check model name
        if any(keyword in model_name for keyword in vision_keywords):
            return True

        # Check details for projector or clip
        if isinstance(details, dict):
            if 'projector_type' in details or 'clip' in str(details).lower():
                return True

        return False

    def clear_cache(self) -> None:
        """Clear the model cache."""
        self._cache.clear()
