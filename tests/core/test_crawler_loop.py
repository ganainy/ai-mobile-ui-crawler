"""Tests for CrawlerLoop lifecycle, event emission, and error handling."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from mobile_crawler.core.crawler_loop import CrawlerLoop
from mobile_crawler.domain.models import ActionResult


@pytest.fixture
def mock_config_manager():
    return Mock()


@pytest.fixture
def mock_run_repository():
    return Mock()


@pytest.fixture
def mock_session_folder_manager():
    return Mock()


@pytest.fixture
def mock_listener():
    listener = Mock()
    return listener


@pytest.fixture
def crawler_loop(mock_config_manager, mock_run_repository, mock_session_folder_manager, mock_listener):
    return CrawlerLoop(
        config_manager=mock_config_manager,
        run_repository=mock_run_repository,
        session_folder_manager=mock_session_folder_manager,
        event_listeners=[mock_listener]
    )


class TestCrawlerLoopInitialization:
    """Tests for CrawlerLoop initialization."""

    def test_init_with_valid_config(self, mock_config_manager, mock_run_repository, mock_session_folder_manager):
        """Test CrawlerLoop initialization with valid config."""
        loop = CrawlerLoop(
            config_manager=mock_config_manager,
            run_repository=mock_run_repository,
            session_folder_manager=mock_session_folder_manager
        )
        assert loop.config_manager == mock_config_manager
        assert loop.run_repository == mock_run_repository
        assert loop.session_folder_manager == mock_session_folder_manager
        assert loop.event_listeners == []
        assert loop._state == "IDLE"
        assert not loop.is_running()

    def test_init_with_event_listeners(self, mock_config_manager, mock_run_repository, mock_session_folder_manager, mock_listener):
        """Test initialization with event listeners."""
        loop = CrawlerLoop(
            config_manager=mock_config_manager,
            run_repository=mock_run_repository,
            session_folder_manager=mock_session_folder_manager,
            event_listeners=[mock_listener]
        )
        assert len(loop.event_listeners) == 1

    def test_add_event_listener(self, crawler_loop):
        """Test adding an event listener."""
        new_listener = Mock()
        crawler_loop.add_event_listener(new_listener)
        assert new_listener in crawler_loop.event_listeners

    def test_remove_event_listener(self, crawler_loop, mock_listener):
        """Test removing an event listener."""
        crawler_loop.remove_event_listener(mock_listener)
        assert mock_listener not in crawler_loop.event_listeners


class TestCrawlerLoopLifecycle:
    """Tests for CrawlerLoop lifecycle and state transitions."""

    @patch('mobile_crawler.core.crawler_loop.DroidRunAgentService')
    def test_run_emits_on_crawl_started(self, mock_droid_service_class, crawler_loop, mock_run_repository, mock_session_folder_manager, mock_listener):
        """Test that run() emits on_crawl_started event."""
        mock_run = Mock()
        mock_run.app_package = "com.example.app"
        mock_run.device_id = "device123"
        mock_run_repository.get_run_by_id.return_value = mock_run
        mock_session_folder_manager.create_session_folder.return_value = "/tmp/session"

        mock_service = Mock()
        mock_service.configure_run_logging.return_value = None
        mock_service.clear_run_logging.return_value = None
        mock_service.execute_exploration_task = Mock()
        mock_droid_service_class.return_value = mock_service

        async def mock_explore(*args, **kwargs):
            mock_result = Mock()
            mock_result.success = True
            mock_result.steps_completed = 5
            mock_result.error_message = None
            mock_result.final_state = {}
            return mock_result

        mock_service.execute_exploration_task = mock_explore
        mock_service.cleanup = Mock()

        crawler_loop.run(1)

        # Verify on_crawl_started was called
        mock_listener.on_crawl_started.assert_called_once_with(1, "com.example.app")

    @patch('mobile_crawler.core.crawler_loop.VideoRecordingManager')
    @patch('mobile_crawler.core.crawler_loop.DroidRunAgentService')
    def test_run_starts_and_stops_video_recording_when_enabled(
        self,
        mock_droid_service_class,
        mock_video_manager_class,
        crawler_loop,
        mock_config_manager,
        mock_run_repository,
        mock_session_folder_manager,
        mock_listener,
    ):
        """Video recording flag should produce best-effort start/stop lifecycle calls."""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "enable_video_recording": True,
            "limit_type": "steps",
            "max_crawl_steps": 1,
            "max_crawl_duration_seconds": 300,
        }.get(key, default)

        mock_run = Mock()
        mock_run.app_package = "com.example.app"
        mock_run.device_id = "device123"
        mock_run_repository.get_run_by_id.return_value = mock_run
        mock_session_folder_manager.create_session_folder.return_value = "/tmp/session"

        mock_video_manager = Mock()
        mock_video_manager.start_recording_async = AsyncMock(return_value=(True, "Video recording started"))
        mock_video_manager.stop_recording_and_save_async = AsyncMock(return_value="/tmp/session/videos/part001.mp4")
        mock_video_manager_class.return_value = mock_video_manager

        mock_service = Mock()
        mock_droid_service_class.return_value = mock_service

        async def mock_explore(*args, **kwargs):
            mock_result = Mock()
            mock_result.success = True
            mock_result.steps_completed = 1
            mock_result.error_message = None
            mock_result.final_state = {"completion_reason": "Reached max step count of 1 steps"}
            return mock_result

        mock_service.execute_exploration_task = mock_explore
        mock_service.cleanup = AsyncMock()

        crawler_loop.run(1)

        mock_video_manager.start_recording_async.assert_awaited_once_with(
            run_id=1,
            session_path="/tmp/session",
            app_package="com.example.app",
        )
        mock_video_manager.stop_recording_and_save_async.assert_awaited_once()
        mock_run_repository.update_run_stats.assert_called_once()
        assert mock_run_repository.update_run_stats.call_args.kwargs["status"] == "COMPLETED"

    @patch('mobile_crawler.core.crawler_loop.DroidRunAgentService')
    def test_run_transitions_through_states(self, mock_droid_service_class, crawler_loop, mock_run_repository, mock_session_folder_manager, mock_listener):
        """Test that run() transitions through states IDLE -> RUNNING -> STOPPED."""
        mock_run = Mock()
        mock_run.app_package = "com.example.app"
        mock_run.device_id = "device123"
        mock_run_repository.get_run_by_id.return_value = mock_run
        mock_session_folder_manager.create_session_folder.return_value = "/tmp/session"

        mock_service = Mock()
        mock_droid_service_class.return_value = mock_service

        async def mock_explore(*args, **kwargs):
            mock_result = Mock()
            mock_result.success = True
            mock_result.steps_completed = 3
            mock_result.error_message = None
            mock_result.final_state = {}
            return mock_result

        mock_service.execute_exploration_task = mock_explore
        mock_service.cleanup = Mock()

        states = []
        def state_tracker(run_id, old_state, new_state):
            states.append((old_state, new_state))
        mock_listener.on_state_changed.side_effect = state_tracker

        crawler_loop.run(1)

        # Should have transitioned from IDLE to RUNNING, then to STOPPED
        assert ("IDLE", "RUNNING") in states
        assert any(s[1] == "STOPPED" for s in states)

    @patch('mobile_crawler.core.crawler_loop.DroidRunAgentService')
    def test_run_handles_exception_and_emits_on_error(self, mock_droid_service_class, crawler_loop, mock_run_repository, mock_session_folder_manager, mock_listener):
        """Test that run() handles exceptions and emits on_error."""
        mock_run = Mock()
        mock_run.app_package = "com.example.app"
        mock_run.device_id = "device123"
        mock_run_repository.get_run_by_id.return_value = mock_run
        mock_session_folder_manager.create_session_folder.return_value = "/tmp/session"

        mock_service = Mock()
        mock_droid_service_class.return_value = mock_service

        async def mock_explore_raises(*args, **kwargs):
            raise ValueError("Simulated error")

        mock_service.execute_exploration_task = mock_explore_raises
        mock_service.cleanup = Mock()

        crawler_loop.run(1)

        # Verify on_error was called
        mock_listener.on_error.assert_called_once()
        args = mock_listener.on_error.call_args
        assert args[0][0] == 1  # run_id

    def test_is_running_returns_false_initially(self, crawler_loop):
        """Test is_running returns False when not started."""
        assert not crawler_loop.is_running()

    def test_is_running_returns_true_while_running(self, crawler_loop):
        """Test is_running returns True while thread is active."""
        import threading
        import time

        def slow_run():
            time.sleep(0.1)

        crawler_loop._crawl_thread = threading.Thread(target=slow_run)
        crawler_loop._crawl_thread.start()
        assert crawler_loop.is_running()
        crawler_loop._crawl_thread.join(timeout=1.0)

    def test_start_raises_if_already_running(self, crawler_loop):
        """Test start raises RuntimeError if crawler is already running."""
        import threading
        import time

        def slow_run():
            time.sleep(0.5)

        crawler_loop._crawl_thread = threading.Thread(target=slow_run)
        crawler_loop._crawl_thread.start()

        with pytest.raises(RuntimeError, match="already running"):
            crawler_loop.start(1)

        crawler_loop._crawl_thread.join(timeout=1.0)

    def test_stop_sets_cancel_requested(self, crawler_loop):
        """Test stop sets cancel flag."""
        crawler_loop.stop()
        assert crawler_loop._cancel_requested

    def test_pause_emits_debug_log(self, crawler_loop, mock_listener):
        """Test pause emits debug log about unsupported operation."""
        crawler_loop.pause()
        mock_listener.on_debug_log.assert_called_once()
        assert "not supported" in mock_listener.on_debug_log.call_args[0][2].lower()

    def test_resume_emits_debug_log(self, crawler_loop, mock_listener):
        """Test resume emits debug log about unsupported operation."""
        crawler_loop.resume()
        mock_listener.on_debug_log.assert_called_once()

    def test_set_step_by_step_enabled_emits_debug_log(self, crawler_loop, mock_listener):
        """Test set_step_by_step_enabled emits debug log."""
        crawler_loop.set_step_by_step_enabled(True)
        mock_listener.on_debug_log.assert_called_once()

    def test_advance_step_emits_debug_log(self, crawler_loop, mock_listener):
        """Test advance_step emits debug log."""
        crawler_loop.advance_step()
        mock_listener.on_debug_log.assert_called_once()

    def test_is_step_by_step_enabled_returns_false(self, crawler_loop):
        """Test is_step_by_step_enabled always returns False."""
        assert not crawler_loop.is_step_by_step_enabled()


class TestCrawlerLoopEventEmission:
    """Tests for CrawlerLoop event emission."""

    def test_emit_event_dispatches_to_all_listeners(self, crawler_loop):
        """Test _emit_event dispatches to all registered listeners."""
        listener1 = Mock()
        listener2 = Mock()
        crawler_loop.add_event_listener(listener1)
        crawler_loop.add_event_listener(listener2)

        crawler_loop._emit_event("on_debug_log", 1, 0, "test message")

        listener1.on_debug_log.assert_called_once_with(1, 0, "test message")
        listener2.on_debug_log.assert_called_once_with(1, 0, "test message")

    def test_emit_event_skips_missing_handler(self, crawler_loop):
        """Test _emit_event skips listeners without the handler method."""
        listener = Mock()
        del listener.on_debug_log
        crawler_loop.add_event_listener(listener)

        # Should not raise
        crawler_loop._emit_event("on_debug_log", 1, 0, "test")

    def test_emit_event_logs_warning_on_listener_exception(self, crawler_loop):
        """Test _emit_event logs warning for non-critical listener failures."""
        listener = Mock()
        listener.on_debug_log.side_effect = ValueError("listener error")
        crawler_loop.add_event_listener(listener)

        # Should not raise
        crawler_loop._emit_event("on_debug_log", 1, 0, "test")

    def test_emit_event_raises_on_recorder_error(self, crawler_loop):
        """Test _emit_event re-raises RecorderError."""
        from mobile_crawler.domain.errors import RecorderError
        listener = Mock()
        listener.on_debug_log.side_effect = RecorderError("recorder failed")
        crawler_loop.add_event_listener(listener)

        with pytest.raises(RecorderError):
            crawler_loop._emit_event("on_debug_log", 1, 0, "test")

    def test_emit_event_raises_on_checkpoint_error(self, crawler_loop):
        """Test _emit_event re-raises CheckpointError."""
        from mobile_crawler.domain.errors import CheckpointError
        listener = Mock()
        listener.on_debug_log.side_effect = CheckpointError("checkpoint failed")
        crawler_loop.add_event_listener(listener)

        with pytest.raises(CheckpointError):
            crawler_loop._emit_event("on_debug_log", 1, 0, "test")


class TestCrawlerLoopErrorHandling:
    """Tests for CrawlerLoop error handling."""

    def test_run_handles_missing_run_as_fatal_error(self, crawler_loop, mock_run_repository, mock_listener):
        """Test run() wraps missing run error in FatalError and emits on_error."""
        mock_run_repository.get_run_by_id.return_value = None

        crawler_loop.run(999)

        # Verify on_error was called with a FatalError wrapping the ValueError
        mock_listener.on_error.assert_called_once()
        args = mock_listener.on_error.call_args
        assert args[0][0] == 999  # run_id
        from mobile_crawler.domain.errors import FatalError
        assert isinstance(args[0][2], FatalError)

    @patch('mobile_crawler.core.crawler_loop.DroidRunAgentService')
    def test_run_handles_crawler_error(self, mock_droid_service_class, crawler_loop, mock_run_repository, mock_session_folder_manager, mock_listener):
        """Test run() handles CrawlerError gracefully."""
        from mobile_crawler.domain.errors import CrawlerError, ErrorContext
        mock_run = Mock()
        mock_run.app_package = "com.example.app"
        mock_run.device_id = "device123"
        mock_run_repository.get_run_by_id.return_value = mock_run
        mock_session_folder_manager.create_session_folder.return_value = "/tmp/session"

        mock_service = Mock()
        mock_droid_service_class.return_value = mock_service

        async def mock_explore_raises(*args, **kwargs):
            raise CrawlerError("crawler error", context=ErrorContext(run_id=1))

        mock_service.execute_exploration_task = mock_explore_raises
        mock_service.cleanup = Mock()

        crawler_loop.run(1)

        # Should emit on_error with the CrawlerError
        mock_listener.on_error.assert_called_once()
        error_arg = mock_listener.on_error.call_args[0][2]
        assert isinstance(error_arg, CrawlerError)

    def test_transition_state_updates_state(self, crawler_loop, mock_listener):
        """Test _transition_state updates internal state and notifies."""
        crawler_loop._transition_state("RUNNING", 1)
        assert crawler_loop._state == "RUNNING"
        mock_listener.on_state_changed.assert_called_once_with(1, "IDLE", "RUNNING")
