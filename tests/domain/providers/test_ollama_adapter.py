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
            
            response, metadata = adapter.generate_response("System prompt", "User prompt")
            
            assert response == "Test response from Ollama"
            assert metadata['token_usage']['input_tokens'] is None
            assert metadata['token_usage']['output_tokens'] is None
            assert metadata['token_usage']['total_tokens'] is None
            mock_chat.assert_called_once()
            call_args = mock_chat.call_args
            content = call_args[1]['messages'][0]['content']
            assert 'System prompt' in content
            assert 'User prompt' in content

    def test_generate_response_combines_prompts(self):
        """Test that system and user prompts are combined."""
        adapter = OllamaAdapter()
        adapter._model_config = {'model_name': 'llama3.2'}
        
        mock_response = {'message': {'content': 'Test'}}
        
        with patch('mobile_crawler.domain.providers.ollama_adapter.ollama.chat') as mock_chat:
            mock_chat.return_value = mock_response
            
            adapter.generate_response("Be helpful", "{\"screenshot\": \"abc\"}")
            
            call_args = mock_chat.call_args
            content = call_args[1]['messages'][0]['content']
            assert 'Be helpful' in content
            assert 'screenshot' in content

    def test_model_info(self):
        """Test model info property."""
        adapter = OllamaAdapter()
        adapter._model_config = {'model_name': 'codellama'}
        
        info = adapter.model_info
        
        assert info['provider'] == 'ollama'
        assert info['model'] == 'codellama'
        assert info['supports_vision'] is False
        assert info['is_local'] is True