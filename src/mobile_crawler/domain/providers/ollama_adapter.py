"""Ollama AI model adapter."""

from typing import Any, Dict, Optional, Tuple

import ollama

from mobile_crawler.domain.model_adapters import ModelAdapter


class OllamaAdapter(ModelAdapter):
    """Adapter for local Ollama AI models."""

    def __init__(self):
        """Initialize Ollama adapter."""
        self._model_config: Dict[str, Any] = {}

    def initialize(self, model_config: Dict[str, Any], safety_settings: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Ollama client.

        Args:
            model_config: Configuration with optional 'model_name' and 'base_url'
            safety_settings: Optional safety settings (not applicable for local Ollama)
        """
        if 'base_url' in model_config:
            ollama.base_url = model_config['base_url']
        
        self._model_config = model_config

    def generate_response(self, prompt: str, image: Optional[bytes] = None) -> Tuple[str, Dict[str, Any]]:
        """Generate response from Ollama model.

        Args:
            prompt: Text prompt
            image: Optional image (not supported yet)

        Returns:
            Tuple of (response_text, metadata)

        Raises:
            NotImplementedError: If image is provided
        """
        if image is not None:
            raise NotImplementedError("Image support not implemented for Ollama")

        response = ollama.chat(
            model=self._model_config.get('model_name', 'llama3.2'),
            messages=[{'role': 'user', 'content': prompt}],
            options={'num_predict': 1000}  # Limit output length
        )

        text = response['message']['content']

        # Ollama typically doesn't provide token usage metadata
        metadata = {
            'token_usage': {
                'input_tokens': None,
                'output_tokens': None,
                'total_tokens': None
            }
        }

        return text, metadata

    @property
    def model_info(self) -> Dict[str, Any]:
        """Get model information.

        Returns:
            Dictionary with model details
        """
        return {
            'provider': 'ollama',
            'model': self._model_config.get('model_name', 'llama3.2'),
            'supports_vision': False,
            'is_local': True
        }