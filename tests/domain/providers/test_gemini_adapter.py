"""Tests for Gemini adapter."""

from unittest.mock import Mock, patch
import pytest

from mobile_crawler.domain.providers.gemini_adapter import GeminiAdapter


class TestGeminiAdapter:
    def test_initialize(self):
        """Test initialization of Gemini adapter."""
        adapter = GeminiAdapter()
        
        model_config = {
            'api_key': 'test_key',
            'model_name': 'gemini-1.5-pro'
        }
        
        with patch('mobile_crawler.domain.providers.gemini_adapter.genai') as mock_genai:
            adapter.initialize(model_config)
            
            mock_genai.Client.assert_called_once_with(api_key='test_key')
            assert adapter._model_config == model_config

    def test_generate_response_text_only(self):
        """Test generating response with text only (no screenshot in user prompt)."""
        adapter = GeminiAdapter()
        adapter._client = Mock()
        adapter._model_config = {'model_name': 'gemini-1.5-flash'}
        
        mock_response = Mock()
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock()]
        mock_response.candidates[0].content.parts[0].text = "Test response"
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 5
        mock_response.usage_metadata.total_token_count = 15
        adapter._client.models.generate_content.return_value = mock_response
        
        # Call with system_prompt and user_prompt (no screenshot)
        response, metadata = adapter.generate_response("System prompt", "User prompt")
        
        assert response == "Test response"
        assert metadata['token_usage']['input_tokens'] == 10
        assert metadata['token_usage']['output_tokens'] == 5
        assert metadata['token_usage']['total_tokens'] == 15
        adapter._client.models.generate_content.assert_called_once()
        call_args = adapter._client.models.generate_content.call_args
        assert call_args[1]['model'] == 'gemini-1.5-flash'
        contents = call_args[1]['contents']
        assert len(contents) == 1
        assert len(contents[0].parts) == 1
        # Full prompt should combine system and user prompts
        assert "System prompt" in contents[0].parts[0].text
        assert "User prompt" in contents[0].parts[0].text

    def test_generate_response_with_image(self):
        """Test generating response with image in user prompt JSON."""
        import base64
        import json
        
        adapter = GeminiAdapter()
        adapter._client = Mock()
        adapter._model_config = {'model': 'gemini-2.0-flash'}
        
        mock_response = Mock()
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock()]
        mock_response.candidates[0].content.parts[0].text = "Image response"
        mock_response.usage_metadata.prompt_token_count = 20
        mock_response.usage_metadata.candidates_token_count = 10
        mock_response.usage_metadata.total_token_count = 30
        adapter._client.models.generate_content.return_value = mock_response
        
        # Create user_prompt JSON with base64 screenshot
        dummy_image_bytes = b"fake image data"
        screenshot_b64 = base64.b64encode(dummy_image_bytes).decode()
        user_prompt = json.dumps({"screenshot": screenshot_b64, "other_data": "test"})
        
        response, metadata = adapter.generate_response("Describe image", user_prompt)
        
        assert response == "Image response"
        call_args = adapter._client.models.generate_content.call_args
        contents = call_args[1]['contents']
        assert len(contents) == 1
        assert len(contents[0].parts) == 2
        # Check text part contains both prompts
        assert "Describe image" in contents[0].parts[0].text
        # Check image part
        image_part = contents[0].parts[1]
        assert image_part.inline_data.data == dummy_image_bytes
        assert image_part.inline_data.mime_type == 'image/png'

    def test_model_info(self):
        """Test model info property."""
        adapter = GeminiAdapter()
        adapter._model_config = {'model_name': 'gemini-1.5-pro'}
        
        info = adapter.model_info
        
        assert info['provider'] == 'google'
        assert info['model'] == 'gemini-1.5-pro'
        assert info['supports_vision'] is True
        assert info['api_version'] == 'genai'