"""Tests for DroidRun-backed crawler loop wrapper."""

from unittest.mock import Mock, patch

from mobile_crawler.core.crawler_loop import CrawlerLoop


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

    with patch("mobile_crawler.core.crawler_loop.DroidRunAgentService") as service_cls:
        service = service_cls.return_value
        service.execute_exploration_task.return_value = result
        loop.run(1)

    assert ("started", 1, "com.example.app") in listener.events
    assert any(e[0] == "completed" for e in listener.events)
    run_repo.update_run_stats.assert_called_once()
