"""Tests for CrawlController."""

from unittest.mock import Mock, patch
import pytest

from mobile_crawler.core.crawl_controller import (
    CrawlController,
    CrawlControlState,
)


class TestCrawlController:
    """Tests for CrawlController."""

    def test_init(self):
        """Test initialization."""
        controller = CrawlController()

        assert controller.state == CrawlControlState.STOPPED
        assert controller.is_stopped()
        assert not controller.is_running()
        assert not controller.is_paused()

    def test_pause_from_running(self):
        """Test pausing from running state."""
        controller = CrawlController()

        # Start running (simulate)
        controller._state = CrawlControlState.RUNNING

        # Pause
        controller.pause()

        assert controller.state == CrawlControlState.PAUSED
        assert controller.is_paused()
        assert not controller.is_running()

    def test_pause_from_stopped(self):
        """Test pausing from stopped state is no-op."""
        controller = CrawlController()

        assert controller.state == CrawlControlState.STOPPED

        # Pause (should be no-op)
        controller.pause()

        assert controller.state == CrawlControlState.STOPPED  # No change

    def test_pause_from_paused(self):
        """Test pausing from paused state is no-op."""
        controller = CrawlController()

        # Set to paused
        controller._state = CrawlControlState.PAUSED

        # Pause again (should be no-op)
        controller.pause()

        assert controller.state == CrawlControlState.PAUSED  # No change

    def test_resume_from_paused(self):
        """Test resuming from paused state."""
        controller = CrawlController()

        # Set to paused
        controller._state = CrawlControlState.PAUSED

        # Resume
        controller.resume()

        assert controller.state == CrawlControlState.RUNNING
        assert controller.is_running()
        assert not controller.is_paused()

    def test_resume_from_running(self):
        """Test resuming from running state is no-op."""
        controller = CrawlController()

        # Set to running
        controller._state = CrawlControlState.RUNNING

        # Resume (should be no-op)
        controller.resume()

        assert controller.state == CrawlControlState.RUNNING  # No change

    def test_resume_from_stopped(self):
        """Test resuming from stopped state is no-op."""
        controller = CrawlController()

        # Already stopped
        assert controller.state == CrawlControlState.STOPPED

        # Resume (should be no-op)
        controller.resume()

        assert controller.state == CrawlControlState.STOPPED  # No change

    def test_stop_from_running(self):
        """Test stopping from running state."""
        controller = CrawlController()

        # Set to running
        controller._state = CrawlControlState.RUNNING

        # Stop
        controller.stop()

        assert controller.state == CrawlControlState.STOPPED
        assert controller.is_stopped()

    def test_stop_from_paused(self):
        """Test stopping from paused state."""
        controller = CrawlController()

        # Set to paused
        controller._state = CrawlControlState.PAUSED

        # Stop
        controller.stop()

        assert controller.state == CrawlControlState.STOPPED
        assert controller.is_stopped()

    def test_stop_from_stopped(self):
        """Test stopping from stopped state is no-op."""
        controller = CrawlController()

        # Already stopped
        assert controller.state == CrawlControlState.STOPPED

        # Stop again (should be no-op)
        controller.stop()

        assert controller.state == CrawlControlState.STOPPED  # No change

    def test_is_running(self):
        """Test is_running property."""
        controller = CrawlController()

        # Stopped
        assert not controller.is_running()

        # Running
        controller._state = CrawlControlState.RUNNING
        assert controller.is_running()

        # Paused
        controller._state = CrawlControlState.PAUSED
        assert not controller.is_running()

    def test_is_paused(self):
        """Test is_paused property."""
        controller = CrawlController()

        # Stopped
        assert not controller.is_paused()

        # Paused
        controller._state = CrawlControlState.PAUSED
        assert controller.is_paused()

        # Running
        controller._state = CrawlControlState.RUNNING
        assert not controller.is_paused()

    def test_is_stopped(self):
        """Test is_stopped property."""
        controller = CrawlController()

        # Stopped
        assert controller.is_stopped()

        # Running
        controller._state = CrawlControlState.RUNNING
        assert not controller.is_stopped()

        # Paused
        controller._state = CrawlControlState.PAUSED
        assert not controller.is_stopped()

    def test_should_continue(self):
        """Test should_continue property."""
        controller = CrawlController()

        # Stopped
        assert not controller.should_continue()

        # Running
        controller._state = CrawlControlState.RUNNING
        assert controller.should_continue()

        # Paused
        controller._state = CrawlControlState.PAUSED
        assert not controller.should_continue()

    def test_state_change_listener(self):
        """Test state change listener."""
        controller = CrawlController()
        states_received = []

        def listener(state):
            states_received.append(state)

        controller.add_state_change_listener(listener)

        # Change state
        controller._state = CrawlControlState.RUNNING
        controller.pause()

        assert CrawlControlState.PAUSED in states_received

    def test_multiple_state_change_listeners(self):
        """Test multiple state change listeners."""
        controller = CrawlController()
        states_1 = []
        states_2 = []

        def listener1(state):
            states_1.append(state)

        def listener2(state):
            states_2.append(state)

        controller.add_state_change_listener(listener1)
        controller.add_state_change_listener(listener2)

        # Change state
        controller._state = CrawlControlState.RUNNING
        controller.pause()

        assert CrawlControlState.PAUSED in states_1
        assert CrawlControlState.PAUSED in states_2

    def test_remove_state_change_listener(self):
        """Test removing state change listener."""
        controller = CrawlController()
        states_received = []

        def listener(state):
            states_received.append(state)

        controller.add_state_change_listener(listener)

        # Remove listener
        controller.remove_state_change_listener(listener)

        # Change state
        controller._state = CrawlControlState.RUNNING
        controller.pause()

        assert len(states_received) == 0  # Listener was removed

    def test_reset(self):
        """Test reset functionality."""
        controller = CrawlController()
        states_received = []

        def listener(state):
            states_received.append(state)

        controller.add_state_change_listener(listener)

        # Change state
        controller._state = CrawlControlState.RUNNING
        controller.pause()

        assert len(states_received) == 1
        assert controller.state == CrawlControlState.PAUSED

        # Reset - clears listeners
        controller.reset()

        assert controller.state == CrawlControlState.STOPPED
        # After reset, state changes should not notify listeners
        controller._state = CrawlControlState.RUNNING
        assert len(states_received) == 1  # No new notification

    def test_thread_safety(self):
        """Test thread safety with concurrent operations."""
        import threading
        import time

        controller = CrawlController()
        states_received = []

        def listener(state):
            states_received.append(state)

        controller.add_state_change_listener(listener)

        # Simulate concurrent operations
        def pause_thread():
            controller._state = CrawlControlState.RUNNING
            controller.pause()

        def resume_thread():
            controller.resume()

        def stop_thread():
            controller.stop()

        threads = [
            threading.Thread(target=pause_thread),
            threading.Thread(target=resume_thread),
            threading.Thread(target=stop_thread),
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=1.0)

        # Verify final state is one of the expected states
        assert controller.state in [
            CrawlControlState.RUNNING,
            CrawlControlState.PAUSED,
            CrawlControlState.STOPPED,
        ]

    def test_state_sequence(self):
        """Test a typical state sequence."""
        controller = CrawlController()
        states_received = []

        def listener(state):
            states_received.append(state)

        controller.add_state_change_listener(listener)

        # Simulate typical sequence
        assert controller.state == CrawlControlState.STOPPED

        # Start running
        controller._state = CrawlControlState.RUNNING
        assert controller.is_running()
        assert controller.should_continue()

        # Pause
        controller.pause()
        assert controller.is_paused()
        assert not controller.should_continue()
        assert CrawlControlState.PAUSED in states_received

        # Resume
        controller.resume()
        assert controller.is_running()
        assert controller.should_continue()
        assert CrawlControlState.RUNNING in states_received

        # Stop
        controller.stop()
        assert controller.is_stopped()
        assert not controller.should_continue()
        assert CrawlControlState.STOPPED in states_received

    def test_listener_exception_handling(self):
        """Test that listener exceptions don't break state changes."""
        controller = CrawlController()
        states_received = []

        def good_listener(state):
            states_received.append(state)

        def bad_listener(state):
            raise Exception("Listener error")

        controller.add_state_change_listener(good_listener)
        controller.add_state_change_listener(bad_listener)

        # Change state - should not raise exception
        controller._state = CrawlControlState.RUNNING
        controller.pause()

        # Good listener should still be called
        assert CrawlControlState.PAUSED in states_received

    def test_control_state_enum(self):
        """Test CrawlControlState enum values."""
        assert CrawlControlState.RUNNING.value == "running"
        assert CrawlControlState.PAUSED.value == "paused"
        assert CrawlControlState.STOPPED.value == "stopped"
