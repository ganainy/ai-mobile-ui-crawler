"""Tests for AI interaction service."""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from mobile_crawler.domain.models import AIAction, AIResponse, BoundingBox
from mobile_crawler.infrastructure.ai_interaction_service import AIInteractionService


class TestAIInteractionService:
    """Test AIInteractionService."""

    def test_get_next_actions_success(self):
        """Test successful AI interaction."""
        # Setup mocks
        model_adapter = Mock()
        model_adapter.generate_response.return_value = (
            '{"actions": [{"action": "click", "action_desc": "Click button", "target_bounding_box": {"top_left": [100, 200], "bottom_right": [300, 250]}, "input_text": null, "reasoning": "Button visible"}], "signup_completed": false}',
            {"input_tokens": 100, "output_tokens": 50}
        )
        
        prompt_builder = Mock()
        prompt_builder.build_system_prompt.return_value = "System prompt"
        prompt_builder.build_user_prompt.return_value = '{"screenshot": "b64", "exploration_journal": [], "is_stuck": false, "stuck_reason": null, "available_actions": {"click": "Tap"}}'
        
        ai_repo = Mock()
        ai_repo.create_ai_interaction.return_value = 1
        
        config_manager = Mock()
        config_manager.get.return_value = 2  # max retries
        
        service = AIInteractionService(model_adapter, prompt_builder, ai_repo, config_manager)
        
        # Execute
        response = service.get_next_actions(1, 1, "screenshot_b64", "/path/to/screenshot.png")
        
        # Verify
        assert isinstance(response, AIResponse)
        assert len(response.actions) == 1
        assert response.actions[0].action == "click"
        assert response.signup_completed is False
        
        # Verify logging
        assert ai_repo.create_ai_interaction.called
        call_args = ai_repo.create_ai_interaction.call_args[0][0]
        assert call_args.success is True
        assert call_args.retry_count == 0

    def test_get_next_actions_retry_on_failure(self):
        """Test retry logic on AI failure."""
        # Setup mocks
        model_adapter = Mock()
        model_adapter.generate_response.side_effect = [
            Exception("API Error"),  # First call fails
            ('{"actions": [{"action": "click", "action_desc": "Click button", "target_bounding_box": {"top_left": [100, 200], "bottom_right": [300, 250]}, "input_text": null, "reasoning": "Button visible"}], "signup_completed": false}',
             {"input_tokens": 100, "output_tokens": 50})  # Second call succeeds
        ]
        
        prompt_builder = Mock()
        prompt_builder.build_system_prompt.return_value = "System prompt"
        prompt_builder.build_user_prompt.return_value = "User prompt"
        
        ai_repo = Mock()
        ai_repo.create_ai_interaction.return_value = 1
        
        config_manager = Mock()
        config_manager.get.return_value = 2  # max retries
        
        service = AIInteractionService(model_adapter, prompt_builder, ai_repo, config_manager)
        
        # Execute
        response = service.get_next_actions(1, 1, "screenshot_b64", None)
        
        # Verify
        assert model_adapter.generate_response.call_count == 2
        assert ai_repo.create_ai_interaction.call_count == 2  # One failure, one success
        
        # Check that one interaction was logged as failure
        failure_call = ai_repo.create_ai_interaction.call_args_list[0][0][0]
        assert failure_call.success is False
        assert failure_call.retry_count == 0
        
        # Check that final interaction was logged as success
        success_call = ai_repo.create_ai_interaction.call_args_list[1][0][0]
        assert success_call.success is True
        assert success_call.retry_count == 1

    def test_get_next_actions_all_retries_fail(self):
        """Test that exception is raised when all retries fail."""
        # Setup mocks
        model_adapter = Mock()
        model_adapter.generate_response.side_effect = Exception("Persistent API Error")
        
        prompt_builder = Mock()
        prompt_builder.build_system_prompt.return_value = "System prompt"
        prompt_builder.build_user_prompt.return_value = "User prompt"
        
        ai_repo = Mock()
        ai_repo.create_ai_interaction.return_value = 1
        
        config_manager = Mock()
        config_manager.get.return_value = 1  # max retries = 1
        
        service = AIInteractionService(model_adapter, prompt_builder, ai_repo, config_manager)
        
        # Execute and verify
        with pytest.raises(Exception, match="Persistent API Error"):
            service.get_next_actions(1, 1, "screenshot_b64", None)
        
        # Verify all retries attempted
        assert model_adapter.generate_response.call_count == 2  # Initial + 1 retry
        assert ai_repo.create_ai_interaction.call_count == 2

    def test_parse_ai_response_valid(self):
        """Test parsing valid AI response."""
        service = AIInteractionService(None, None, None, None)
        
        response_text = '''{
            "actions": [
                {
                    "action": "click",
                    "action_desc": "Click login button",
                    "target_bounding_box": {"top_left": [100, 200], "bottom_right": [300, 250]},
                    "input_text": null,
                    "reasoning": "Login button is visible"
                },
                {
                    "action": "input",
                    "action_desc": "Enter username",
                    "target_bounding_box": {"top_left": [50, 150], "bottom_right": [350, 200]},
                    "input_text": "testuser",
                    "reasoning": "Username field needs input"
                }
            ],
            "signup_completed": true
        }'''
        
        response = service._parse_ai_response(response_text)
        
        assert isinstance(response, AIResponse)
        assert len(response.actions) == 2
        assert response.signup_completed is True
        
        # Check first action
        action1 = response.actions[0]
        assert action1.action == "click"
        assert action1.input_text is None
        assert action1.target_bounding_box.top_left == (100, 200)
        assert action1.target_bounding_box.bottom_right == (300, 250)
        
        # Check second action
        action2 = response.actions[1]
        assert action2.action == "input"
        assert action2.input_text == "testuser"

    def test_parse_ai_response_invalid_json(self):
        """Test parsing invalid JSON response."""
        service = AIInteractionService(None, None, None, None)
        
        with pytest.raises(ValueError, match="Invalid JSON response"):
            service._parse_ai_response("invalid json")

    def test_parse_ai_response_missing_fields(self):
        """Test parsing response with missing required fields."""
        service = AIInteractionService(None, None, None, None)
        
        # Missing actions
        with pytest.raises(ValueError, match="missing 'actions' field"):
            service._parse_ai_response('{"signup_completed": false}')
        
        # Missing signup_completed
        with pytest.raises(ValueError, match="missing 'signup_completed' field"):
            service._parse_ai_response('{"actions": []}')

    def test_parse_ai_response_invalid_action_count(self):
        """Test parsing response with invalid action count."""
        service = AIInteractionService(None, None, None, None)
        
        # Too many actions - construct proper JSON
        actions = []
        for i in range(13):
            actions.append({
                "action": "click",
                "action_desc": "test",
                "target_bounding_box": {"top_left": [0, 0], "bottom_right": [10, 10]},
                "reasoning": "test"
            })
        
        response_data = {"actions": actions, "signup_completed": False}
        response_text = json.dumps(response_data)
        
        with pytest.raises(ValueError, match="not in range 1-12"):
            service._parse_ai_response(response_text)
        
        # Zero actions
        with pytest.raises(ValueError, match="not in range 1-12"):
            service._parse_ai_response('{"actions": [], "signup_completed": false}')

    def test_parse_ai_response_invalid_action(self):
        """Test parsing response with invalid action."""
        service = AIInteractionService(None, None, None, None)
        
        # Invalid action type
        response_text = '{"actions": [{"action": "invalid", "action_desc": "test", "target_bounding_box": {"top_left": [0,0], "bottom_right": [10,10]}, "reasoning": "test"}], "signup_completed": false}'
        with pytest.raises(ValueError, match="Invalid action type"):
            service._parse_ai_response(response_text)
        
        # Missing bounding box
        response_text = '{"actions": [{"action": "click", "action_desc": "test", "reasoning": "test"}], "signup_completed": false}'
        with pytest.raises(ValueError, match="missing required field"):
            service._parse_ai_response(response_text)
        
        # Input action without input_text
        response_text = '{"actions": [{"action": "input", "action_desc": "test", "target_bounding_box": {"top_left": [0,0], "bottom_right": [10,10]}, "reasoning": "test"}], "signup_completed": false}'
        with pytest.raises(ValueError, match="requires input_text"):
            service._parse_ai_response(response_text)
        
        # Non-input action with input_text
        response_text = '{"actions": [{"action": "click", "action_desc": "test", "target_bounding_box": {"top_left": [0,0], "bottom_right": [10,10]}, "input_text": "should not be here", "reasoning": "test"}], "signup_completed": false}'
        with pytest.raises(ValueError, match="Only input actions can have input_text"):
            service._parse_ai_response(response_text)