"""Step phase state machine for managing individual crawl step lifecycle."""

import time
from collections.abc import Callable
from enum import Enum


class StepPhase(Enum):
    """Enumeration of phases a crawl step transitions through."""

    CAPTURE = "capture"
    DECIDE = "decide"
    EXECUTE = "execute"
    RECORD = "record"
    CHECKPOINT = "checkpoint"


# Valid transition map: each phase can only transition to its listed successor(s).
# CAPTURE can transition to DECIDE (normal flow) or CHECKPOINT (skip flow when
# context pre-check or UI dump validation fails).
VALID_TRANSITIONS = {
    StepPhase.CAPTURE: [StepPhase.DECIDE, StepPhase.CHECKPOINT],
    StepPhase.DECIDE: [StepPhase.EXECUTE],
    StepPhase.EXECUTE: [StepPhase.RECORD],
    StepPhase.RECORD: [StepPhase.CHECKPOINT],
    StepPhase.CHECKPOINT: [StepPhase.CAPTURE],
}


class StepPhaseStateMachine:
    """State machine for managing step phase transitions.

    Each crawl step transitions through CAPTURE -> DECIDE -> EXECUTE -> RECORD
    -> CHECKPOINT, then cycles back to CAPTURE for the next step. Listeners
    are notified on every transition and transition timestamps are recorded
    for timing analysis.
    """

    def __init__(self, initial_phase: StepPhase = StepPhase.CAPTURE):
        """Initialize state machine in the given phase.

        Args:
            initial_phase: The starting phase. Defaults to CAPTURE.
        """
        self.current_phase = initial_phase
        self._listeners: list[Callable[[StepPhase, StepPhase], None]] = []
        self._transition_times: dict[StepPhase, float] = {
            initial_phase: time.monotonic()
        }

    def add_listener(self, callback: Callable[[StepPhase, StepPhase], None]):
        """Add a listener for phase change events.

        Args:
            callback: Function called with (old_phase, new_phase) on transitions.
        """
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[StepPhase, StepPhase], None]):
        """Remove a phase change listener.

        Args:
            callback: The callback to remove.
        """
        if callback in self._listeners:
            self._listeners.remove(callback)

    def transition_to(self, new_phase: StepPhase):
        """Attempt to transition to a new phase.

        Args:
            new_phase: The target phase.

        Raises:
            ValueError: If the transition is invalid.
        """
        if not self._is_valid_transition(self.current_phase, new_phase):
            raise ValueError(
                f"Invalid transition from {self.current_phase.value} to {new_phase.value}"
            )

        old_phase = self.current_phase
        self._transition_times[new_phase] = time.monotonic()
        self.current_phase = new_phase
        self._notify_listeners(old_phase, new_phase)

    def _is_valid_transition(self, current: StepPhase, target: StepPhase) -> bool:
        """Check if a transition is valid.

        Args:
            current: Current phase.
            target: Target phase.

        Returns:
            True if transition is valid.
        """
        # Allow staying in the same phase (no-op transition)
        if current == target:
            return True

        return target in VALID_TRANSITIONS.get(current, [])

    def _notify_listeners(self, old_phase: StepPhase, new_phase: StepPhase):
        """Notify all listeners of phase change.

        Args:
            old_phase: Previous phase.
            new_phase: New phase.
        """
        for listener in self._listeners:
            try:
                listener(old_phase, new_phase)
            except Exception:
                # Don't let listener exceptions break the state machine
                pass

    def get_phase_duration(self, phase: StepPhase) -> float | None:
        """Return seconds spent in a phase based on transition timestamps.

        Duration is computed as the entry time of the *next* phase minus the
        entry time of the given phase. Returns None if the phase was never
        entered or if no subsequent transition has been recorded yet.

        Args:
            phase: The phase to query duration for.

        Returns:
            Duration in seconds, or None if not yet measurable.
        """
        if phase not in self._transition_times:
            return None

        phase_entry = self._transition_times[phase]

        # Find the next phase that was entered after this one
        next_entries = [
            t for t in self._transition_times.values() if t > phase_entry
        ]
        if not next_entries:
            return None

        return min(next_entries) - phase_entry
