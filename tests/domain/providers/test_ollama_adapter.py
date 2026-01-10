"""Tests for Ollama adapter."""

from unittest.mock import Mock, patch
import pytest

from mobile_crawler.domain.providers.ollama_adapter import OllamaAdapter


class TestOllamaAdapter:
    def test_initialize(self):
        """Test initialization of Ollama adapter."""
        adapter = OllamaAdapter()
        
        model_config = {
            'model_name': 'llama3.2',
            'base_url': 'http://localhost:11434'
        }
        
        with patch('mobile_crawler.domain.providers.ollama_adapter.ollama') as mock_ollama:
            adapter.initialize(model_config)
            
            assert mock_ollama.base_url == 'http://localhost:11434'
            assert adapter._model_config == model_config

    def test_initialize_without_base_url(self):
        """Test initialization without base_url."""
        adapter = OllamaAdapter()
        
        model_config = {'model_name': 'llama3.2'}
        
        with patch('mobile_crawler.domain.providers.ollama_adapter.ollama') as mock_ollama:
            initial_base_url = getattr(mock_ollama, 'base_url', 'not_set')
            adapter.initialize(model_config)
            
            # base_url should not be changed
            assert mock_ollama.base_url == initial_base_url
            assert adapter._model_config == model_config

    def test_generate_response_success(self):
        """Test generating response successfully."""
        adapter = OllamaAdapter()
        adapter._model_config = {'model_name': 'llama3.2'}
        
        mock_response = {
            'message': {'content': 'Test response from Ollama'}
        }
        
        with patch('mobile_crawler.domain.providers.ollama_adapter.ollama.chat') as mock_chat:
            mock_chat.return_value = mock_response
            
            response, metadata = adapter.generate_response("Hello")
            
            assert response == "Test response from Ollama"
            assert metadata['token_usage']['input_tokens'] is None
            assert metadata['token_usage']['output_tokens'] is None
            assert metadata['token_usage']['total_tokens'] is None
            mock_chat.assert_called_once_with(
                model='llama3.2',
                messages=[{'role': 'user', 'content': 'Hello'}],
                options={'num_predict': 1000}
            )

    def test_generate_response_with_image_raises_error(self):
        """Test that providing image raises NotImplementedError."""
        adapter = OllamaAdapter()
        
        with pytest.raises(NotImplementedError, match="Image support not implemented"):
            adapter.generate_response("Describe image", b"fake image")

    def test_model_info(self):
        """Test model info property."""
        adapter = OllamaAdapter()
        adapter._model_config = {'model_name': 'codellama'}
        
        info = adapter.model_info
        
        assert info['provider'] == 'ollama'
        assert info['model'] == 'codellama'
        assert info['supports_vision'] is False
        assert info['is_local'] is True