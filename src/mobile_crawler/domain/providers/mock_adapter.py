"""Mock AI provider for testing."""

from typing import Dict, Any, Tuple
import time

from mobile_crawler.domain.model_adapters import ModelAdapter


class MockAdapter(ModelAdapter):
    """Mock AI adapter that returns predetermined responses for testing."""

    def __init__(self):
        self.call_count = 0
        self.responses = [
            {
                "action": "click",
                "element_index": 0,
                "reasoning": "Clicking on the main menu button to explore the app"
            },
            {
                "action": "input",
                "element_index": 1,
                "text": "test input",
                "reasoning": "Entering test data into the input field"
            },
            {
                "action": "scroll_down",
                "reasoning": "Scrolling down to see more content"
            },
            {
                "action": "back",
                "reasoning": "Going back to previous screen"
            }
        ]

    def initialize(self, model_config: Dict[str, Any], safety_settings: Dict[str, Any]) -> None:
        """Initialize the mock adapter."""
        pass

    def generate_response(self, prompt: str, image_path: str = None) -> Tuple[str, Dict[str, Any]]:
        """Generate a mock response."""
        self.call_count += 1

        # Cycle through responses
        response_index = (self.call_count - 1) % len(self.responses)
        response = self.responses[response_index]

        # Simulate some processing time
        time.sleep(0.1)

        metadata = {
            "model": "mock-model",
            "tokens_used": 100,
            "call_count": self.call_count,
            "response_index": response_index
        }

        return str(response), metadata

    @property
    def model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "name": "mock-model",
            "provider": "mock",
            "supports_vision": True,
            "max_tokens": 1000
        }