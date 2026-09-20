"""Tests for step phase state machine."""

import time
from unittest.mock import patch

import pytest

from mobile_crawler.domain.step_phase import StepPhase, StepPhaseStateMachine


class TestStepPhase:
    """Test StepPhase enum."""

    def test_enum_values(self):
        """Test that all expected phases exist with correct values."""
        expected_phases = ["capture", "decide", "execute", "record", "checkpoint"]
        actual_phases = [phase.value for phase in StepPhase]
        assert set(actual_phases) == set(expected_phases)
        assert len(actual_phases) == 5


class TestStepPhaseStateMachine:
    """Test StepPhaseStateMachine."""

    def test_initial_state(self):
        """Test initial phase is CAPTURE."""
        machine = StepPhaseStateMachine()
        assert machine.current_phase == StepPhase.CAPTURE

    def test_custom_initial_state(self):
        """Test initializing with a different phase."""
        machine = StepPhaseStateMachine(initial_phase=StepPhase.EXECUTE)
        assert machine.current_phase == StepPhase.EXECUTE

    def test_valid_full_cycle(self):
        """Test full valid cycle: CAPTURE -> DECIDE -> EXECUTE -> RECORD -> CHECKPOINT -> CAPTURE."""
        machine = StepPhaseStateMachine()

        machine.transition_to(StepPhase.DECIDE)
        assert machine.current_phase == StepPhase.DECIDE

        machine.transition_to(StepPhase.EXECUTE)
        assert machine.current_phase == StepPhase.EXECUTE

        machine.transition_to(StepPhase.RECORD)
        assert machine.current_phase == StepPhase.RECORD

        machine.transition_to(StepPhase.CHECKPOINT)
        assert machine.current_phase == StepPhase.CHECKPOINT

        machine.transition_to(StepPhase.CAPTURE)
        assert machine.current_phase == StepPhase.CAPTURE

    def test_invalid_transition_capture_to_execute(self):
        """Test CAPTURE -> EXECUTE raises ValueError."""
        machine = StepPhaseStateMachine()
        with pytest.raises(ValueError, match="Invalid transition"):
            machine.transition_to(StepPhase.EXECUTE)

    def test_invalid_transition_capture_to_record(self):
        """Test CAPTURE -> RECORD raises ValueError."""
        machine = StepPhaseStateMachine()
        with pytest.raises(ValueError, match="Invalid transition"):
            machine.transition_to(StepPhase.RECORD)

    def test_same_phase_noop(self):
        """Test same-phase transition is a no-op and does not raise."""
        machine = StepPhaseStateMachine()
        # Should not raise
        machine.transition_to(StepPhase.CAPTURE)
        assert machine.current_phase == StepPhase.CAPTURE

    def test_listener_receives_events(self):
        """Test listener receives (old_phase, new_phase) tuple on each transition."""
        machine = StepPhaseStateMachine()

        events = []

        def listener(old_phase, new_phase):
            events.append((old_phase, new_phase))

        machine.add_listener(listener)

        machine.transition_to(StepPhase.DECIDE)
        machine.transition_to(StepPhase.EXECUTE)

        expected_events = [
            (StepPhase.CAPTURE, StepPhase.DECIDE),
            (StepPhase.DECIDE, StepPhase.EXECUTE),
        ]
        assert events == expected_events

    def test_listener_exception_does_not_prevent_transition(self):
        """Test listener exception does not prevent transition from completing."""
        machine = StepPhaseStateMachine()

        def bad_listener(old_phase, new_phase):
            raise Exception("Listener failed")

        good_called = False

        def good_listener(old_phase, new_phase):
            nonlocal good_called
            good_called = True

        machine.add_listener(bad_listener)
        machine.add_listener(good_listener)

        # Should not raise
        machine.transition_to(StepPhase.DECIDE)

        assert machine.current_phase == StepPhase.DECIDE
        assert good_called

    def test_remove_listener(self):
        """Test remove_listener stops the listener from receiving further events."""
        machine = StepPhaseStateMachine()

        events = []

        def listener(old_phase, new_phase):
            events.append((old_phase, new_phase))

        machine.add_listener(listener)
        machine.transition_to(StepPhase.DECIDE)
        assert len(events) == 1

        machine.remove_listener(listener)
        machine.transition_to(StepPhase.EXECUTE)
        assert len(events) == 1  # No new event after removal

    def test_transition_timestamps_recorded(self):
        """Test transition timestamps are recorded via time.monotonic() in _transition_times dict."""
        machine = StepPhaseStateMachine()

        # Initial phase should have a timestamp (set in __init__)
        assert StepPhase.CAPTURE in machine._transition_times
        assert isinstance(machine._transition_times[StepPhase.CAPTURE], float)

        before = time.monotonic()
        machine.transition_to(StepPhase.DECIDE)
        after = time.monotonic()

        assert StepPhase.DECIDE in machine._transition_times
        ts = machine._transition_times[StepPhase.DECIDE]
        assert before <= ts <= after

    def test_get_phase_duration(self):
        """Test get_phase_duration returns seconds spent in a phase."""
        machine = StepPhaseStateMachine()

        # Before any transition, duration for CAPTURE is None (no subsequent transition)
        assert machine.get_phase_duration(StepPhase.CAPTURE) is None

        machine.transition_to(StepPhase.DECIDE)
        # Now CAPTURE should have a duration
        cap_duration = machine.get_phase_duration(StepPhase.CAPTURE)
        assert cap_duration is not None
        assert cap_duration >= 0

        # DECIDE has no duration yet (still in it)
        assert machine.get_phase_duration(StepPhase.DECIDE) is None

        machine.transition_to(StepPhase.EXECUTE)
        decide_duration = machine.get_phase_duration(StepPhase.DECIDE)
        assert decide_duration is not None
        assert decide_duration >= 0

    def test_get_phase_duration_phase_not_entered(self):
        """Test get_phase_duration returns None for phase never entered."""
        machine = StepPhaseStateMachine()
        # CHECKPOINT was never entered
        assert machine.get_phase_duration(StepPhase.CHECKPOINT) is None


