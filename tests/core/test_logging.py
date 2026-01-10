"""Tests for logging infrastructure."""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from mobile_crawler.core.log_sinks import (
    ConsoleSink,
    DatabaseSink,
    FileSink,
    JSONEventSink,
    LogLevel,
)
from mobile_crawler.core.logging_service import LoggingService
from mobile_crawler.infrastructure.database import DatabaseManager


class TestConsoleSink:
    """Test ConsoleSink."""

    def test_log_above_min_level(self):
        """Test logging when level is above minimum."""
        sink = ConsoleSink(min_level=LogLevel.WARNING)
        captured_output = StringIO()
        with patch('sys.stderr', captured_output):
            sink.log(LogLevel.ERROR, "Test error")

        output = captured_output.getvalue()
        assert "ERROR" in output
        assert "Test error" in output

    def test_log_below_min_level(self):
        """Test no logging when level is below minimum."""
        sink = ConsoleSink(min_level=LogLevel.WARNING)
        captured_output = StringIO()
        with patch('sys.stderr', captured_output):
            sink.log(LogLevel.INFO, "Test info")

        output = captured_output.getvalue()
        assert output == ""

    def test_log_with_extra_data(self):
        """Test logging with extra data."""
        sink = ConsoleSink(min_level=LogLevel.INFO)
        captured_output = StringIO()
        with patch('sys.stderr', captured_output):
            sink.log(LogLevel.INFO, "Test", {"key": "value"})

        output = captured_output.getvalue()
        assert "Test" in output
        assert "{'key': 'value'}" in output


class TestJSONEventSink:
    """Test JSONEventSink."""

    def test_log_creates_json_output(self):
        """Test that log creates valid JSON output."""
        sink = JSONEventSink()
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            sink.log(LogLevel.INFO, "Test message", {"extra": "data"})

        output = captured_output.getvalue().strip()
        event = json.loads(output)

        assert event["level"] == "INFO"
        assert event["message"] == "Test message"
        assert event["extra"] == {"extra": "data"}
        assert "timestamp" in event


class TestFileSink:
    """Test FileSink."""

    def test_log_writes_to_file(self):
        """Test that log writes to file."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
            log_file = Path(f.name)

        try:
            sink = FileSink(log_file=log_file)
            sink.log(LogLevel.INFO, "Test message")

            # Close the handler to release the file
            sink._logger.removeHandler(sink._handler)
            sink._handler.close()

            content = log_file.read_text()
            assert "INFO" in content
            assert "Test message" in content
        finally:
            log_file.unlink(missing_ok=True)


class TestDatabaseSink:
    """Test DatabaseSink."""

    def test_log_inserts_into_database(self):
        """Test that log inserts into logs table."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = Path(f.name)

        try:
            db_manager = DatabaseManager(db_path)
            db_manager.create_schema()

            sink = DatabaseSink(db_manager)
            sink.log(LogLevel.ERROR, "Test error", {"code": 500})

            conn = db_manager.get_connection()
            cursor = conn.execute("SELECT * FROM logs")
            rows = cursor.fetchall()

            assert len(rows) == 1
            row = rows[0]
            assert row["level"] == "ERROR"
            assert row["message"] == "Test error"
            assert json.loads(row["extra_json"]) == {"code": 500}

            db_manager.close()
        finally:
            db_path.unlink(missing_ok=True)


class TestLoggingService:
    """Test LoggingService."""

    def test_log_distributes_to_all_sinks(self):
        """Test that log distributes to all sinks."""
        console_sink = ConsoleSink(min_level=LogLevel.DEBUG)
        json_sink = JSONEventSink()

        captured_stderr = StringIO()
        captured_stdout = StringIO()

        with patch('sys.stderr', captured_stderr), patch('sys.stdout', captured_stdout):
            service = LoggingService([console_sink, json_sink])
            service.info("Test message")

        stderr_output = captured_stderr.getvalue()
        stdout_output = captured_stdout.getvalue()

        assert "Test message" in stderr_output
        assert "Test message" in stdout_output

    def test_convenience_methods(self):
        """Test convenience methods."""
        sink = ConsoleSink(min_level=LogLevel.DEBUG)
        captured_output = StringIO()

        with patch('sys.stderr', captured_output):
            service = LoggingService([sink])
            service.debug("Debug")
            service.info("Info")
            service.warning("Warning")
            service.error("Error")
            service.action("Action")

        output = captured_output.getvalue()
        assert "DEBUG" in output
        assert "INFO" in output
        assert "WARNING" in output
        assert "ERROR" in output
        assert "ACTION" in output

    def test_sink_error_handling(self):
        """Test that sink errors don't break logging."""
        class FailingSink:
            def log(self, level, message, extra_data=None):
                raise Exception("Sink failed")

        service = LoggingService([FailingSink()])
        captured_stderr = StringIO()

        with patch('sys.stderr', captured_stderr):
            # Should not raise
            service.info("Test")

        error_output = captured_stderr.getvalue()
        assert "Logging error" in error_output