"""OpenRouter AI model adapter."""

import requests
from typing import Any, Dict, Optional, Tuple

from mobile_crawler.domain.model_adapters import ModelAdapter


class OpenRouterAdapter(ModelAdapter):
    """Adapter for OpenRouter AI models."""

    def __init__(self):
        """Initialize OpenRouter adapter."""
        self._session: Optional[requests.Session] = None
        self._model_config: Dict[str, Any] = {}

    def initialize(self, model_config: Dict[str, Any], safety_settings: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the OpenRouter client.

        Args:
            model_config: Configuration with 'api_key' and optional 'model_name'
            safety_settings: Optional safety settings (not implemented)
        """
        self._session = requests.Session()
        self._session.headers.update({
            'Authorization': f'Bearer {model_config["api_key"]}',
            'Content-Type': 'application/json',
            'HTTP-Referer': model_config.get('referer', ''),  # Optional
            'X-Title': model_config.get('title', 'Mobile Crawler')  # Optional
        })
        self._model_config = model_config

    def generate_response(self, system_prompt: str, user_prompt: str) -> Tuple[str, Dict[str, Any]]:
        """Generate response from OpenRouter model.

        Args:
            system_prompt: System prompt text
            user_prompt: User prompt (may be JSON containing screenshot)

        Returns:
            Tuple of (response_text, metadata)
        """
        # Combine prompts for non-vision models
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        data = {
            'model': self._model_config.get('model_name', 'anthropic/claude-3-haiku'),
            'messages': [{'role': 'user', 'content': full_prompt}]
        }

        response = self._session.post('https://openrouter.ai/api/v1/chat/completions', json=data)
        response.raise_for_status()

        result = response.json()
        text = result['choices'][0]['message']['content']
        usage = result['usage']

        metadata = {
            'token_usage': {
                'input_tokens': usage['prompt_tokens'],
                'output_tokens': usage['completion_tokens'],
                'total_tokens': usage['total_tokens']
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
            'provider': 'openrouter',
            'model': self._model_config.get('model_name', 'anthropic/claude-3-haiku'),
            'supports_vision': False,
            'api_version': 'v1'
        }