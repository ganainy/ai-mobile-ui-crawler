"""Gemini AI model adapter."""

import io
from typing import Any, Dict, Optional, Tuple

from PIL import Image
import google.genai as genai

from mobile_crawler.domain.model_adapters import ModelAdapter


class GeminiAdapter(ModelAdapter):
    """Adapter for Google Gemini AI models."""

    def __init__(self):
        """Initialize Gemini adapter."""
        self._client: Optional[genai.Client] = None
        self._model_config: Dict[str, Any] = {}

    def initialize(self, model_config: Dict[str, Any], safety_settings: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Gemini client.

        Args:
            model_config: Configuration with 'api_key' and optional 'model_name'
            safety_settings: Optional safety settings (not implemented yet)
        """
        self._client = genai.Client(api_key=model_config['api_key'])
        self._model_config = model_config

    def generate_response(self, prompt: str, image: Optional[bytes] = None) -> Tuple[str, Dict[str, Any]]:
        """Generate response from Gemini model.

        Args:
            prompt: Text prompt
            image: Optional image as bytes

        Returns:
            Tuple of (response_text, metadata)
        """
        parts = [genai.types.Part(text=prompt)]
        
        if image:
            # Add image part
            parts.append(genai.types.Part(inline_data=genai.types.Blob(data=image, mime_type='image/png')))
        
        content = genai.types.Content(parts=parts)
        
        response = self._client.models.generate_content(
            model=self._model_config.get('model_name', 'gemini-1.5-flash'),
            contents=[content]
        )
        
        text = response.candidates[0].content.parts[0].text
        
        metadata = {
            'token_usage': {
                'input_tokens': response.usage_metadata.prompt_token_count,
                'output_tokens': response.usage_metadata.candidates_token_count,
                'total_tokens': response.usage_metadata.total_token_count
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
            'provider': 'google',
            'model': self._model_config.get('model_name', 'gemini-1.5-flash'),
            'supports_vision': True,
            'api_version': 'genai'
        }