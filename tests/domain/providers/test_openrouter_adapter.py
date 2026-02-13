"""Tests for OpenRouter adapter."""

from unittest.mock import Mock, patch
import pytest

from mobile_crawler.domain.providers.openrouter_adapter import OpenRouterAdapter


class TestOpenRouterAdapter:
    def test_initialize(self):
        """Test initialization of OpenRouter adapter."""
        adapter = OpenRouterAdapter()
        
        model_config = {
            'api_key': 'test_key',
            'model_name': 'anthropic/claude-3-haiku',
            'referer': 'http://example.com',
            'title': 'Test App'
        }
        
        with patch('mobile_crawler.domain.providers.openrouter_adapter.requests.Session') as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            
            adapter.initialize(model_config)
            
            mock_session.assert_called_once()
            mock_session_instance.headers.update.assert_called_once_with({
                'Authorization': 'Bearer test_key',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'http://example.com',
                'X-Title': 'Test App'
            })
            assert adapter._model_config == model_config

    def test_generate_response_success(self):
        """Test generating response successfully."""
        adapter = OpenRouterAdapter()
        adapter._session = Mock()
        adapter._model_config = {'model_name': 'anthropic/claude-3-haiku'}
        
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Test response'}}],
            'usage': {
                'prompt_tokens': 10,
                'completion_tokens': 5,
                'total_tokens': 15
            }
        }
        mock_response.raise_for_status.return_value = None
        adapter._session.post.return_value = mock_response
        
        response, metadata = adapter.generate_response("System prompt", "User prompt")
        
        assert response == "Test response"
        assert metadata['token_usage']['input_tokens'] == 10
        assert metadata['token_usage']['output_tokens'] == 5
        assert metadata['token_usage']['total_tokens'] == 15
        adapter._session.post.assert_called_once()
        call_args = adapter._session.post.call_args
        assert 'System prompt' in call_args[1]['json']['messages'][0]['content']
        assert 'User prompt' in call_args[1]['json']['messages'][0]['content']

    def test_generate_response_combines_prompts(self):
        """Test that system and user prompts are combined."""
        adapter = OpenRouterAdapter()
        adapter._session = Mock()
        adapter._model_config = {'model_name': 'anthropic/claude-3-haiku'}
        
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Test'}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}
        }
        mock_response.raise_for_status.return_value = None
        adapter._session.post.return_value = mock_response
        
        adapter.generate_response("Be helpful", "{\"screenshot\": \"abc\"}")
        
        call_args = adapter._session.post.call_args
        content = call_args[1]['json']['messages'][0]['content']
        assert 'Be helpful' in content
        assert 'screenshot' in content

    def test_model_info(self):
        """Test model info property."""
        adapter = OpenRouterAdapter()
        adapter._model_config = {'model_name': 'openai/gpt-4'}
        
        info = adapter.model_info
        
        assert info['provider'] == 'openrouter'
        assert info['model'] == 'openai/gpt-4'
        assert info['supports_vision'] is False
        assert info['api_version'] == 'v1'