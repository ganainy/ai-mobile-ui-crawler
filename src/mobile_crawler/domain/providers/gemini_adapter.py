"""Gemini AI model adapter."""

import base64
import io
import json
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

    def generate_response(self, system_prompt: str, user_prompt: str) -> Tuple[str, Dict[str, Any]]:
        """Generate response from Gemini model.

        Args:
            system_prompt: System prompt text
            user_prompt: User prompt as JSON string (may contain base64 screenshot)

        Returns:
            Tuple of (response_text, metadata)
        """
        # Extract screenshot from user_prompt JSON if present
        image_bytes = None
        try:
            user_data = json.loads(user_prompt)
            if isinstance(user_data, dict) and 'screenshot' in user_data:
                screenshot_b64 = user_data['screenshot']
                if screenshot_b64:
                    image_bytes = base64.b64decode(screenshot_b64)
        except (json.JSONDecodeError, ValueError):
            # user_prompt is not JSON or doesn't contain screenshot
            pass
        
        # Combine system prompt and user prompt
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        parts = [genai.types.Part(text=full_prompt)]
        
        if image_bytes:
            # Add image part
            parts.append(genai.types.Part(inline_data=genai.types.Blob(data=image_bytes, mime_type='image/png')))
        
        content = genai.types.Content(parts=parts)
        
        model = self._model_config.get('model') or self._model_config.get('model_name')
        if not model:
            raise ValueError("No model specified in configuration")
        
        response = self._client.models.generate_content(
            model=model,
            contents=[content]
        )
        
        # Check for valid response
        if not response.candidates:
            raise ValueError("No candidates in Gemini response")
        
        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            # Check for safety filter or other issues
            if hasattr(candidate, 'finish_reason'):
                raise ValueError(f"Gemini response blocked or empty. Finish reason: {candidate.finish_reason}")
            raise ValueError("Empty content in Gemini response")
        
        text = candidate.content.parts[0].text
        if not text:
            raise ValueError("Empty text in Gemini response")
        
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
            'model': self._model_config.get('model') or self._model_config.get('model_name'),
            'supports_vision': True,
            'api_version': 'genai'
        }