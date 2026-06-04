"""Tests for the typed exception taxonomy."""

import pytest

from mobile_crawler.domain.errors import (
    AIServiceError,
    CheckpointError,
    CrawlerError,
    DeviceDisconnectedError,
    DeviceError,
    ErrorContext,
    ErrorSeverity,
    FatalError,
    OperatorActionableError,
    RecorderError,
    RetryableError,
)


class TestErrorContext:
    def test_default_values(self):
        ctx = ErrorContext()
        assert ctx.run_id is None
        assert ctx.step_id is None
        assert ctx.action_type is None
        assert ctx.device_state is None
        assert ctx.extra == {}

    def test_to_dict(self):
        ctx = ErrorContext(run_id=42, step_id=3, action_type="click")
        d = ctx.to_dict()
        assert d["run_id"] == 42
        assert d["step_id"] == 3
        assert d["action_type"] == "click"


class TestCrawlerError:
    def test_default_severity_is_fatal(self):
        err = CrawlerError("test")
        assert err.severity == ErrorSeverity.FATAL

    def test_to_log_dict_includes_type(self):
        err = CrawlerError("test error")
        log_dict = err.to_log_dict()
        assert log_dict["error_type"] == "CrawlerError"
        assert log_dict["severity"] == "fatal"
        assert log_dict["message"] == "test error"

    def test_exception_chaining(self):
        original = ValueError("original")
        err = CrawlerError("wrapped", cause=original)
        log_dict = err.to_log_dict()
        assert log_dict["cause_type"] == "ValueError"
        assert "original" in log_dict["cause_message"]


class TestRetryableError:
    def test_severity(self):
        err = RetryableError("retry me")
        assert err.severity == ErrorSeverity.RETRYABLE


class TestFatalError:
    def test_severity(self):
        err = FatalError("fatal")
        assert err.severity == ErrorSeverity.FATAL


class TestRecorderError:
    def test_is_fatal(self):
        err = RecorderError("db write failed")
        assert err.severity == ErrorSeverity.FATAL

    def test_is_caught_by_crawler_error(self):
        with pytest.raises(CrawlerError):
            raise RecorderError("db write failed")

    def test_is_caught_by_fatal_error(self):
        with pytest.raises(FatalError):
            raise RecorderError("db write failed")


class TestDeviceError:
    def test_is_retryable(self):
        err = DeviceError("device busy")
        assert err.severity == ErrorSeverity.RETRYABLE


class TestInheritance:
    def test_device_error_inheritance(self):
        assert issubclass(DeviceError, RetryableError)
        assert issubclass(DeviceError, CrawlerError)

    def test_recorder_error_inheritance(self):
        assert issubclass(RecorderError, FatalError)
        assert issubclass(RecorderError, CrawlerError)

    def test_checkpoint_error_inheritance(self):
        assert issubclass(CheckpointError, FatalError)
        assert issubclass(CheckpointError, CrawlerError)

    def test_device_disconnected_error_inheritance(self):
        assert issubclass(DeviceDisconnectedError, OperatorActionableError)
        assert issubclass(DeviceDisconnectedError, CrawlerError)

    def test_all_inherit_from_crawler_error(self):
        for cls in [
            DeviceError,
            RecorderError,
            CheckpointError,
            AIServiceError,
            DeviceDisconnectedError,
        ]:
            assert issubclass(cls, CrawlerError)
