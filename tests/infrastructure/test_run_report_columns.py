"""Run Report columns on runs: stop_reason, guided_progress_json, trace_id."""

import sqlite3
from datetime import datetime

from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import Run, RunRepository

LEGACY_RUNS_DDL = """
    CREATE TABLE runs (
        id INTEGER PRIMARY KEY,
        device_id TEXT NOT NULL,
        app_package TEXT NOT NULL,
        start_activity TEXT,
        start_time TEXT NOT NULL,
        end_time TEXT,
        status TEXT NOT NULL,
        ai_provider TEXT,
        ai_model TEXT,
        total_steps INTEGER DEFAULT 0,
        unique_screens INTEGER DEFAULT 0,
        session_path TEXT
    )
"""


def _make_run(**overrides) -> Run:
    fields = {
        "id": None,
        "device_id": "emulator-5554",
        "app_package": "com.example.app",
        "start_activity": None,
        "start_time": datetime(2026, 9, 19, 10, 0, 0),
        "end_time": None,
        "status": "RUNNING",
        "ai_provider": "gemini",
        "ai_model": "gemini-x",
    }
    fields.update(overrides)
    return Run(**fields)


def test_new_run_columns_round_trip(tmp_path):
    db = DatabaseManager(tmp_path / "crawler.db")
    db.migrate_schema()
    repo = RunRepository(db)

    run_id = repo.create_run(_make_run(stop_reason="step_limit", guided_progress_json='{"done": 2}', trace_id="abc123"))

    run = repo.get_run_by_id(run_id)
    assert run.stop_reason == "step_limit"
    assert run.guided_progress_json == '{"done": 2}'
    assert run.trace_id == "abc123"


def test_update_run_persists_stop_reason(tmp_path):
    db = DatabaseManager(tmp_path / "crawler.db")
    db.migrate_schema()
    repo = RunRepository(db)
    run_id = repo.create_run(_make_run())

    run = repo.get_run_by_id(run_id)
    run.stop_reason = "user_stop"
    repo.update_run(run)

    assert repo.get_run_by_id(run_id).stop_reason == "user_stop"


def test_legacy_database_migrates_and_old_runs_read_back_empty(tmp_path):
    db_path = tmp_path / "crawler.db"
    conn = sqlite3.connect(db_path)
    conn.execute(LEGACY_RUNS_DDL)
    conn.execute(
        "INSERT INTO runs (device_id, app_package, start_time, status) "
        "VALUES ('dev', 'com.old.app', '2026-01-01T00:00:00', 'STOPPED')"
    )
    conn.commit()
    conn.close()

    db = DatabaseManager(db_path)
    db.migrate_schema()
    repo = RunRepository(db)

    (old_run,) = repo.get_all_runs()
    assert old_run.app_package == "com.old.app"
    assert old_run.stop_reason is None
    assert old_run.guided_progress_json is None
    assert old_run.trace_id is None


def test_update_run_stats_records_stop_reason_and_guided_progress(tmp_path):
    db = DatabaseManager(tmp_path / "crawler.db")
    db.migrate_schema()
    repo = RunRepository(db)
    run_id = repo.create_run(_make_run())

    repo.update_run_stats(
        run_id,
        total_steps=4,
        unique_screens=0,
        status="COMPLETED",
        end_time=datetime(2026, 9, 19, 11, 0, 0),
        stop_reason="duration_limit",
        guided_progress_json='{"scenarios": ["a"]}',
    )

    run = repo.get_run_by_id(run_id)
    assert run.stop_reason == "duration_limit"
    assert run.guided_progress_json == '{"scenarios": ["a"]}'
    assert run.status == "COMPLETED"


def test_update_run_stats_without_extras_keeps_existing_stop_reason(tmp_path):
    db = DatabaseManager(tmp_path / "crawler.db")
    db.migrate_schema()
    repo = RunRepository(db)
    run_id = repo.create_run(_make_run(stop_reason="user_stop"))

    repo.update_run_stats(run_id, total_steps=2, unique_screens=0)

    assert repo.get_run_by_id(run_id).stop_reason == "user_stop"


def test_update_trace_id_round_trips(tmp_path):
    db = DatabaseManager(tmp_path / "crawler.db")
    db.migrate_schema()
    repo = RunRepository(db)
    run_id = repo.create_run(_make_run())

    assert repo.update_trace_id(run_id, "run-1-abcd1234") is True
    assert repo.get_run_by_id(run_id).trace_id == "run-1-abcd1234"
    assert repo.update_trace_id(9999, "x") is False
