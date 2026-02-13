"""Tests for crawler loop."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from PIL import Image
from mobile_crawler.core.crawler_event_listener import CrawlerEventListener
from mobile_crawler.core.crawler_loop import CrawlerLoop
from mobile_crawler.core.crawl_state_machine import CrawlStateMachine
from mobile_crawler.domain.models import ActionResult, AIAction, AIResponse, BoundingBox


class TestEventListener:
    """Test implementation of CrawlerEventListener interface."""

    def __init__(self):
        self.events = []

    def on_crawl_started(self, run_id: int, target_package: str) -> None:
        self.events.append(("crawl_started", run_id, target_package))

    def on_step_started(self, run_id: int, step_number: int) -> None:
        self.events.append(("step_started", run_id, step_number))

    def on_screenshot_captured(self, run_id: int, step_number: int, screenshot_path: str) -> None:
        self.events.append(("screenshot_captured", run_id, step_number, screenshot_path))

    def on_ai_request_sent(self, run_id: int, step_number: int, request_data: dict) -> None:
        self.events.append(("ai_request_sent", run_id, step_number, request_data))

    def on_ai_response_received(self, run_id: int, step_number: int, response_data: dict) -> None:
        self.events.append(("ai_response_received", run_id, step_number, response_data))

    def on_action_executed(self, run_id: int, step_number: int, action_index: int, result: ActionResult) -> None:
        self.events.append(("action_executed", run_id, step_number, action_index, result))

    def on_step_completed(self, run_id: int, step_number: int, actions_count: int, duration_ms: float) -> None:
        self.events.append(("step_completed", run_id, step_number, actions_count, duration_ms))

    def on_crawl_completed(self, run_id: int, total_steps: int, total_duration_ms: float, reason: str) -> None:
        self.events.append(("crawl_completed", run_id, total_steps, total_duration_ms, reason))

    def on_error(self, run_id: int, step_number: int, error: Exception) -> None:
        self.events.append(("error", run_id, step_number, str(error)))

    def on_state_changed(self, run_id: int, old_state: str, new_state: str) -> None:
        self.events.append(("state_changed", run_id, old_state, new_state))


class TestCrawlerLoop:
    """Test CrawlerLoop."""

    def test_crawler_loop_basic_execution(self):
        """Test basic crawler loop execution."""
        # Setup mocks
        state_machine = CrawlStateMachine()
        screenshot_capture = Mock()
        mock_image = Image.new('RGB', (100, 100))
        screenshot_capture.capture_full.return_value = (mock_image, "/path/to/screenshot.png", "base64data", 1.0)
        screenshot_capture.capture_screenshot.return_value = mock_image

        ai_service = Mock()
        ai_response = AIResponse(
            actions=[
                AIAction(
                    action="click",
                    action_desc="Click button",
                    target_bounding_box=BoundingBox(top_left=(100, 200), bottom_right=(300, 250)),
                    input_text=None,
                    reasoning="Button visible"
                )
            ],
            signup_completed=False
        )
        ai_service.get_next_actions.return_value = ai_response

        action_executor = Mock()
        action_executor.click.return_value = ActionResult(
            success=True, action_type="click", target="(100,200)-(300,250)", duration_ms=100.0,
            error_message=None, navigated_away=False
        )

        step_log_repo = Mock()
        step_log_repo.create_step_log.return_value = 1

        run_repo = Mock()
        run = Mock()
        run.target_package = "com.example.app"
        run_repo.get_run.return_value = run

        config_manager = Mock()
        config_manager.get.side_effect = lambda key, default: {
            'max_crawl_steps': 2,
            'max_crawl_duration_seconds': 60
        }.get(key, default)

        event_listener = TestEventListener()

        session_folder_manager = Mock()
        session_folder_manager.get_subfolder.return_value = "/tmp/screenshots"
        screen_tracker = Mock()
        screen_tracker.is_stuck.return_value = (False, None)
        appium_driver = MagicMock()
        appium_driver.get_driver().current_package = "com.example.app"

        # Create crawler loop
        crawler = CrawlerLoop(
            state_machine, screenshot_capture, ai_service, action_executor,
            step_log_repo, run_repo, config_manager, 
            appium_driver, screen_tracker, session_folder_manager, [event_listener]
        )

        with patch.object(CrawlerLoop, "_ensure_app_foreground", return_value=True):
            # Execute
            crawler.run(1)

        # Verify state transitions
        assert state_machine.state.value == "stopped"

        # Verify events were emitted
        events = event_listener.events
        assert len(events) >= 8  # Should have multiple events

        # Check key events
        event_types = [e[0] for e in events]
        assert "crawl_started" in event_types
        assert "state_changed" in event_types
        assert "step_started" in event_types
        assert "screenshot_captured" in event_types
        assert "ai_request_sent" in event_types
        assert "ai_response_received" in event_types
        assert "action_executed" in event_types
        assert "step_completed" in event_types
        assert "crawl_completed" in event_types

    def test_crawler_loop_respects_max_steps(self):
        """Test that crawler respects maximum steps limit."""
        # Setup mocks
        state_machine = CrawlStateMachine()
        screenshot_capture = Mock()
        mock_image = Image.new('RGB', (100, 100))
        screenshot_capture.capture_full.return_value = (mock_image, "/path/to/screenshot.png", "base64data", 1.0)
        screenshot_capture.capture_screenshot.return_value = mock_image

        ai_service = Mock()
        ai_response = AIResponse(actions=[], signup_completed=False)  # No actions = continue
        ai_service.get_next_actions.return_value = ai_response

        action_executor = Mock()
        step_log_repo = Mock()
        run_repo = Mock()
        run = Mock()
        run.target_package = "com.example.app"
        run_repo.get_run.return_value = run

        config_manager = Mock()
        config_manager.get.side_effect = lambda key, default: {
            'max_crawl_steps': 1,  # Only 1 step allowed
            'max_crawl_duration_seconds': 60
        }.get(key, default)

        event_listener = TestEventListener()

        session_folder_manager = Mock()
        session_folder_manager.get_subfolder.return_value = "/tmp/screenshots"
        appium_driver = MagicMock()
        appium_driver.get_driver().current_package = "com.example.app"

        screen_tracker = Mock()
        screen_tracker.is_stuck.return_value = (False, None)
        screen_tracker.process_screen.return_value = Mock(screen_id=1, is_new=True, visit_count=1, total_screens_discovered=1)

        crawler = CrawlerLoop(
            state_machine, screenshot_capture, ai_service, action_executor,
            step_log_repo, run_repo, config_manager, 
            appium_driver, screen_tracker, session_folder_manager, [event_listener]
        )

        with patch.object(CrawlerLoop, "_ensure_app_foreground", return_value=True):
            crawler.run(1)

        # Should complete after 1 step
        crawl_completed_events = [e for e in event_listener.events if e[0] == "crawl_completed"]
        assert len(crawl_completed_events) == 1
        reason = crawl_completed_events[0][4]
        assert "maximum steps" in reason

    def test_crawler_loop_handles_action_failure(self):
        """Test that crawler handles action execution failure."""
        # Setup mocks
        state_machine = CrawlStateMachine()
        screenshot_capture = Mock()
        mock_image = Image.new('RGB', (100, 100))
        screenshot_capture.capture_full.return_value = (mock_image, "/path/to/screenshot.png", "base64data", 1.0)
        screenshot_capture.capture_screenshot.return_value = mock_image

        ai_service = Mock()
        ai_response = AIResponse(
            actions=[
                AIAction(
                    action="click",
                    action_desc="Click button",
                    target_bounding_box=BoundingBox(top_left=(100, 200), bottom_right=(300, 250)),
                    input_text=None,
                    reasoning="Button visible"
                )
            ],
            signup_completed=False
        )
        ai_service.get_next_actions.return_value = ai_response

        action_executor = Mock()
        action_executor.click.return_value = ActionResult(
            success=False, action_type="click", target="(100,200)-(300,250)", 
            duration_ms=50.0, error_message="Element not found", navigated_away=False
        )

        step_log_repo = Mock()
        run_repo = Mock()
        run = Mock()
        run.target_package = "com.example.app"
        run_repo.get_run.return_value = run

        config_manager = Mock()
        config_manager.get.side_effect = lambda key, default: {
            'max_crawl_steps': 5,
            'max_crawl_duration_seconds': 60
        }.get(key, default)

        event_listener = TestEventListener()

        session_folder_manager = Mock()
        session_folder_manager.get_subfolder.return_value = "/tmp/screenshots"
        appium_driver = MagicMock()
        appium_driver.get_driver().current_package = "com.example.app"

        screen_tracker = Mock()
        screen_tracker.is_stuck.return_value = (False, None)
        screen_tracker.process_screen.return_value = Mock(screen_id=1, is_new=True, visit_count=1, total_screens_discovered=1)

        crawler = CrawlerLoop(
            state_machine, screenshot_capture, ai_service, action_executor,
            step_log_repo, run_repo, config_manager, 
            appium_driver, screen_tracker, session_folder_manager, [event_listener]
        )

        with patch.object(CrawlerLoop, "_ensure_app_foreground", return_value=True):
            crawler.run(1)

        # Should have completed the crawl (stopped after failed action)
        assert state_machine.state.value == "stopped"

        # Check that action failure was logged
        action_events = [e for e in event_listener.events if e[0] == "action_executed"]
        assert len(action_events) == 1
        result = action_events[0][4]
        assert result.success is False

    def test_crawler_loop_handles_ai_error(self):
        """Test that crawler handles AI service errors."""
        # Setup mocks
        state_machine = CrawlStateMachine()
        screenshot_capture = Mock()
        mock_image = Image.new('RGB', (100, 100))
        screenshot_capture.capture_full.return_value = (mock_image, "/path/to/screenshot.png", "base64data", 1.0)
        screenshot_capture.capture_screenshot.return_value = mock_image

        ai_service = Mock()
        ai_service.get_next_actions.side_effect = Exception("AI service unavailable")

        action_executor = Mock()
        step_log_repo = Mock()
        run_repo = Mock()
        run = Mock()
        run.target_package = "com.example.app"
        run_repo.get_run.return_value = run

        config_manager = Mock()
        config_manager.get.side_effect = lambda key, default: {
            'max_crawl_steps': 5,
            'max_crawl_duration_seconds': 60
        }.get(key, default)

        event_listener = TestEventListener()

        session_folder_manager = Mock()
        session_folder_manager.get_subfolder.return_value = "/tmp/screenshots"
        appium_driver = MagicMock()
        appium_driver.get_driver().current_package = "com.example.app"

        screen_tracker = Mock()
        screen_tracker.is_stuck.return_value = (False, None)
        screen_tracker.process_screen.return_value = Mock(screen_id=1, is_new=True, visit_count=1, total_screens_discovered=1)

        crawler = CrawlerLoop(
            state_machine, screenshot_capture, ai_service, action_executor,
            step_log_repo, run_repo, config_manager, 
            appium_driver, screen_tracker, session_folder_manager, [event_listener]
        )

        # Should raise exception
        with patch.object(CrawlerLoop, "_ensure_app_foreground", return_value=True):
            with pytest.raises(Exception, match="AI service unavailable"):
                crawler.run(1)

        # Should be in error state
        assert state_machine.state.value == "error"

        # Should have error event
        error_events = [e for e in event_listener.events if e[0] == "error"]
        assert len(error_events) == 1

    def test_crawler_loop_event_listener_management(self):
        """Test adding and removing event listeners."""
        state_machine = CrawlStateMachine()
        screenshot_capture = Mock()
        ai_service = Mock()
        action_executor = Mock()
        step_log_repo = Mock()
        run_repo = Mock()
        config_manager = Mock()

        crawler = CrawlerLoop(
            state_machine, screenshot_capture, ai_service, action_executor,
            step_log_repo, run_repo, config_manager, Mock(), Mock(), Mock()
        )

        # Initially no listeners
        assert len(crawler.event_listeners) == 0

        # Add listener
        listener = TestEventListener()
        crawler.add_event_listener(listener)
        assert len(crawler.event_listeners) == 1

        # Remove listener
        crawler.remove_event_listener(listener)
        assert len(crawler.event_listeners) == 0

        # Remove non-existent listener (should not error)
        crawler.remove_event_listener(listener)
        assert len(crawler.event_listeners) == 0

    def test_crawler_loop_invalid_run_id(self):
        """Test crawler loop with invalid run ID."""
        state_machine = CrawlStateMachine()
        screenshot_capture = Mock()
        ai_service = Mock()
        action_executor = Mock()
        step_log_repo = Mock()
        run_repo = Mock()
        run_repo.get_run.return_value = None  # No run found

        config_manager = Mock()

        crawler = CrawlerLoop(
            state_machine, screenshot_capture, ai_service, action_executor,
            step_log_repo, run_repo, config_manager, Mock(), Mock(), Mock()
        )

        with pytest.raises(ValueError, match="Run 999 not found"):
            crawler.run(999)