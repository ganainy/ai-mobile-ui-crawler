"""Provider registry for fetching and managing AI models."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


# Cache expiration time (7 days)
CACHE_EXPIRATION_DAYS = 7


class ProviderRegistry:
    """Registry for fetching available models from AI providers."""

    def __init__(self, config_store=None):
        """Initialize the provider registry.

        Args:
            config_store: Optional UserConfigStore for persistent caching.
                         If provided, models will be cached to disk with expiration.
        """
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
        self._config_store = config_store

        # Load cached models from persistent storage if available
        if self._config_store:
            self._load_persistent_cache()

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
            found_ids = set()
            
            for model in models:
                model_id = model.name
                # Strip models/ prefix if present
                if model_id.startswith('models/'):
                    model_id = model_id.replace('models/', '')
                    
                model_info = {
                    'id': model_id,
                    'name': model.display_name or model_id,
                    'provider': 'google',
                    'supports_vision': self._is_gemini_vision_model(model_id)
                }
                result.append(model_info)
                found_ids.add(model_id)

            # Manually ensure Gemini 3 preview models are present if not returned
            gemini_3_models = [
                {'id': 'gemini-3-pro-preview', 'name': 'Gemini 3 Pro (Preview)'},
                {'id': 'gemini-3-flash-preview', 'name': 'Gemini 3 Flash (Preview)'},
            ]

            for g3 in gemini_3_models:
                if g3['id'] not in found_ids:
                    # Check if model supports vision (it does)
                    if self._is_gemini_vision_model(g3['id']):
                         result.append({
                            'id': g3['id'],
                            'name': g3['name'],
                            'provider': 'google',
                            'supports_vision': True
                        })

            self._cache[cache_key] = result
            self._save_persistent_cache()
            return result

        except Exception as e:
            logger.error(f"Failed to fetch Gemini models: {e}")
            raise RuntimeError(f"Failed to fetch Gemini models from API. Please check your API key and internet connection: {e}") from e

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
            self._save_persistent_cache()
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
            self._save_persistent_cache()
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
            'gemini-3', # Changed from gemini-3. to gemini-3 to match gemini-3-pro-preview
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

    def clear_cache(self, provider: Optional[str] = None) -> None:
        """Clear the model cache.

        Args:
            provider: Optional provider name to clear. If None, clears all.
        """
        if provider:
            self._cache.pop(provider, None)
        else:
            self._cache.clear()

        # Also clear persistent cache
        if self._config_store:
            try:
                self._config_store.delete_setting("model_cache")
                logger.info("Cleared persistent model cache")
            except Exception as e:
                logger.warning(f"Failed to clear persistent cache: {e}")

    def _load_persistent_cache(self) -> None:
        """Load cached models from persistent storage if available and not expired."""
        if not self._config_store:
            return

        try:
            cache_data = self._config_store.get_setting("model_cache", default=None)
            if not cache_data:
                return

            cached_at_str = cache_data.get("cached_at")
            if not cached_at_str:
                return

            # Parse cache timestamp
            try:
                cached_at = datetime.fromisoformat(cached_at_str)
            except (ValueError, AttributeError):
                logger.warning("Invalid cache timestamp, ignoring persistent cache")
                return

            # Check if cache is expired
            cache_age = datetime.now(timezone.utc) - cached_at
            if cache_age > timedelta(days=CACHE_EXPIRATION_DAYS):
                logger.info(f"Model cache expired ({cache_age.days} days old), ignoring")
                return

            # Load cached models into memory
            models_by_provider = cache_data.get("models", {})
            for provider, models in models_by_provider.items():
                if models:  # Only cache non-empty lists
                    self._cache[provider] = models
                    logger.info(f"Loaded {len(models)} cached models for {provider}")

        except Exception as e:
            logger.warning(f"Failed to load persistent cache: {e}")

    def _save_persistent_cache(self) -> None:
        """Save current in-memory cache to persistent storage."""
        if not self._config_store:
            return

        try:
            cache_data = {
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "models": self._cache
            }
            self._config_store.set_setting("model_cache", cache_data, "json")
            logger.debug(f"Saved {len(self._cache)} provider caches to persistent storage")
        except Exception as e:
            logger.warning(f"Failed to save persistent cache: {e}")
