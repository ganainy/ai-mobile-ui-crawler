"""RunStatsRecorder turns crawler events into a saved run_stats row."""

from datetime import datetime

import pytest

from mobile_crawler.core.run_stats_recorder import RunStatsRecorder
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import Run, RunRepository
from mobile_crawler.infrastructure.run_stats_repository import RunStatsRepository
from mobile_crawler.infrastructure.screen_repository import Screen, ScreenRepository


@pytest.fixture
def db(tmp_path):
    manager = DatabaseManager(tmp_path / "crawler.db")
    manager.migrate_schema()
    return manager


@pytest.fixture
def run_id(db):
    return RunRepository(db).create_run(
        Run(
            id=None,
            device_id="emulator-5554",
            app_package="com.example.health",
            start_activity=None,
            start_time=datetime(2026, 9, 23, 10, 0, 0),
            end_time=None,
            status="RUNNING",
            ai_provider="gemini",
            ai_model="gemini-x",
            total_steps=0,
            unique_screens=0,
        )
    )


def _screen(db, run_id, hash_):
    return ScreenRepository(db).create_screen(
        Screen(None, hash_, hash_, None, None, first_seen_run_id=run_id, first_seen_step=1)
    )


def test_events_are_saved_as_run_stats(db, run_id, tmp_path):
    repository = RunStatsRepository(db)
    recorder = RunStatsRecorder(repository)
    home, detail = _screen(db, run_id, "00ff00ff00ff00ff"), _screen(db, run_id, "ff00ff00ff00ff00")
    session = tmp_path / "session"
    (session / "pcap").mkdir(parents=True)
    (session / "pcap" / "capture.pcap").write_bytes(b"x" * 10)

    recorder.on_crawl_started(run_id, "com.example.health")
    recorder.on_screen_processed(run_id, 1, home, True, 1, 1)
    recorder.on_ai_response_received(
        run_id,
        1,
        {"latency_ms": 800.0, "tokens_input": 100, "tokens_output": 20, "call_type": "manager", "retry_count": 1},
    )
    recorder.on_action_timing(run_id, 1, "click", True, 50.0)
    recorder.on_action_timing(run_id, 2, "type", False, 30.0)
    recorder.on_screen_processed(run_id, 2, detail, True, 1, 2)
    recorder.on_screen_processed(run_id, 3, home, False, 2, 2)

    assert recorder.save(run_id, session_path=str(session)) is True

    stats = repository.get_run_stats(run_id)
    assert (stats.total_steps, stats.successful_steps, stats.failed_steps) == (2, 1, 1)
    assert stats.actions_by_type == {"click": 1, "type": 1}
    assert (stats.unique_screens_visited, stats.total_screen_visits) == (2, 3)
    assert stats.most_visited_screen_count == 2
    assert (stats.total_ai_calls, stats.total_ai_tokens_used, stats.ai_retry_count) == (1, 120, 1)
    assert stats.ai_total_by_type == {"manager": 1}
    assert stats.app_package == "com.example.health"
    assert stats.pcap_file_size_bytes == 10


def test_saves_only_once_per_run(db, run_id):
    recorder = RunStatsRecorder(RunStatsRepository(db))
    recorder.on_crawl_started(run_id, "com.example.health")

    assert recorder.save(run_id, None) is True
    assert recorder.save(run_id, None) is False


def test_events_of_another_run_are_ignored(db, run_id):
    repository = RunStatsRepository(db)
    recorder = RunStatsRecorder(repository)
    recorder.on_crawl_started(run_id, "com.example.health")

    recorder.on_action_timing(run_id + 1, 1, "click", True, 50.0)
    recorder.save(run_id, None)

    assert repository.get_run_stats(run_id).total_steps == 0
