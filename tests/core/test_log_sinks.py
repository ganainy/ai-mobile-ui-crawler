"""Tests for log sink abstractions."""

import json
import logging
import sys
from unittest.mock import MagicMock, Mock, patch

from mobile_crawler.core.log_sinks import (
    ConsoleSink,
    DatabaseSink,
    FileSink,
    JSONEventSink,
    LogLevel,
    LogSink,
    QLogHandler,
    _LineCapturingStream,
    capture_stdout_to_ui,
)


class TestConsoleSink:
    """Tests for ConsoleSink."""

    def test_console_sink_instantiation(self):
        """Test ConsoleSink can be instantiated."""
        sink = ConsoleSink()
        assert sink.min_level == LogLevel.INFO

    def test_console_sink_with_custom_min_level(self):
        """Test ConsoleSink with custom minimum level."""
        sink = ConsoleSink(min_level=LogLevel.DEBUG)
        assert sink.min_level == LogLevel.DEBUG

    @patch('sys.stderr', new_callable=MagicMock)
    def test_console_sink_logs_at_or_above_min_level(self, mock_stderr):
        """Test ConsoleSink logs messages at or above min level."""
        sink = ConsoleSink(min_level=LogLevel.INFO)
        sink.log(LogLevel.INFO, "test message")
        mock_stderr.write.assert_called()
        written = mock_stderr.write.call_args_list[0][0][0]
        assert "test message" in written

    @patch('sys.stderr', new_callable=MagicMock)
    def test_console_sink_skips_below_min_level(self, mock_stderr):
        """Test ConsoleSink skips messages below min level."""
        sink = ConsoleSink(min_level=LogLevel.WARNING)
        sink.log(LogLevel.INFO, "info message")
        mock_stderr.write.assert_not_called()

    @patch('sys.stderr', new_callable=MagicMock)
    def test_console_sink_includes_extra_data(self, mock_stderr):
        """Test ConsoleSink includes extra data when provided."""
        sink = ConsoleSink()
        sink.log(LogLevel.INFO, "test", extra_data={"key": "value"})
        written = mock_stderr.write.call_args_list[0][0][0]
        assert "key" in written

    def test_console_sink_handles_none_extra(self):
        """Test ConsoleSink handles None extra_data gracefully."""
        sink = ConsoleSink()
        # Should not raise
        sink.log(LogLevel.INFO, "test message", extra_data=None)


class TestJSONEventSink:
    """Tests for JSONEventSink."""

    def test_json_event_sink_instantiation(self):
        """Test JSONEventSink can be instantiated."""
        sink = JSONEventSink()
        assert isinstance(sink, LogSink)

    @patch('sys.stdout', new_callable=MagicMock)
    def test_json_event_sink_outputs_valid_json(self, mock_stdout):
        """Test JSONEventSink outputs valid JSON."""
        sink = JSONEventSink()
        sink.log(LogLevel.INFO, "test message", extra_data={"run_id": 42})
        mock_stdout.write.assert_called()
        written = mock_stdout.write.call_args_list[0][0][0]
        event = json.loads(written.strip())
        assert event["level"] == "INFO"
        assert event["message"] == "test message"
        assert event["extra"]["run_id"] == 42

    @patch('sys.stdout', new_callable=MagicMock)
    def test_json_event_sink_without_extra(self, mock_stdout):
        """Test JSONEventSink outputs JSON without extra data."""
        sink = JSONEventSink()
        sink.log(LogLevel.ERROR, "error message")
        written = mock_stdout.write.call_args_list[0][0][0]
        event = json.loads(written.strip())
        assert "extra" not in event
        assert event["message"] == "error message"


class TestFileSink:
    """Tests for FileSink."""

    def test_file_sink_instantiation(self, tmp_path):
        """Test FileSink can be instantiated with a custom log file."""
        log_file = tmp_path / "test.log"
        sink = FileSink(log_file=log_file)
        assert sink.log_file == log_file

    def test_file_sink_log_writes_to_file(self, tmp_path):
        """Test FileSink writes log entries to file."""
        log_file = tmp_path / "test.log"
        sink = FileSink(log_file=log_file)
        sink.log(LogLevel.INFO, "test message")

        # Read the log file
        content = log_file.read_text()
        assert "test message" in content

    def test_file_sink_handles_error_level(self, tmp_path):
        """Test FileSink handles ERROR level correctly."""
        log_file = tmp_path / "test.log"
        sink = FileSink(log_file=log_file)
        sink.log(LogLevel.ERROR, "error occurred")

        content = log_file.read_text()
        assert "error occurred" in content

    def test_file_sink_with_extra_data(self, tmp_path):
        """Test FileSink handles extra data."""
        log_file = tmp_path / "test.log"
        sink = FileSink(log_file=log_file)
        sink.log(LogLevel.INFO, "test", extra_data={"key": "value"})

        content = log_file.read_text()
        assert "test" in content
        assert "key" in content


