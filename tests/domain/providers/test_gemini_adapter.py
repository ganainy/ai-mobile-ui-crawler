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
        """Test generating response with text only."""
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
        
        response, metadata = adapter.generate_response("Hello")
        
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
        assert contents[0].parts[0].text == "Hello"

    def test_generate_response_with_image(self):
        """Test generating response with image."""
        adapter = GeminiAdapter()
        adapter._client = Mock()
        adapter._model_config = {}
        
        mock_response = Mock()
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock()]
        mock_response.candidates[0].content.parts[0].text = "Image response"
        mock_response.usage_metadata.prompt_token_count = 20
        mock_response.usage_metadata.candidates_token_count = 10
        mock_response.usage_metadata.total_token_count = 30
        adapter._client.models.generate_content.return_value = mock_response
        
        dummy_image_bytes = b"fake image data"
        response, metadata = adapter.generate_response("Describe image", dummy_image_bytes)
        
        assert response == "Image response"
        call_args = adapter._client.models.generate_content.call_args
        contents = call_args[1]['contents']
        assert len(contents) == 1
        assert len(contents[0].parts) == 2
        assert contents[0].parts[0].text == "Describe image"
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