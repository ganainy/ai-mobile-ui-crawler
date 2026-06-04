"""Tests for DroidRun-backed crawler loop wrapper."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from mobile_crawler.core.crawler_loop import CrawlerLoop
from mobile_crawler.domain.errors import ErrorContext, RecorderError


class TestListener:
    def __init__(self):
        self.events = []

    def on_crawl_started(self, run_id, target_package):
        self.events.append(("started", run_id, target_package))

    def on_state_changed(self, run_id, old_state, new_state):
        self.events.append(("state", run_id, old_state, new_state))

    def on_crawl_completed(self, run_id, total_steps, duration_ms, reason, ocr_avg_ms=0.0):
        self.events.append(("completed", run_id, total_steps, reason))

    def on_error(self, run_id, step_number, error):
        self.events.append(("error", run_id, step_number, str(error)))


def test_droidrun_wrapper_happy_path():
    config_manager = Mock()
    config_manager.get.side_effect = lambda key, default=None: {
        "max_crawl_steps": 3,
        "droidrun_streaming": False,
        "exploration_objective": None,
    }.get(key, default)

    run_repo = Mock()
    run = Mock()
    run.id = 1
    run.device_id = "emulator-5554"
    run.app_package = "com.example.app"
    run_repo.get_run_by_id.return_value = run

    session_manager = Mock()
    session_manager.create_session_folder.return_value = "C:/tmp/session"
    session_manager.get_subfolder.return_value = "C:/tmp/session/logs"

    listener = TestListener()

    loop = CrawlerLoop(
        config_manager=config_manager,
        run_repository=run_repo,
        session_folder_manager=session_manager,
        event_listeners=[listener],
    )

    result = Mock()
    result.success = True
    result.steps_completed = 3
    result.error_message = None
    result.final_state = {"successful_actions": 3, "failed_actions": 0, "total_actions": 3, "completion_reason": "done"}

    with patch("mobile_crawler.core.crawler_loop.CrawlerAgentService") as service_cls:
        service = service_cls.return_value
        service.execute_exploration_task = AsyncMock(return_value=result)
        service.cleanup = AsyncMock()
        service.begin_step_tracking = Mock()
        service.configure_run_logging = Mock()
        service.clear_run_logging = Mock()
        service._stats_processor = Mock()
        service._stats_processor.get_stats.return_value = None
        loop.run(1)

    assert ("started", 1, "com.example.app") in listener.events
    assert any(e[0] == "completed" for e in listener.events)
    run_repo.update_run_stats.assert_called_once()


class FailingRecorderListener(TestListener):
    def on_crawl_completed(self, run_id, total_steps, duration_ms, reason, ocr_avg_ms=0.0):
        raise RecorderError(
            "DB write failed",
            context=ErrorContext(run_id=run_id),
        )

    def on_state_changed(self, run_id, old_state, new_state):
        self.events.append(("state", run_id, old_state, new_state))


def test_emit_event_propagates_recorder_error():
    loop = CrawlerLoop(
        config_manager=Mock(),
        run_repository=Mock(),
        session_folder_manager=Mock(),
        event_listeners=[FailingRecorderListener()],
    )
    with pytest.raises(RecorderError):
        loop._emit_event("on_crawl_completed", 1, 5, 1000.0, "done", 0.0)


def test_emit_event_continues_on_non_critical_error():
    class FlakyListener(TestListener):
        def on_debug_log(self, run_id, step_number, message):
            raise RuntimeError("UI widget broke")

    loop = CrawlerLoop(
        config_manager=Mock(),
        run_repository=Mock(),
        session_folder_manager=Mock(),
        event_listeners=[FlakyListener()],
    )
    # Should not raise — non-critical listener failures are logged and swallowed
    loop._emit_event("on_debug_log", 1, 0, "test message")