class TestDatabaseSink:
    """Tests for DatabaseSink."""

    def test_database_sink_instantiation_with_mock_db(self):
        """Test DatabaseSink can be instantiated with mock db manager."""
        mock_db = Mock()
        mock_conn = Mock()
        mock_db.get_connection.return_value = mock_conn
        sink = DatabaseSink(db_manager=mock_db)
        assert sink.db_manager == mock_db

    def test_database_sink_persists_log(self):
        """Test DatabaseSink persists log to database."""
        mock_db = Mock()
        mock_conn = Mock()
        Mock()
        mock_conn.execute = Mock()
        mock_conn.commit = Mock()
        mock_db.get_connection.return_value = mock_conn

        sink = DatabaseSink(db_manager=mock_db)
        sink.log(LogLevel.INFO, "test message", extra_data={"run_id": 42})

        mock_conn.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_database_sink_handles_none_extra(self):
        """Test DatabaseSink handles None extra_data."""
        mock_db = Mock()
        mock_conn = Mock()
        mock_conn.execute = Mock()
        mock_conn.commit = Mock()
        mock_db.get_connection.return_value = mock_conn

        sink = DatabaseSink(db_manager=mock_db)
        sink.log(LogLevel.WARNING, "warning message")

        args = mock_conn.execute.call_args[0]
        # Check that None extra_data is handled (extra_json should be None)
        assert args[1][3] is None


class TestQLogHandler:
    """Tests for QLogHandler."""

    def test_qlog_handler_instantiation(self):
        """Test QLogHandler can be instantiated."""
        callback = Mock()
        handler = QLogHandler(callback)
        assert handler._callback == callback

    def test_qlog_handler_emits_to_callback(self):
        """Test QLogHandler forwards log records to callback."""
        callback = Mock()
        handler = QLogHandler(callback)

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        handler.emit(record)

        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == LogLevel.INFO
        assert "test message" in args[1]

    def test_qlog_handler_suppresses_noisy_loggers(self):
        """Test QLogHandler suppresses noisy third-party loggers."""
        callback = Mock()
        handler = QLogHandler(callback)

        record = logging.LogRecord(
            name="httpx.connection", level=logging.DEBUG, pathname="", lineno=0,
            msg="connection msg", args=(), exc_info=None
        )
        handler.emit(record)

        callback.assert_not_called()

    def test_qlog_handler_error_safety(self):
        """Test QLogHandler never raises on callback failure."""
        callback = Mock(side_effect=Exception("callback error"))
        handler = QLogHandler(callback)

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        # Should not raise
        handler.emit(record)


class TestLineCapturingStream:
    """Tests for _LineCapturingStream."""

    def test_line_capturing_stream_forwards_lines(self):
        """Test _LineCapturingStream forwards complete lines to callback."""
        original = MagicMock()
        callback = Mock()
        stream = _LineCapturingStream(original, callback, LogLevel.DEBUG)

        stream.write("hello world\n")
        callback.assert_called_once_with("hello world")

    def test_line_capturing_stream_buffers_partial_lines(self):
        """Test _LineCapturingStream buffers partial lines."""
        original = MagicMock()
        callback = Mock()
        stream = _LineCapturingStream(original, callback, LogLevel.DEBUG)

        stream.write("hello ")
        callback.assert_not_called()
        stream.write("world\n")
        callback.assert_called_once_with("hello world")

    def test_line_capturing_stream_skips_empty_lines(self):
        """Test _LineCapturingStream skips blank lines."""
        original = MagicMock()
        callback = Mock()
        stream = _LineCapturingStream(original, callback, LogLevel.DEBUG)

        stream.write("\n\n\n")
        callback.assert_not_called()


class TestCaptureStdoutToUI:
    """Tests for capture_stdout_to_ui context manager."""

    def test_capture_stdout_context_manager(self):
        """Test capture_stdout_to_ui captures stdout."""
        callback = Mock()
        with capture_stdout_to_ui(callback):
            print("test message", flush=True)

        # The callback should have been called with the captured line
        callback.assert_called()

    def test_capture_stdout_restores_streams(self):
        """Test capture_stdout_to_ui restores original streams."""
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        callback = Mock()

        with capture_stdout_to_ui(callback):
            pass

        assert sys.stdout is original_stdout
        assert sys.stderr is original_stderr
