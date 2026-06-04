"""Tests for structured error logging and fail-closed repository behavior."""

import json
import sqlite3
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from mobile_crawler.domain.errors import (
    CrawlerError,
    ErrorContext,
    RecorderError,
)
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import Run, RunRepository


class TestStructuredLogging:
    def test_crawler_error_to_log_dict(self):
        err = CrawlerError(
            "test error",
            context=ErrorContext(run_id=42, step_id=3, action_type="click"),
        )
        log_dict = err.to_log_dict()
        assert log_dict["error_type"] == "CrawlerError"
        assert log_dict["severity"] == "fatal"
        assert log_dict["message"] == "test error"
        assert log_dict["run_id"] == 42
        assert log_dict["step_id"] == 3
        assert log_dict["action_type"] == "click"

    def test_to_log_dict_is_json_serializable(self):
        err = RecorderError(
            "write failed",
            context=ErrorContext(run_id=1, device_state={"screen": "home"}),
        )
        raw = json.dumps(err.to_log_dict())
        parsed = json.loads(raw)
        assert parsed["error_type"] == "RecorderError"
        assert parsed["severity"] == "fatal"

    def test_chained_exception_in_log_dict(self):
        original = sqlite3.OperationalError("database is locked")
        err = RecorderError(
            "write failed",
            context=ErrorContext(run_id=1),
            cause=original,
        )
        log_dict = err.to_log_dict()
        assert log_dict["cause_type"] == "OperationalError"
        assert "database is locked" in log_dict["cause_message"]


class TestFailClosedRepository:
    @pytest.fixture
    def temp_db_path(self, tmp_path):
        return tmp_path / "test.db"

    @pytest.fixture
    def run_repo(self, temp_db_path):
        db_manager = DatabaseManager(db_path=temp_db_path)
        db_manager.create_schema()
        return RunRepository(db_manager)

    def test_create_run_raises_recorder_error_on_db_failure(self, run_repo):
        with patch.object(
            run_repo.db_manager, "get_connection", side_effect=sqlite3.OperationalError("locked")
        ):
            run = Run(
                id=None,
                device_id="dev",
                app_package="com.test",
                start_activity=None,
                start_time=datetime.now(tz=UTC),
                end_time=None,
                status="RUNNING",
                ai_provider=None,
                ai_model=None,
            )
            with pytest.raises(RecorderError) as exc_info:
                run_repo.create_run(run)
            assert exc_info.value.context.run_id is None
