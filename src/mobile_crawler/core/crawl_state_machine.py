"""Crawl state machine for managing crawler lifecycle."""

from enum import Enum
from typing import Callable, List


class CrawlState(Enum):
    """Enumeration of possible crawler states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED_MANUAL = "paused_manual"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class CrawlStateMachine:
    """State machine for managing crawler state transitions."""

    def __init__(self):
        """Initialize state machine in UNINITIALIZED state."""
        self.state = CrawlState.UNINITIALIZED
        self._listeners: List[Callable[[CrawlState, CrawlState], None]] = []

    def add_listener(self, callback: Callable[[CrawlState, CrawlState], None]):
        """Add a listener for state change events.
        
        Args:
            callback: Function called with (old_state, new_state) on transitions
        """
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[CrawlState, CrawlState], None]):
        """Remove a state change listener.
        
        Args:
            callback: The callback to remove
        """
        if callback in self._listeners:
            self._listeners.remove(callback)

    def transition_to(self, new_state: CrawlState):
        """Attempt to transition to a new state.
        
        Args:
            new_state: The target state
            
        Raises:
            ValueError: If the transition is invalid
        """
        if not self._is_valid_transition(self.state, new_state):
            raise ValueError(f"Invalid transition from {self.state.value} to {new_state.value}")
        
        old_state = self.state
        self.state = new_state
        self._notify_listeners(old_state, new_state)

    def _is_valid_transition(self, current: CrawlState, target: CrawlState) -> bool:
        """Check if a transition is valid.
        
        Args:
            current: Current state
            target: Target state
            
        Returns:
            True if transition is valid
        """
        # Allow staying in the same state (no-op transition)
        if current == target:
            return True
            
        valid_transitions = {
            CrawlState.UNINITIALIZED: [CrawlState.INITIALIZING, CrawlState.ERROR],
            CrawlState.INITIALIZING: [CrawlState.RUNNING, CrawlState.ERROR],
            CrawlState.RUNNING: [CrawlState.PAUSED_MANUAL, CrawlState.STOPPING, CrawlState.ERROR],
            CrawlState.PAUSED_MANUAL: [CrawlState.RUNNING, CrawlState.STOPPING, CrawlState.ERROR],
            CrawlState.STOPPING: [CrawlState.STOPPED, CrawlState.ERROR],
            CrawlState.STOPPED: set(),  # Terminal state
            CrawlState.ERROR: set()     # Terminal state
        }
        
        return target in valid_transitions.get(current, [])

    def _notify_listeners(self, old_state: CrawlState, new_state: CrawlState):
        """Notify all listeners of state change.
        
        Args:
            old_state: Previous state
            new_state: New state
        """
        for listener in self._listeners:
            try:
                listener(old_state, new_state)
            except Exception:
                # Don't let listener exceptions break the state machine
                pass