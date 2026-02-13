"""Tests for crawl state machine."""

import pytest

from mobile_crawler.core.crawl_state_machine import CrawlState, CrawlStateMachine


class TestCrawlState:
    """Test CrawlState enum."""
    
    def test_enum_values(self):
        """Test that all expected states exist."""
        expected_states = [
            "uninitialized", "initializing", "running", "paused_manual", 
            "stopping", "stopped", "error"
        ]
        
        actual_states = [state.value for state in CrawlState]
        assert set(actual_states) == set(expected_states)


class TestCrawlStateMachine:
    """Test CrawlStateMachine."""
    
    def test_initial_state(self):
        """Test initial state is UNINITIALIZED."""
        machine = CrawlStateMachine()
        assert machine.state == CrawlState.UNINITIALIZED

    def test_valid_transitions(self):
        """Test all valid state transitions."""
        machine = CrawlStateMachine()
        
        # UNINITIALIZED -> INITIALIZING
        machine.transition_to(CrawlState.INITIALIZING)
        assert machine.state == CrawlState.INITIALIZING
        
        # INITIALIZING -> RUNNING
        machine.transition_to(CrawlState.RUNNING)
        assert machine.state == CrawlState.RUNNING
        
        # RUNNING -> PAUSED_MANUAL
        machine.transition_to(CrawlState.PAUSED_MANUAL)
        assert machine.state == CrawlState.PAUSED_MANUAL
        
        # PAUSED_MANUAL -> RUNNING
        machine.transition_to(CrawlState.RUNNING)
        assert machine.state == CrawlState.RUNNING
        
        # RUNNING -> STOPPING
        machine.transition_to(CrawlState.STOPPING)
        assert machine.state == CrawlState.STOPPING
        
        # STOPPING -> STOPPED
        machine.transition_to(CrawlState.STOPPED)
        assert machine.state == CrawlState.STOPPED

    def test_invalid_transitions(self):
        """Test that invalid transitions raise ValueError."""
        machine = CrawlStateMachine()
        
        # Try invalid transition from UNINITIALIZED
        with pytest.raises(ValueError, match="Invalid transition"):
            machine.transition_to(CrawlState.RUNNING)
        
        # Valid transition first
        machine.transition_to(CrawlState.INITIALIZING)
        
        # Try invalid from INITIALIZING
        with pytest.raises(ValueError, match="Invalid transition"):
            machine.transition_to(CrawlState.STOPPED)

    def test_terminal_states(self):
        """Test that terminal states don't allow further transitions."""
        machine = CrawlStateMachine()
        
        # Go to STOPPED
        machine.transition_to(CrawlState.INITIALIZING)
        machine.transition_to(CrawlState.RUNNING)
        machine.transition_to(CrawlState.STOPPING)
        machine.transition_to(CrawlState.STOPPED)
        
        # Try to transition from STOPPED
        with pytest.raises(ValueError, match="Invalid transition"):
            machine.transition_to(CrawlState.RUNNING)
        
        # Go to ERROR
        machine2 = CrawlStateMachine()
        machine2.transition_to(CrawlState.INITIALIZING)
        machine2.transition_to(CrawlState.ERROR)
        
        # Try to transition from ERROR
        with pytest.raises(ValueError, match="Invalid transition"):
            machine2.transition_to(CrawlState.RUNNING)

    def test_error_transitions(self):
        """Test that ERROR can be reached from multiple states."""
        # From INITIALIZING
        machine1 = CrawlStateMachine()
        machine1.transition_to(CrawlState.INITIALIZING)
        machine1.transition_to(CrawlState.ERROR)
        assert machine1.state == CrawlState.ERROR
        
        # From RUNNING
        machine2 = CrawlStateMachine()
        machine2.transition_to(CrawlState.INITIALIZING)
        machine2.transition_to(CrawlState.RUNNING)
        machine2.transition_to(CrawlState.ERROR)
        assert machine2.state == CrawlState.ERROR

    def test_state_change_events(self):
        """Test that state change events are emitted."""
        machine = CrawlStateMachine()
        
        events = []
        def listener(old_state, new_state):
            events.append((old_state, new_state))
        
        machine.add_listener(listener)
        
        machine.transition_to(CrawlState.INITIALIZING)
        machine.transition_to(CrawlState.RUNNING)
        
        expected_events = [
            (CrawlState.UNINITIALIZED, CrawlState.INITIALIZING),
            (CrawlState.INITIALIZING, CrawlState.RUNNING)
        ]
        
        assert events == expected_events

    def test_remove_listener(self):
        """Test removing listeners."""
        machine = CrawlStateMachine()
        
        events = []
        def listener(old_state, new_state):
            events.append((old_state, new_state))
        
        machine.add_listener(listener)
        machine.transition_to(CrawlState.INITIALIZING)
        assert len(events) == 1
        
        machine.remove_listener(listener)
        machine.transition_to(CrawlState.RUNNING)
        assert len(events) == 1  # No new event

    def test_listener_exception_handling(self):
        """Test that listener exceptions don't break the state machine."""
        machine = CrawlStateMachine()
        
        def bad_listener(old_state, new_state):
            raise Exception("Listener failed")
        
        def good_listener(old_state, new_state):
            good_listener.called = True
        
        good_listener.called = False
        
        machine.add_listener(bad_listener)
        machine.add_listener(good_listener)
        
        # Should not raise exception
        machine.transition_to(CrawlState.INITIALIZING)
        
        assert machine.state == CrawlState.INITIALIZING
        assert good_listener.called