class TestPhaseDurationAcrossSteps:
    """A phase re-entered on later steps must not report negative durations."""

    def test_second_step_durations_are_positive_and_measured_per_visit(self):
        clock = iter([0.0, 1.0, 1.5, 4.0, 4.1, 4.2, 10.0, 10.5, 12.0, 12.1, 12.2])
        with patch("mobile_crawler.domain.step_phase.time.monotonic", side_effect=lambda: next(clock)):
            machine = StepPhaseStateMachine()  # CAPTURE entered at 0.0
            seen = []
            machine.add_listener(lambda old, new: seen.append((old, machine.get_phase_duration(old))))
            for phase in (
                StepPhase.DECIDE,  # 1.0
                StepPhase.EXECUTE,  # 1.5
                StepPhase.RECORD,  # 4.0
                StepPhase.CHECKPOINT,  # 4.1
                StepPhase.CAPTURE,  # 4.2  (step 2 begins)
                StepPhase.DECIDE,  # 10.0
                StepPhase.EXECUTE,  # 10.5
                StepPhase.RECORD,  # 12.0
                StepPhase.CHECKPOINT,  # 12.1
            ):
                machine.transition_to(phase)

        durations = {}
        for old, duration in seen:
            durations.setdefault(old, []).append(duration)
        assert durations[StepPhase.CAPTURE] == [pytest.approx(1.0), pytest.approx(5.8)]
        assert durations[StepPhase.DECIDE] == [pytest.approx(0.5), pytest.approx(0.5)]
        assert all(d >= 0 for values in durations.values() for d in values)

    def test_phase_with_no_later_transition_has_no_duration(self):
        machine = StepPhaseStateMachine()
        machine.transition_to(StepPhase.DECIDE)
        assert machine.get_phase_duration(StepPhase.DECIDE) is None
        assert machine.get_phase_duration(StepPhase.RECORD) is None
