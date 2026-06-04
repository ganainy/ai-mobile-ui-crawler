"""Tests for LoggingService."""

from unittest.mock import Mock, patch

from mobile_crawler.core.log_sinks import LogLevel
from mobile_crawler.core.logging_service import LoggingService


class TestLoggingService:
    """Tests for LoggingService."""

    def test_init_with_sinks(self):
        """Test LoggingService initialization with sinks."""
        sink = Mock()
        service = LoggingService(sinks=[sink])
        assert service.sinks == [sink]

    def test_init_with_empty_sinks(self):
        """Test LoggingService initialization with empty sinks list."""
        service = LoggingService(sinks=[])
        assert service.sinks == []

    def test_log_dispatches_to_all_sinks(self):
        """Test log() dispatches to all sinks."""
        sink1 = Mock()
        sink2 = Mock()
        service = LoggingService(sinks=[sink1, sink2])

        service.log(LogLevel.INFO, "test message", extra_data={"key": "value"})

        sink1.log.assert_called_once_with(LogLevel.INFO, "test message", {"key": "value"})
        sink2.log.assert_called_once_with(LogLevel.INFO, "test message", {"key": "value"})

    def test_log_handles_sink_exception(self):
        """Test log() handles sink exceptions gracefully."""
        bad_sink = Mock()
        bad_sink.log.side_effect = Exception("sink error")
        good_sink = Mock()

        service = LoggingService(sinks=[bad_sink, good_sink])

        # Should not raise
        service.log(LogLevel.INFO, "test message")

        # Good sink should still be called
        good_sink.log.assert_called_once()

    @patch('sys.stderr', new_callable=Mock)
    def test_log_fallback_to_stderr(self, mock_stderr):
        """Test log() falls back to stderr when sink raises."""
        bad_sink = Mock()
        bad_sink.log.side_effect = Exception("sink error")

        service = LoggingService(sinks=[bad_sink])
        service.log(LogLevel.INFO, "test message")

        mock_stderr.write.assert_called()

    def test_log_without_extra_data(self):
        """Test log() with no extra_data."""
        sink = Mock()
        service = LoggingService(sinks=[sink])

        service.log(LogLevel.WARNING, "warning message")
        sink.log.assert_called_once_with(LogLevel.WARNING, "warning message", None)

    def test_debug_level(self):
        """Test debug() convenience method."""
        sink = Mock()
        service = LoggingService(sinks=[sink])

        service.debug("debug message")
        sink.log.assert_called_once_with(LogLevel.DEBUG, "debug message", None)

    def test_info_level(self):
        """Test info() convenience method."""
        sink = Mock()
        service = LoggingService(sinks=[sink])

        service.info("info message")
        sink.log.assert_called_once_with(LogLevel.INFO, "info message", None)

    def test_warning_level(self):
        """Test warning() convenience method."""
        sink = Mock()
        service = LoggingService(sinks=[sink])

        service.warning("warning message")
        sink.log.assert_called_once_with(LogLevel.WARNING, "warning message", None)

    def test_error_level(self):
        """Test error() convenience method."""
        sink = Mock()
        service = LoggingService(sinks=[sink])

        service.error("error message")
        sink.log.assert_called_once_with(LogLevel.ERROR, "error message", None)

    def test_action_level(self):
        """Test action() convenience method."""
        sink = Mock()
        service = LoggingService(sinks=[sink])

        service.action("action message")
        sink.log.assert_called_once_with(LogLevel.ACTION, "action message", None)

    def test_convenience_methods_with_extra_data(self):
        """Test convenience methods pass extra_data through."""
        sink = Mock()
        service = LoggingService(sinks=[sink])
        extra = {"run_id": 42}

        service.info("info", extra_data=extra)
        sink.log.assert_called_once_with(LogLevel.INFO, "info", extra)

    def test_re_initialization_idempotent(self):
        """Test re-initializing LoggingService is effectively idempotent."""
        sink = Mock()
        service1 = LoggingService(sinks=[sink])
        service2 = LoggingService(sinks=[sink])

        service1.info("msg1")
        service2.info("msg2")

        assert sink.log.call_count == 2
