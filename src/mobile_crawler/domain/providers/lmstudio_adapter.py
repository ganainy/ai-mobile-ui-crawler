"""LMStudio local AI model adapter."""

import requests
from typing import Any, Dict, Optional, Tuple

from mobile_crawler.domain.model_adapters import ModelAdapter


class LmstudioAdapter(ModelAdapter):
    """Adapter for local LMStudio AI models."""

    def __init__(self):
        """Initialize LMStudio adapter."""
        self._session: Optional[requests.Session] = None
        self._model_config: Dict[str, Any] = {}

    def initialize(self, model_config: Dict[str, Any], safety_settings: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the LMStudio client.

        Args:
            model_config: Configuration with optional 'model_name' and 'base_url'
            safety_settings: Optional safety settings (not implemented)
        """
        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json'
        })
        self._model_config = model_config

    def generate_response(self, system_prompt: str, user_prompt: str) -> Tuple[str, Dict[str, Any]]:
        """Generate response from LMStudio model.

        Args:
            system_prompt: System prompt text
            user_prompt: User prompt (may be JSON containing screenshot)

        Returns:
            Tuple of (response_text, metadata)
        """
        import json
        
        base_url = self._model_config.get('base_url', 'http://localhost:1234/v1')
        
        # Check if the user prompt is JSON containing a screenshot
        try:
            prompt_data = json.loads(user_prompt)
            if isinstance(prompt_data, dict) and 'screenshot' in prompt_data:
                # Build multimodal message
                screenshot_b64 = prompt_data.pop('screenshot')
                
                # Format the text part with remaining JSON data
                text_content = json.dumps(prompt_data, indent=2)
                
                messages = [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': [
                        {'type': 'text', 'text': text_content},
                        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{screenshot_b64}'}}
                    ]}
                ]
            else:
                # Regular JSON prompt without screenshot
                messages = [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ]
        except json.JSONDecodeError:
            # Not JSON, send as regular text
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]

        data = {
            'model': self._model_config.get('model_name', 'local-model'),
            'messages': messages,
            'temperature': self._model_config.get('temperature', 0.1)
        }

        # Local LLMs can be slow, remove timeouts or set very high
        response = self._session.post(f'{base_url}/chat/completions', json=data, timeout=120)
        
        if response.status_code != 200:
            raise Exception(f"LMStudio API error ({response.status_code}): {response.text}")

        result = response.json()
        text = result['choices'][0]['message']['content']
        usage = result.get('usage', {})

        metadata = {
            'token_usage': {
                'input_tokens': usage.get('prompt_tokens'),
                'output_tokens': usage.get('completion_tokens'),
                'total_tokens': usage.get('total_tokens')
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
            'provider': 'lmstudio',
            'model': self._model_config.get('model_name', 'local-model'),
            'supports_vision': False,
            'is_local': True
        }
