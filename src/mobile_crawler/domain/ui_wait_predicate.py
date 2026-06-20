"""Explicit wait predicates for UI synchronization.

Replaces fixed-duration sleeps (ADBActionExecutor._action_delay_ms = 1500)
with polling-based waits that check UI state readiness.
"""
import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class StateProvider(Protocol):
    """Protocol for UI state capture."""

    async def get_state(self) -> Any:
        """Return current UI state."""
        ...


@dataclass
class WaitProfile:
    """Wait configuration for a specific action type."""
    timeout_ms: float
    poll_interval_ms: float

    @property
    def timeout_s(self) -> float:
        return self.timeout_ms / 1000.0

    @property
    def poll_interval_s(self) -> float:
        return self.poll_interval_ms / 1000.0


# Action-type to wait profile mapping
DEFAULT_WAIT_PROFILES: dict[str, WaitProfile] = {
    "default": WaitProfile(timeout_ms=3000, poll_interval_ms=200),
    "tap": WaitProfile(timeout_ms=2000, poll_interval_ms=150),
    "click": WaitProfile(timeout_ms=3000, poll_interval_ms=200),
    "scroll": WaitProfile(timeout_ms=1500, poll_interval_ms=100),
    "scroll_up": WaitProfile(timeout_ms=1500, poll_interval_ms=100),
    "scroll_down": WaitProfile(timeout_ms=1500, poll_interval_ms=100),
    "swipe": WaitProfile(timeout_ms=1500, poll_interval_ms=100),
    "type": WaitProfile(timeout_ms=2000, poll_interval_ms=200),
    "input": WaitProfile(timeout_ms=2000, poll_interval_ms=200),
    "back": WaitProfile(timeout_ms=3000, poll_interval_ms=200),
    "home": WaitProfile(timeout_ms=3000, poll_interval_ms=200),
    "start_app": WaitProfile(timeout_ms=5000, poll_interval_ms=300),
    "launch_app": WaitProfile(timeout_ms=5000, poll_interval_ms=300),
}


class AdaptiveWaitConfig:
    """Loads adaptive wait profiles from config, falling back to defaults."""

    def __init__(self, config_manager=None):
        """
        Args:
            config_manager: Optional ConfigManager for reading user overrides.
                            If None, uses DEFAULT_WAIT_PROFILES.
        """
        self.config_manager = config_manager
        self._profiles: dict[str, WaitProfile] = {}

    def get_profile(self, action_type: str) -> WaitProfile:
        """Get wait profile for an action type.

        Checks config_manager first, then DEFAULT_WAIT_PROFILES,
        then falls back to the "default" profile.
        """
        if action_type in self._profiles:
            return self._profiles[action_type]

        profile = self._load_profile(action_type)
        self._profiles[action_type] = profile
        return profile

    def _load_profile(self, action_type: str) -> WaitProfile:
        """Load a profile from config or defaults."""
        # Check defaults first
        if action_type in DEFAULT_WAIT_PROFILES:
            default = DEFAULT_WAIT_PROFILES[action_type]
        else:
            default = DEFAULT_WAIT_PROFILES["default"]

        if self.config_manager is None:
            return default

        # Allow config to override specific timeouts
        timeout = self.config_manager.get(
            f"wait_{action_type}_timeout_ms",
            default.timeout_ms,
        )
        poll_interval = self.config_manager.get(
            f"wait_{action_type}_poll_interval_ms",
            default.poll_interval_ms,
        )

        return WaitProfile(
            timeout_ms=float(timeout),
            poll_interval_ms=float(poll_interval),
        )

    @classmethod
    def from_config(cls, config_manager) -> "AdaptiveWaitConfig":
        """Create an AdaptiveWaitConfig from a ConfigManager."""
        return cls(config_manager=config_manager)


class UIWaitPredicate:
    """Polls UI state until a readiness condition is met.

    Replaces fixed-duration sleeps in ADBActionExecutor with explicit
    readiness checks using DroidRun's StateProvider.
    """

    def __init__(
        self,
        state_provider: StateProvider,
        config: AdaptiveWaitConfig | None = None,
        latest_state_provider: Callable[[], Any] | None = None,
        current_app_provider: Callable[[], Awaitable[str]] | None = None,
        expensive_state_polling: bool | None = None,
    ):
        """
        Args:
            state_provider: Object with async get_state() method returning
                            an object with formatted_text attribute.
            config: Adaptive wait configuration. Uses defaults if None.
        """
        self.state_provider = state_provider
        self.config = config or AdaptiveWaitConfig()
        self.latest_state_provider = latest_state_provider
        self.current_app_provider = current_app_provider
        self.expensive_state_polling = (
            expensive_state_polling
            if expensive_state_polling is not None
            else getattr(state_provider, "ui_parser_mode", None) == "omniparser"
        )

    async def wait_for_ui_settled(
        self,
        action_type: str,
        timeout_ms: float | None = None,
    ) -> bool:
        """Wait until UI state is stable after an action.

        Polls state_provider.get_state() and compares formatted_text
        between consecutive polls. Returns True when two consecutive
        reads return identical text (UI has settled).

        Args:
            action_type: Type of action (tap, click, scroll, etc.)
                        Used to select the appropriate wait profile.
            timeout_ms: Override timeout in ms. If None, uses profile default.

        Returns:
            True if UI settled within timeout, False if timed out.
        """
        profile = self.config.get_profile(action_type)
        timeout = (timeout_ms if timeout_ms is not None else profile.timeout_ms) / 1000.0
        poll_interval = profile.poll_interval_s

        if self.expensive_state_polling:
            await asyncio.sleep(min(timeout, max(0.2, poll_interval)))
            if self.current_app_provider:
                try:
                    current_app = await self.current_app_provider()
                    logger.debug(
                        "UI settle used cheap current-app check for %s: current_app=%s",
                        action_type,
                        current_app or "",
                    )
                except Exception as e:
                    logger.debug(f"Cheap current-app check failed after {action_type}: {e}")
            else:
                logger.debug(
                    "UI settle used fixed settle delay for %s because state polling is expensive",
                    action_type,
                )
            return True

        deadline = time.monotonic() + timeout
        latest_state = self.latest_state_provider() if self.latest_state_provider else None
        prev_text: str | None = getattr(latest_state, "formatted_text", None)
        poll_count = 0

        while time.monotonic() < deadline:
            poll_count += 1
            try:
                ui_state = await self.state_provider.get_state()
                current_text = getattr(ui_state, "formatted_text", None)

                if current_text is not None and current_text == prev_text:
                    logger.debug(
                        f"UI settled after {poll_count} polls "
                        f"({action_type}, ~{poll_count * profile.poll_interval_ms:.0f}ms)"
                    )
                    return True

                prev_text = current_text
            except Exception as e:
                logger.debug(f"State poll failed (will retry): {e}")

            await asyncio.sleep(poll_interval)

        logger.debug(
            f"UI wait timed out after {poll_count} polls "
            f"({action_type}, {timeout:.1f}s)"
        )
        return False
