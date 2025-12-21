"""
Ollama provider strategy implementation.

This module contains all Ollama-specific logic including model fetching,
caching, vision detection, and metadata management.
"""

import json
import logging
import os
import subprocess
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from config.app_config import Config

from domain.providers.base import ProviderStrategy
from domain.providers.enums import AIProvider
from config.app_config import AI_PROVIDER_CAPABILITIES
from config.urls import ServiceURLs

logger = logging.getLogger(__name__)


class OllamaProvider(ProviderStrategy):
    """Provider strategy for Ollama."""
    
    def __init__(self):
        super().__init__(AIProvider.OLLAMA)
    
    @property
    def name(self) -> str:
        return "ollama"
    
    # ========== Cache Management ==========
    
    def _get_cache_path(self) -> str:
        """Determine the full path to the Ollama models cache file."""
        # Use the traverser_ai_api directory as the base
        traverser_ai_api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(traverser_ai_api_dir, "output_data", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file_path = os.path.join(cache_dir, "ollama_models.json")
        return cache_file_path
    
    def _load_models_cache(self) -> Optional[List[Dict[str, Any]]]:
        """Load and return the list of models from cache.
        
        Returns:
            List of model dicts if cache exists, None otherwise
        """
        try:
            cache_path = self._get_cache_path()
            if not os.path.exists(cache_path):
                return None
            
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # New schema: { schema_version, timestamp, models, index }
            if isinstance(data, dict) and data.get("schema_version") and isinstance(data.get("models"), list):
                models = data.get("models")
                return models if models else None
            
            return None
        except Exception as e:
            return None
    
    def _save_models_to_cache(self, models: List[Dict[str, Any]]) -> None:
        """Write normalized model list to cache with schema v1 and index mapping."""
        try:
            cache_path = self._get_cache_path()
            # Build index mapping for fast lookup
            index: Dict[str, int] = {}
            for i, m in enumerate(models):
                model_id = m.get("id") or m.get("name")
                if model_id:
                    index[str(model_id)] = i
            payload = {
                "schema_version": 1,
                "timestamp": int(time.time()),
                "models": models,
                "index": index,
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save Ollama cache: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
    
    # ========== Vision Detection ==========
    
    def _check_vision_via_sdk_metadata(self, model_name: str, base_url: Optional[str] = None) -> Optional[bool]:
        """Check vision support via Ollama SDK metadata inspection.
        
        Args:
            model_name: The model name to check
            base_url: Optional base URL for Ollama instance
            
        Returns:
            True if vision is detected, False if confirmed no vision, None if unable to determine
        """
        if not model_name:
            return None
        
        try:
            import ollama
        except ImportError:
            return None
        
        try:
            # Initialize client
            if base_url:
                client = ollama.Client(host=base_url)
            else:
                client = ollama.Client()
            
            try:
                # Use show() method to get model information
                if not hasattr(client, 'show'):
                    return None
                response = client.show(model_name)
                
                if response is None:
                    return None
                
                # Check if response contains vision indicators
                if hasattr(response, 'modelfile'):
                    modelfile = response.modelfile
                    if isinstance(modelfile, str):
                        modelfile_lower = modelfile.lower()
                        if any(indicator in modelfile_lower for indicator in ['projector', 'clip', 'vision', 'image']):
                            return True
                
                # Check response attributes for architecture info
                if hasattr(response, 'details'):
                    details = response.details
                    if isinstance(details, dict):
                        arch = details.get('architecture', '').lower()
                        family = details.get('family', '').lower()
                        if any(indicator in arch or indicator in family for indicator in ['clip', 'vision', 'multimodal']):
                            return True
                
                # Check for projector in any nested structure
                response_dict = response.__dict__ if hasattr(response, '__dict__') else {}
                response_str = str(response).lower()
                if 'projector' in response_str or 'clip' in response_str:
                    return True
                    
            except AttributeError:
                pass
            except Exception as e:
                pass
            
            return None
        except Exception as e:
            return None
    
    def _check_vision_via_cli(self, model_name: str, base_url: Optional[str] = None) -> Optional[bool]:
        """Check vision support via `ollama show` CLI command.
        
        Args:
            model_name: The model name to check
            base_url: Optional base URL for Ollama instance
            
        Returns:
            True if vision is detected, False if confirmed no vision, None if unable to determine
        """
        if not model_name:
            return None
        
        try:
            cmd = ['ollama', 'show', model_name]
            env = os.environ.copy()
            if base_url:
                env['OLLAMA_HOST'] = base_url
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                env=env,
            )
            
            if result.returncode != 0:
                return None
            
            output = result.stdout.lower()
            vision_indicators = [
                'projector',
                'clip',
                'vision encoder',
                'vision model',
                'multimodal',
                'image encoder',
            ]
            
            for indicator in vision_indicators:
                if indicator in output:
                    return True
            
            return None
            
        except subprocess.TimeoutExpired:
            return None
        except FileNotFoundError:
            return None
        except Exception as e:
            return None
    
    def _check_vision_via_patterns(self, model_name: str) -> bool:
        """Check vision support via name pattern matching (fallback method).
        
        Args:
            model_name: The model name to check
            
        Returns:
            True if the model name matches known vision patterns, False otherwise
        """
        if not model_name:
            return False
        
        base_name = model_name.split(':')[0].lower()
        vision_patterns = [
            "vision",
            "llava",
            "bakllava",
            "minicpm-v",
            "moondream",
            "gemma2",
            "gemma3",
            "qwen2.5vl",
            "qwen-vl",
            "llama3.2-vision",
            "llama3.1-vision",
            "llama3-vision",
            "mistral3",
            "vl",
        ]
        
        return any(pattern in base_name for pattern in vision_patterns)
    
    def _check_vision_via_cache(self, model_name: str) -> Optional[bool]:
        """Check vision support from cached model data (non-blocking).
        
        Args:
            model_name: The model name to check
            
        Returns:
            True/False if found in cache, None if not cached
        """
        if not model_name:
            return None
        
        try:
            cached_models = self._load_models_cache()
            if not cached_models:
                return None
            
            # Search for the model in cache
            for model in cached_models:
                model_id = model.get("id") or model.get("name", "")
                if model_id == model_name or model.get("name") == model_name:
                    # Return cached vision_supported if available
                    if "vision_supported" in model:
                        return bool(model["vision_supported"])
            
            return None
        except Exception:
            return None
    
    def is_model_vision(
        self,
        model_name: str,
        base_url: Optional[str] = None,
        use_cache: bool = True,
        use_metadata: bool = True,
        use_cli: bool = True,
        use_patterns: bool = True
    ) -> bool:
        """Determine if an Ollama model supports vision using hybrid detection.
        
        Uses a multi-tier approach (in order of preference):
        0. Cache lookup: Check cached model data (non-blocking, preferred for UI calls)
        1. Primary: Ollama SDK metadata inspection (blocking network call)
        2. Secondary: `ollama show` CLI command parsing (blocking subprocess)
        3. Fallback: Name pattern matching (non-blocking)
        
        For UI responsiveness, call with use_cache=True, use_metadata=False, use_cli=False
        to avoid blocking calls.
        
        Args:
            model_name: The model name to check
            base_url: Optional base URL for Ollama instance
            use_cache: Whether to check cached model data first (default: True)
            use_metadata: Whether to attempt SDK metadata inspection (default: True)
            use_cli: Whether to attempt CLI command inspection (default: True)
            use_patterns: Whether to use pattern matching as fallback (default: True)
            
        Returns:
            True if the model supports vision, False otherwise
        """
        if not model_name:
            return False
        
        # Tier 0: Check cache first (non-blocking)
        if use_cache:
            result = self._check_vision_via_cache(model_name)
            if result is not None:
                return result
        
        # Tier 1: Try SDK metadata inspection (BLOCKING - avoid in UI thread)
        if use_metadata:
            result = self._check_vision_via_sdk_metadata(model_name, base_url)
            if result is not None:
                return result
        
        # Tier 2: Try CLI command inspection (BLOCKING - avoid in UI thread)
        if use_cli:
            result = self._check_vision_via_cli(model_name, base_url)
            if result is not None:
                return result
        
        # Tier 3: Fallback to pattern matching (non-blocking)
        if use_patterns:
            result = self._check_vision_via_patterns(model_name)
            return result
        
        return False
    
    # ========== Model Normalization ==========
    
    def _normalize_model(self, model_info: Dict[str, Any], base_url: Optional[str] = None) -> Dict[str, Any]:
        """Normalize a single Ollama model for cache storage.
        
        Args:
            model_info: Raw model info from Ollama API (can be dict or object with attributes)
            base_url: Optional base URL for the Ollama instance
            
        Returns:
            Normalized model dictionary
        """
        # Handle both dict and object formats
        if hasattr(model_info, 'model'):
            model_name = model_info.model
            modified_at = getattr(model_info, 'modified_at', '')
            model_dict = {
                'model': model_name,
                'name': getattr(model_info, 'name', model_name),
                'size': getattr(model_info, 'size', 0),
                'digest': getattr(model_info, 'digest', ''),
                'modified_at': modified_at,
            }
        else:
            model_dict = model_info.copy()
            model_name = model_dict.get('model') or model_dict.get('name', '')
            modified_at = model_dict.get('modified_at', '')
        
        # Convert datetime to string if present
        if isinstance(modified_at, datetime):
            modified_at_str = modified_at.isoformat()
        elif modified_at:
            modified_at_str = str(modified_at)
        else:
            modified_at_str = ''
        
        # Extract base name for feature detection
        base_name = model_name.split(':')[0] if model_name else ''
        
        # Detect vision support using hybrid approach
        vision_supported = self.is_model_vision(model_name, base_url=base_url)
        
        # Build normalized model
        normalized = {
            "id": model_name,
            "name": model_name,
            "base_name": base_name,
            "description": f"Ollama model: {base_name}",
            "vision_supported": vision_supported,
            "size": model_dict.get('size', 0),
            "digest": model_dict.get('digest', ''),
            "modified_at": modified_at_str,
            "base_url": base_url or ServiceURLs.OLLAMA,
            "provider": "ollama",
            "online": False,  # Ollama models are always local
        }
        
        return normalized
    
    # ========== Model Fetching ==========
    
    def _fetch_models(self, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch installed models directly from Ollama.
        
        Args:
            base_url: Optional base URL for Ollama (defaults to localhost:11434)
            
        Returns:
            List of normalized model dictionaries
            
        Raises:
            ImportError: If ollama package is not installed
            RuntimeError: If Ollama service is not available
        """
        try:
            import ollama
        except ImportError:
            raise ImportError("Ollama Python package not installed. Run: pip install ollama")
        
        try:
            if base_url:
                client = ollama.Client(host=base_url)
            else:
                client = ollama.Client()

            # Fetch models from Ollama
            response = client.list()
            
            # Handle different response formats
            models_list = []
            if hasattr(response, 'models'):
                models_list = response.models
            elif isinstance(response, dict) and 'models' in response:
                models_list = response['models']
            elif isinstance(response, list):
                models_list = response
            else:
                logger.warning(f"Unexpected Ollama response format: {type(response)}")
                return []
            
            if not models_list:
                return []
            
            # Normalize all models
            normalized_models = []
            for model_info in models_list:
                try:
                    normalized = self._normalize_model(model_info, base_url)
                    normalized_models.append(normalized)
                except Exception as e:
                    logger.warning(f"Failed to normalize model {model_info}: {e}")
                    continue
            
            return normalized_models
            
        except ConnectionError as e:
            error_msg = str(e)
            raise RuntimeError(error_msg) from None
        except Exception as e:
            error_msg = f"Failed to fetch Ollama models: {e}"
            raise RuntimeError(error_msg) from None
    
    # ========== ProviderStrategy Interface ==========
    
    def get_models(self, config: 'Config') -> List[str]:
        """Get available Ollama models."""
        models = []
        base_url = self.get_api_key(config, ServiceURLs.OLLAMA)
        
        try:
            fetched_models = self._fetch_models(base_url)
            if fetched_models:
                for model in fetched_models:
                    model_name = model.get("name") or model.get("id", "")
                    if model_name:
                        models.append(model_name)
        except Exception:
            pass
        
        # Fallback to cache
        if not models:
            try:
                cached_models = self._load_models_cache()
                if cached_models:
                    for model in cached_models:
                        model_name = model.get("name") or model.get("id", "")
                        if model_name:
                            models.append(model_name)
            except Exception:
                pass
        
        return models
    
    def get_api_key_name(self) -> str:
        return "OLLAMA_BASE_URL"
    
    def validate_config(self, config: 'Config') -> Tuple[bool, Optional[str]]:
        """Validate Ollama configuration."""
        # Ollama doesn't require API key, base URL is optional
        return True, None
    
    def get_api_key(self, config: 'Config', default_url: Optional[str] = None) -> Optional[str]:
        """Get Ollama base URL from config."""
        base_url = config.get("OLLAMA_BASE_URL")
        if not base_url and default_url:
            return default_url
        return base_url or DEFAULT_OLLAMA_URL
    
    def check_dependencies(self) -> Tuple[bool, str]:
        """Check if Ollama SDK is installed."""
        try:
            import ollama
            return True, ""
        except ImportError:
            return False, "Ollama Python SDK not installed. Run: pip install ollama"
    
    def supports_image_context(self, config: 'Config', model_name: Optional[str] = None) -> bool:
        """Check if Ollama model supports image context.
        
        Uses non-blocking detection (cache + pattern matching) for UI responsiveness.
        Blocking network calls are avoided to prevent UI freezes.
        """
        if model_name:
            base_url = self.get_api_key(config)
            # Disable blocking calls (use_metadata=False, use_cli=False) for UI responsiveness
            # Uses cache lookup and pattern matching only
            return self.is_model_vision(
                model_name, 
                base_url=base_url,
                use_cache=True,
                use_metadata=False,  # Disable blocking SDK call
                use_cli=False,       # Disable blocking CLI call
                use_patterns=True
            )
        return True  # Default to True for vision-capable models
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get Ollama provider capabilities."""
        return AI_PROVIDER_CAPABILITIES.get("ollama", {})
    
    # ========== Extended API for Services ==========
    
    def get_models_full(self, config: 'Config', refresh: bool = False) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """Get full model metadata (not just IDs).
        
        Args:
            config: Configuration object
            refresh: If True, refresh the cache before listing
            
        Returns:
            Tuple of (success, models_list) where models_list contains full model dicts
        """
        # If refresh requested, fetch fresh models
        if refresh:
            try:
                base_url = self.get_api_key(config, ServiceURLs.OLLAMA)
                models = self._fetch_models(base_url)
                if models:
                    self._save_models_to_cache(models)
                    return True, models if models else []
            except Exception as e:
                logger.error(f"Failed to refresh Ollama models: {e}")
                # Fall back to cache
                pass
        
        # Try to load from cache first
        models = self._load_models_cache()
        
        # If no cache, try to fetch fresh
        if not models:
            try:
                base_url = self.get_api_key(config, ServiceURLs.OLLAMA)
                models = self._fetch_models(base_url)
                if models:
                    self._save_models_to_cache(models)
            except Exception as e:
                logger.error(f"Failed to fetch Ollama models: {e}")
                return False, None
        
        if not models:
            return False, None
        
        return True, models
    
    def get_model_meta(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Lookup a model's metadata by id from the cache.
        
        Args:
            model_id: The model ID to look up
            
        Returns:
            Model metadata dict if found, None otherwise
        """
        try:
            cache_path = self._get_cache_path()
            if not os.path.exists(cache_path):
                return None
            
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, dict) and data.get("schema_version") and isinstance(data.get("models"), list):
                index = data.get("index") or {}
                models = data.get("models") or []
                i = index.get(str(model_id))
                if isinstance(i, int) and 0 <= i < len(models):
                    return models[i]
                # Fallback linear search
                for m in models:
                    if str(m.get("id")) == str(model_id) or str(m.get("name")) == str(model_id):
                        return m
                return None
            
            return None
        except Exception as e:
            return None
    
    def refresh_models(self, config: 'Config', wait_for_completion: bool = False) -> Tuple[bool, Optional[str]]:
        """Refresh Ollama models cache.
        
        Args:
            config: Configuration object
            wait_for_completion: If True, wait for the refresh to complete before returning
            
        Returns:
            Tuple of (success, cache_path) where cache_path is the path to the saved cache file
        """
        def refresh_logic():
            base_url = self.get_api_key(config, ServiceURLs.OLLAMA)
            models = self._fetch_models(base_url)
            
            if not models:
                logger.warning("No Ollama models found during refresh")
                return None
            
            cache_path = self._get_cache_path()
            self._save_models_to_cache(models)
            return cache_path

        if wait_for_completion:
            try:
                cache_path = refresh_logic()
                return True, cache_path
            except Exception as e:
                logger.error(f"Failed to refresh Ollama models synchronously: {e}", exc_info=True)
                raise
        else:
            def background_worker():
                try:
                    refresh_logic()
                except Exception as e:
                    logger.error(f"Background refresh for Ollama failed: {e}", exc_info=True)

            thread = threading.Thread(target=background_worker, daemon=True)
            thread.start()
            return True, None
