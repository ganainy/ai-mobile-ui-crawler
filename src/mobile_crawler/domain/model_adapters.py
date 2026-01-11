"""Abstract base class for AI model adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple


class ModelAdapter(ABC):
    """Abstract base class for AI model adapters.

    Provides a common interface for different AI providers (Gemini, OpenRouter, Ollama, etc.).
    """

    @abstractmethod
    def initialize(self, model_config: Dict[str, Any], safety_settings: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the model adapter with configuration.

        Args:
            model_config: Configuration dictionary for the model
            safety_settings: Optional safety settings for the model
        """
        pass

    @abstractmethod
    def generate_response(self, system_prompt: str, user_prompt: str) -> Tuple[str, Dict[str, Any]]:
        """Generate a response from the AI model.

        Args:
            system_prompt: System prompt for the model
            user_prompt: User prompt (may be JSON containing screenshot)

        Returns:
            Tuple of (response_text, metadata_dict)
        """
        pass

    @property
    @abstractmethod
    def model_info(self) -> Dict[str, Any]:
        """Get information about the model.

        Returns:
            Dictionary with model information (name, version, capabilities, etc.)
        """
        pass