"""Mock AI provider for testing."""

from typing import Dict, Any, Tuple
import time
import json

from mobile_crawler.domain.model_adapters import ModelAdapter


class MockAdapter(ModelAdapter):
    """Mock AI adapter that returns predetermined responses for testing."""

    def __init__(self):
        self.call_count = 0
        # Pre-defined responses in the expected AI response format
        # Fields: action, action_desc, target_bounding_box, input_text (optional), reasoning
        self._mock_actions = [
            {
                "action": "click",
                "action_desc": "Click on main menu button",
                "target_bounding_box": {"top_left": [100, 200], "bottom_right": [200, 250]},
                "reasoning": "Clicking on the main menu button to explore the app"
            },
            {
                "action": "input",
                "action_desc": "Enter text in input field",
                "target_bounding_box": {"top_left": [50, 300], "bottom_right": [350, 350]},
                "input_text": "test input",
                "reasoning": "Entering test data into the input field"
            },
            {
                "action": "scroll_down",
                "action_desc": "Scroll down on screen",
                "target_bounding_box": {"top_left": [200, 400], "bottom_right": [600, 800]},
                "reasoning": "Scrolling down to see more content"
            },
            {
                "action": "back",
                "action_desc": "Navigate back",
                "target_bounding_box": {"top_left": [0, 0], "bottom_right": [100, 100]},
                "reasoning": "Going back to previous screen"
            }
        ]

    def initialize(self, model_config: Dict[str, Any], safety_settings: Dict[str, Any]) -> None:
        """Initialize the mock adapter."""
        pass

    def generate_response(self, system_prompt: str, user_prompt: str) -> Tuple[str, Dict[str, Any]]:
        """Generate a mock response in the expected AI response format."""
        self.call_count += 1

        # Cycle through mock actions
        action_index = (self.call_count - 1) % len(self._mock_actions)
        action = self._mock_actions[action_index]

        # Build response in the expected format
        response = {
            "actions": [action],
            "signup_completed": self.call_count >= 100  # Complete after 100 steps
        }

        # Simulate some processing time
        time.sleep(0.5)

        metadata = {
            "model": "mock-model",
            "tokens_used": 100,
            "call_count": self.call_count,
            "action_index": action_index
        }

        # Return properly formatted JSON string
        return json.dumps(response), metadata

    @property
    def model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "name": "mock-model",
            "provider": "mock",
            "supports_vision": True,
            "max_tokens": 1000
        }