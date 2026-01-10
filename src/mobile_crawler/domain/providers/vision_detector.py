"""Vision model detection and filtering."""

import logging
from typing import Any, Dict, List, Optional

from mobile_crawler.domain.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)


class VisionDetector:
    """Detects and filters vision-capable AI models."""

    def __init__(self, registry: Optional[ProviderRegistry] = None):
        """Initialize the vision detector.

        Args:
            registry: Optional ProviderRegistry instance (creates new if None)
        """
        self._registry = registry or ProviderRegistry()

    def get_vision_models(
        self,
        provider: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get vision-capable models for a provider.

        Args:
            provider: Provider name ('gemini', 'openrouter', 'ollama')
            api_key: API key for cloud providers (required for gemini, openrouter)
            base_url: Base URL for Ollama (defaults to localhost:11434)

        Returns:
            List of vision-capable model dictionaries

        Raises:
            ValueError: If provider is not supported or API key is missing
        """
        provider = provider.lower()

        if provider == 'gemini':
            if not api_key:
                raise ValueError("API key is required for Gemini provider")
            models = self._registry.fetch_gemini_models(api_key)

        elif provider == 'openrouter':
            if not api_key:
                raise ValueError("API key is required for OpenRouter provider")
            models = self._registry.fetch_openrouter_models(api_key)

        elif provider == 'ollama':
            models = self._registry.fetch_ollama_models(base_url or 'http://localhost:11434')

        else:
            raise ValueError(f"Unsupported provider: {provider}")

        # Filter to vision-capable models only
        vision_models = [m for m in models if m.get('supports_vision', False)]

        logger.info(f"Found {len(vision_models)} vision-capable models for {provider}")
        return vision_models

    def get_all_vision_models(
        self,
        gemini_api_key: Optional[str] = None,
        openrouter_api_key: Optional[str] = None,
        ollama_base_url: str = 'http://localhost:11434'
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get vision-capable models from all available providers.

        Args:
            gemini_api_key: Optional Gemini API key
            openrouter_api_key: Optional OpenRouter API key
            ollama_base_url: Base URL for Ollama

        Returns:
            Dictionary mapping provider names to lists of vision models
        """
        result = {}

        if gemini_api_key:
            try:
                result['gemini'] = self.get_vision_models('gemini', api_key=gemini_api_key)
            except Exception as e:
                logger.warning(f"Failed to fetch Gemini models: {e}")
                result['gemini'] = []

        if openrouter_api_key:
            try:
                result['openrouter'] = self.get_vision_models('openrouter', api_key=openrouter_api_key)
            except Exception as e:
                logger.warning(f"Failed to fetch OpenRouter models: {e}")
                result['openrouter'] = []

        try:
            result['ollama'] = self.get_vision_models('ollama', base_url=ollama_base_url)
        except Exception as e:
            logger.warning(f"Failed to fetch Ollama models: {e}")
            result['ollama'] = []

        return result

    def is_model_vision_capable(
        self,
        provider: str,
        model_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> bool:
        """Check if a specific model supports vision.

        Args:
            provider: Provider name
            model_id: Model identifier
            api_key: API key for cloud providers
            base_url: Base URL for Ollama

        Returns:
            True if model supports vision, False otherwise
        """
        try:
            models = self.get_vision_models(provider, api_key, base_url)
            return any(m['id'] == model_id for m in models)
        except Exception as e:
            logger.warning(f"Failed to check vision capability for {provider}/{model_id}: {e}")
            return False

    def get_model_by_id(
        self,
        provider: str,
        model_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get model information by ID.

        Args:
            provider: Provider name
            model_id: Model identifier
            api_key: API key for cloud providers
            base_url: Base URL for Ollama

        Returns:
            Model dictionary if found, None otherwise
        """
        try:
            if provider == 'gemini':
                if not api_key:
                    raise ValueError("API key is required for Gemini provider")
                models = self._registry.fetch_gemini_models(api_key)
            elif provider == 'openrouter':
                if not api_key:
                    raise ValueError("API key is required for OpenRouter provider")
                models = self._registry.fetch_openrouter_models(api_key)
            elif provider == 'ollama':
                models = self._registry.fetch_ollama_models(base_url or 'http://localhost:11434')
            else:
                return None

            for model in models:
                if model['id'] == model_id:
                    return model

            return None
        except Exception as e:
            logger.warning(f"Failed to get model {provider}/{model_id}: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear the model cache."""
        self._registry.clear_cache()
