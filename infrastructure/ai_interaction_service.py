"""
AI Interaction Service - Dedicated handling of AI input/output for UI display.

This service is SEPARATE from general logging to ensure stability.
Changes to logging code will not affect the AI Interaction Inspector.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class AIInteraction:
    """Represents a single AI interaction (prompt + response)."""
    step: int
    timestamp: datetime
    prompt: str  # The input prompt sent to AI
    response: str = ""  # The AI response (filled in later)
    screenshot_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def label(self) -> str:
        """Generate a display label for this interaction."""
        time_str = self.timestamp.strftime("%H:%M:%S")
        return f"#{self.step} ({time_str})"


class AIInteractionService:
    """
    Manages AI interaction history separately from general logging.
    
    This service provides:
    - Recording of AI prompts and responses
    - History management with callbacks for UI updates
    - Clean separation from logging code
    """
    
    def __init__(self):
        self._interactions: List[AIInteraction] = []
        self._step_counter = 0
        
        # Callbacks for UI updates (set by UI controller)
        self._on_new_interaction: Optional[Callable[[AIInteraction], None]] = None
        self._on_response_received: Optional[Callable[[int, str], None]] = None
    
    def set_callbacks(
        self,
        on_new_interaction: Optional[Callable[[AIInteraction], None]] = None,
        on_response_received: Optional[Callable[[int, str], None]] = None
    ):
        """Set callbacks for UI updates."""
        self._on_new_interaction = on_new_interaction
        self._on_response_received = on_response_received
    
    def record_prompt(
        self,
        prompt: str,
        screenshot_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Record a new AI prompt.
        
        Args:
            prompt: The prompt text sent to AI
            screenshot_path: Optional path to screenshot for this interaction
            metadata: Optional additional metadata
            
        Returns:
            The step number of this interaction
        """
        self._step_counter += 1
        
        interaction = AIInteraction(
            step=self._step_counter,
            timestamp=datetime.now(),
            prompt=prompt,
            screenshot_path=screenshot_path,
            metadata=metadata or {}
        )
        
        self._interactions.append(interaction)
        
        # Notify UI
        if self._on_new_interaction:
            try:
                self._on_new_interaction(interaction)
            except Exception as e:
                logger.error(f"Error in new interaction callback: {e}")
        
        return self._step_counter
    
    def record_response(self, step: int, response: str):
        """
        Record the AI response for a given step.
        
        Args:
            step: The step number to update
            response: The AI response text
        """
        # Find the interaction
        for interaction in self._interactions:
            if interaction.step == step:
                interaction.response = response
                
                # Notify UI
                if self._on_response_received:
                    try:
                        self._on_response_received(step, response)
                    except Exception as e:
                        logger.error(f"Error in response callback: {e}")
                return
        
        logger.warning(f"No interaction found for step {step}")
    
    def record_response_for_latest(self, response: str):
        """Record response for the most recent interaction."""
        if self._interactions:
            self.record_response(self._interactions[-1].step, response)
    
    def get_interaction(self, step: int) -> Optional[AIInteraction]:
        """Get an interaction by step number."""
        for interaction in self._interactions:
            if interaction.step == step:
                return interaction
        return None
    
    def get_latest(self) -> Optional[AIInteraction]:
        """Get the most recent interaction."""
        return self._interactions[-1] if self._interactions else None
    
    def get_all(self) -> List[AIInteraction]:
        """Get all interactions."""
        return self._interactions.copy()
    
    def clear(self):
        """Clear all interactions."""
        self._interactions.clear()
        self._step_counter = 0
    
    @property
    def count(self) -> int:
        """Number of recorded interactions."""
        return len(self._interactions)


# Singleton instance
_instance: Optional[AIInteractionService] = None


def get_ai_interaction_service() -> AIInteractionService:
    """Get the singleton AIInteractionService instance."""
    global _instance
    if _instance is None:
        _instance = AIInteractionService()
    return _instance
