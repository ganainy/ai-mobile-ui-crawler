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
                    'supports_vision': self._is_gemini_vision_model(model_id, model=model),
                }
                # Store description and supported_actions if available
                description = getattr(model, 'description', None)
                supported_actions = getattr(model, 'supported_actions', None)
                if description:
                    model_info['description'] = description
                if supported_actions:
                    model_info['supported_actions'] = supported_actions
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
                architecture = model.get('architecture', {})
                input_modalities = architecture.get('input_modalities', []) if isinstance(architecture, dict) else []
                pricing_raw = model.get('pricing', {})
                pricing = {}
                if isinstance(pricing_raw, dict):
                    try:
                        prompt_price = float(pricing_raw.get('prompt', 0))
                        completion_price = float(pricing_raw.get('completion', 0))
                        image_price = float(pricing_raw.get('image', 0))
                        pricing = {
                            'prompt_per_1M': f"{prompt_price * 1_000_000:.4f}",
                            'completion_per_1M': f"{completion_price * 1_000_000:.4f}",
                            'image_per_1M': f"{image_price * 1_000_000:.4f}",
                        }
                    except (ValueError, TypeError):
                        pricing = {
                            'prompt_per_1M': 'N/A',
                            'completion_per_1M': 'N/A',
                            'image_per_1M': 'N/A',
                        }

                model_info = {
                    'id': model['id'],
                    'name': model['name'],
                    'provider': 'openrouter',
                    'supports_vision': self._is_openrouter_vision_model(model),
                    'input_modalities': input_modalities,
                    'pricing': pricing,
                }
                result.append(model_info)

            self._cache[cache_key] = result
            self._save_persistent_cache()
            return result

        except Exception as e:
            logger.error(f"Failed to fetch OpenRouter models: {e}")
            # Return fallback list with known vision models
            return [
                {'id': 'anthropic/claude-3.5-sonnet', 'name': 'Claude 3.5 Sonnet', 'provider': 'openrouter', 'supports_vision': True, 'input_modalities': ['text', 'image'], 'pricing': {'prompt_per_1M': '3.0000', 'completion_per_1M': '15.0000', 'image_per_1M': '3.0000'}},
                {'id': 'anthropic/claude-3-opus', 'name': 'Claude 3 Opus', 'provider': 'openrouter', 'supports_vision': True, 'input_modalities': ['text', 'image'], 'pricing': {'prompt_per_1M': '15.0000', 'completion_per_1M': '75.0000', 'image_per_1M': '15.0000'}},
                {'id': 'anthropic/claude-3-haiku', 'name': 'Claude 3 Haiku', 'provider': 'openrouter', 'supports_vision': True, 'input_modalities': ['text', 'image'], 'pricing': {'prompt_per_1M': '0.2500', 'completion_per_1M': '1.2500', 'image_per_1M': '0.2500'}},
                {'id': 'google/gemini-pro-1.5', 'name': 'Gemini Pro 1.5', 'provider': 'openrouter', 'supports_vision': True, 'input_modalities': ['text', 'image'], 'pricing': {'prompt_per_1M': '1.2500', 'completion_per_1M': '5.0000', 'image_per_1M': '1.2500'}},
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

    def _is_gemini_vision_model(self, model_id: str, model: Any = None) -> bool:
        """Check if a Gemini model supports vision using hybrid detection.

        Uses a three-layer approach:
        1. API metadata (supported_actions) to filter non-content models
        2. Description-based detection for models with modality info
        3. Name-pattern fallback for models without description metadata

        Args:
            model_id: Model identifier (e.g., 'gemini-2.5-flash')
            model: Optional Gemini Model object with description and supported_actions

        Returns:
            True if model likely supports vision input
        """
        model_lower = model_id.lower()

        # Step 0: Exclude models that are clearly not vision-capable based on name
        # (These are never vision models regardless of other signals)
        always_text_only_patterns = [
            'text-',
            'embedding',
            'aqa',
            'tuning',
            'imagen',   # Image generation, not understanding
            'veo',      # Video generation
            'lyria',    # Audio generation
            'gemma',    # Text-only open models (small variants)
        ]
        if any(pattern in model_lower for pattern in always_text_only_patterns):
            return False

        # Step 1: Use API metadata (supported_actions) when available
        # Models must support 'generateContent' to be considered for vision.
        # This filters out embedding-only models (embedContent),
        # video generation (predictLongRunning), and image generation (predict).
        if model is not None:
            supported_actions = getattr(model, 'supported_actions', None) or []
            if isinstance(supported_actions, (list, tuple)) and len(supported_actions) > 0:
                if 'generateContent' not in supported_actions:
                    return False

                # Exclude TTS (text-to-speech) models - they have generateContent
                # but are for audio generation, not visual analysis
                if 'bidiGenerateContent' in supported_actions and 'createCachedContent' not in supported_actions:
                    return False

        # Step 2: Use description-based detection when available
        # The description field sometimes contains "multimodal", "image",
        # "vision", or "video" keywords that confirm vision capability.
        if model is not None:
            description = getattr(model, 'description', None)
            if description and isinstance(description, str) and len(description.strip()) > 0:
                desc_lower = description.lower()

                # Check for text-only signals in description
                text_only_desc_keywords = ['text-only', 'language model only', 'text generation only']
                if any(kw in desc_lower for kw in text_only_desc_keywords):
                    return False

                # Check for vision-capable signals in description
                vision_desc_keywords = ['multimodal', 'image', 'vision', 'video']
                if any(kw in desc_lower for kw in vision_desc_keywords):
                    return True

        # Step 3: Name-pattern fallback for models without modality info in description
        # Many Gemini models have sparse descriptions (e.g., "Gemini 2.0 Flash")
        # so we fall back to the model ID naming convention.
        #
        # Exclude TTS/audio models by name (these have generateContent but aren't for vision)
        tts_audio_patterns = ['-tts', '-native-audio', '-live']
        if any(pattern in model_lower for pattern in tts_audio_patterns):
            return False

        # Core Gemini models (1.x, 2.x, 3.x generations) all support vision
        vision_patterns = [
            'gemini-1.',
            'gemini-2.',
            'gemini-3',     # Matches gemini-3-pro-preview, gemini-3-flash-preview
            'gemini-pro',   # Matches gemini-pro, gemini-pro-vision
            'gemini-flash',
            'gemini-ultra',
            'gemini-exp',
        ]
        return any(pattern in model_lower for pattern in vision_patterns)

    def _is_openrouter_vision_model(self, model: Dict[str, Any]) -> bool:
        """Check if an OpenRouter model supports image input.

        Args:
            model: Model dictionary from OpenRouter API

        Returns:
            True if model supports image input
        """
        architecture = model.get('architecture', {})
        if isinstance(architecture, dict):
            input_modalities = architecture.get('input_modalities', [])
            if isinstance(input_modalities, list) and 'image' in input_modalities:
                return True

        # Fallback: check for vision-related keywords in model ID or name
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

        # Check legacy modals/modalities fields
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
