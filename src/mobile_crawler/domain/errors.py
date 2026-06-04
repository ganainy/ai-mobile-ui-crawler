"""Typed exception taxonomy for the mobile crawler."""

import enum
from dataclasses import dataclass, field
from typing import Any


class ErrorSeverity(enum.Enum):
    """Severity classification for crawler errors."""

    RETRYABLE = "retryable"
    FATAL = "fatal"
    OPERATOR_ACTIONABLE = "operator_actionable"


@dataclass
class ErrorContext:
    """Structured context for errors."""

    run_id: int | None = None
    step_id: int | None = None
    action_type: str | None = None
    device_state: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "step_id": self.step_id,
            "action_type": self.action_type,
            "device_state": self.device_state,
            **self.extra,
        }


class CrawlerError(Exception):
    """Base class for all crawler errors."""

    severity: ErrorSeverity = ErrorSeverity.FATAL

    def __init__(
        self,
        message: str,
        *,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.context = context or ErrorContext()
        self.__cause__ = cause

    def to_log_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "error_type": self.__class__.__name__,
            "severity": self.severity.value,
            "message": str(self),
            **self.context.to_dict(),
        }
        if self.__cause__ is not None:
            result["cause_type"] = self.__cause__.__class__.__name__
            result["cause_message"] = str(self.__cause__)
        return result


class RetryableError(CrawlerError):
    """Error that may be retried."""

    severity = ErrorSeverity.RETRYABLE


class FatalError(CrawlerError):
    """Error that halts the run."""

    severity = ErrorSeverity.FATAL


class OperatorActionableError(CrawlerError):
    """Error requiring operator intervention."""

    severity = ErrorSeverity.OPERATOR_ACTIONABLE


# Domain-specific errors

class DeviceError(RetryableError):
    """Device interaction failure (may recover on retry)."""


class RecorderError(FatalError):
    """Persistence failure -- must halt the run (fail-closed)."""


class CheckpointError(FatalError):
    """Checkpoint persistence failure -- must halt the run."""


class AIServiceError(RetryableError):
    """AI service failure (may recover on retry)."""


class DeviceDisconnectedError(OperatorActionableError):
    """Device disconnected -- requires operator to reconnect."""
