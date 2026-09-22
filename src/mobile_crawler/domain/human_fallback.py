"""Human Fallback: opt-in prompt for codes and manual auth steps, with timeout (see CONTEXT.md).

Standalone: no Qt or agent dependency. The caller supplies a `HumanPrompter` that shows the
request to the user (blocking the calling crawl thread) and returns a reply, or None when the
timeout expired.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

FALLBACK_ENABLED_KEY = "human_fallback_enabled"
FALLBACK_TIMEOUT_KEY = "human_fallback_timeout_minutes"
DEFAULT_TIMEOUT_MINUTES = 5


class RequestKind(Enum):
    CODE = "code"  # user types the verification code
    MANUAL_STEP = "manual_step"  # user finishes the step on the device, then clicks Continue


class FallbackStatus(Enum):
    ANSWERED = "answered"
    TIMED_OUT = "timed_out"
    DISABLED = "disabled"
    DECLINED = "declined"  # user chose to skip authentication


@dataclass(frozen=True)
class HumanRequest:
    kind: RequestKind
    message: str


@dataclass(frozen=True)
class HumanReply:
    code: str | None = None  # set for CODE requests; None for MANUAL_STEP or when skipped
    skipped: bool = False


class HumanPrompter(Protocol):
    def __call__(self, request: HumanRequest, timeout_seconds: float) -> HumanReply | None: ...


@dataclass(frozen=True)
class FallbackOutcome:
    status: FallbackStatus
    code: str | None = None
    skip_note: str | None = None  # set whenever authentication should be skipped

    @property
    def answered(self) -> bool:
        return self.status is FallbackStatus.ANSWERED


@dataclass(frozen=True)
class HumanFallbackConfig:
    enabled: bool = False
    timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES

    @classmethod
    def from_store(cls, store, enabled_override: bool | None = None) -> "HumanFallbackConfig":
        """Build from the persisted setting, unless `enabled_override` is given (a single-run CLI override)."""
        minutes = store.get_setting(FALLBACK_TIMEOUT_KEY, default=DEFAULT_TIMEOUT_MINUTES)
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            minutes = DEFAULT_TIMEOUT_MINUTES
        enabled = (
            bool(store.get_setting(FALLBACK_ENABLED_KEY, default=False)) if enabled_override is None else enabled_override
        )
        return cls(enabled=enabled, timeout_minutes=max(1, minutes))


class HumanFallback:
    """Asks the user for help when automation can't finish authentication."""

    def __init__(self, config: HumanFallbackConfig, prompter: HumanPrompter | None):
        self._config = config
        self._prompter = prompter
        self.skipped_reason: str | None = None

    def request(self, kind: RequestKind, message: str) -> FallbackOutcome:
        """Ask the user; the crawl thread blocks until they answer or the timeout expires."""
        if not self._config.enabled or self._prompter is None:
            return self._skip(FallbackStatus.DISABLED, "authentication failed and Human Fallback is off")

        reply = self._prompter(HumanRequest(kind, message), self._config.timeout_minutes * 60.0)
        if reply is None:
            return self._skip(
                FallbackStatus.TIMED_OUT,
                f"no reply from user within {self._config.timeout_minutes} min",
            )
        if reply.skipped:
            return self._skip(FallbackStatus.DECLINED, "user skipped authentication")
        return FallbackOutcome(FallbackStatus.ANSWERED, code=reply.code)

    def _skip(self, status: FallbackStatus, why: str) -> FallbackOutcome:
        note = f"authentication skipped: {why}"
        self.skipped_reason = note
        return FallbackOutcome(status, skip_note=note)
