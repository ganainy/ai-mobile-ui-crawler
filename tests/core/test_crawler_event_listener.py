"""Tests for CrawlerEventListener ABC contract and default implementations."""


import pytest

from mobile_crawler.core.crawler_event_listener import CrawlerEventListener
from mobile_crawler.domain.models import ActionResult


class ConcreteCrawlerEventListener(CrawlerEventListener):
    """Concrete implementation of CrawlerEventListener for testing."""

    def on_crawl_started(self, run_id, target_package):
        pass

    def on_step_started(self, run_id, step_number):
        pass

    def on_screenshot_captured(self, run_id, step_number, screenshot_path):
        pass

    def on_ai_request_sent(self, run_id, step_number, request_data):
        pass

    def on_ai_response_received(self, run_id, step_number, response_data):
        pass

    def on_action_executed(self, run_id, step_number, action_index, result):
        pass

    def on_step_completed(self, run_id, step_number, actions_count, duration_ms):
        pass

    def on_crawl_completed(self, run_id, total_steps, total_duration_ms, reason, ocr_avg_ms=0.0):
        pass

    def on_error(self, run_id, step_number, error):
        pass

    def on_state_changed(self, run_id, old_state, new_state):
        pass

    def on_screen_processed(self, run_id, step_number, screen_id, is_new, visit_count, total_screens):
        pass

    def on_debug_log(self, run_id, step_number, message):
        pass

    def on_ocr_completed(self, run_id, step_number, duration_ms, element_count):
        pass

    def on_screenshot_timing(self, run_id, step_number, duration_ms):
        pass


class TestCrawlerEventListenerABC:
    """Tests for CrawlerEventListener abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Test that CrawlerEventListener cannot be instantiated directly."""
        with pytest.raises(TypeError, match="abstract"):
            CrawlerEventListener()

    def test_concrete_subclass_can_be_instantiated(self):
        """Test that a concrete subclass implementing all methods works."""
        listener = ConcreteCrawlerEventListener()
        assert isinstance(listener, CrawlerEventListener)

    def test_omitting_abstract_method_raises_typeerror(self):
        """Test that omitting any abstractmethod raises TypeError."""
        class PartialListener(CrawlerEventListener):
            def on_crawl_started(self, run_id, target_package):
                pass

        with pytest.raises(TypeError, match="abstract"):
            PartialListener()

    def test_default_on_recovery_started_is_noop(self):
        """Test that on_recovery_started default can be called without error."""
        listener = ConcreteCrawlerEventListener()
        # Should not raise
        listener.on_recovery_started(1, 1, 1)

    def test_default_on_recovery_completed_is_noop(self):
        """Test that on_recovery_completed default can be called without error."""
        listener = ConcreteCrawlerEventListener()
        # Should not raise
        listener.on_recovery_completed(1, 1, True, 100.0)

    def test_default_on_recovery_exhausted_is_noop(self):
        """Test that on_recovery_exhausted default can be called without error."""
        listener = ConcreteCrawlerEventListener()
        # Should not raise
        listener.on_recovery_exhausted(1, 1, 3, "Max retries reached")

    def test_default_on_step_phase_transition_is_noop(self):
        """Test that on_step_phase_transition default can be called without error."""
        listener = ConcreteCrawlerEventListener()
        # Should not raise
        listener.on_step_phase_transition(1, 1, "capture", "decide", 50.0)

    def test_abstract_methods_must_all_be_implemented(self):
        """Test that all 14 abstract methods must be implemented."""
        # This verifies the complete contract - any missing method should fail
        with pytest.raises(TypeError, match="abstract"):
            class EmptyListener(CrawlerEventListener):
                pass
            EmptyListener()

    def test_listener_with_event_data(self):
        """Test that concrete listener can receive and handle event data."""
        class TrackingListener(CrawlerEventListener):
            def __init__(self):
                self.events = []

            def on_crawl_started(self, run_id, target_package):
                self.events.append(("crawl_started", run_id, target_package))

            def on_step_started(self, run_id, step_number):
                self.events.append(("step_started", run_id, step_number))

            def on_screenshot_captured(self, run_id, step_number, screenshot_path):
                self.events.append(("screenshot", run_id, step_number, screenshot_path))

            def on_ai_request_sent(self, run_id, step_number, request_data):
                pass

            def on_ai_response_received(self, run_id, step_number, response_data):
                pass

            def on_action_executed(self, run_id, step_number, action_index, result):
                self.events.append(("action", run_id, step_number, action_index, result))

            def on_step_completed(self, run_id, step_number, actions_count, duration_ms):
                pass

            def on_crawl_completed(self, run_id, total_steps, total_duration_ms, reason, ocr_avg_ms=0.0):
                self.events.append(("crawl_completed", run_id, total_steps))

            def on_error(self, run_id, step_number, error):
                self.events.append(("error", run_id, step_number, str(error)))

            def on_state_changed(self, run_id, old_state, new_state):
                self.events.append(("state_changed", run_id, old_state, new_state))

            def on_screen_processed(self, run_id, step_number, screen_id, is_new, visit_count, total_screens):
                pass

            def on_debug_log(self, run_id, step_number, message):
                pass

            def on_ocr_completed(self, run_id, step_number, duration_ms, element_count):
                pass

            def on_screenshot_timing(self, run_id, step_number, duration_ms):
                pass

        listener = TrackingListener()
        listener.on_crawl_started(42, "com.example.app")
        listener.on_step_started(42, 1)
        listener.on_state_changed(42, "IDLE", "RUNNING")
        result = ActionResult(success=True, action_type="click", target="btn1")
        listener.on_action_executed(42, 1, 0, result)
        listener.on_crawl_completed(42, 5, 1000.0, "done")
        listener.on_error(42, 2, ValueError("test"))

        assert len(listener.events) == 6
        assert listener.events[0] == ("crawl_started", 42, "com.example.app")
        assert listener.events[1] == ("step_started", 42, 1)
        assert listener.events[2] == ("state_changed", 42, "IDLE", "RUNNING")
        assert listener.events[3][0] == "action"
        assert listener.events[4] == ("crawl_completed", 42, 5)
        assert listener.events[5][0] == "error"
