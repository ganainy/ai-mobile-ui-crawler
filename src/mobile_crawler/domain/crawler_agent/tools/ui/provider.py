"""StateProvider — orchestrates fetching and parsing device state.

Fetches raw data from a ``DeviceDriver``, applies tree filters/formatters,
and produces a ``UIState`` snapshot.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional

from mobile_crawler.domain.crawler_agent.tools.driver.base import DeviceDisconnectedError
from mobile_crawler.domain.crawler_agent.tools.ui.state import UIState
from mobile_crawler.domain.crawler_agent.tools.ui.stealth_state import StealthUIState

if TYPE_CHECKING:
    from mobile_crawler.domain.crawler_agent.tools.driver.base import DeviceDriver
    from mobile_crawler.domain.crawler_agent.tools.filters import TreeFilter
    from mobile_crawler.domain.crawler_agent.tools.formatters import TreeFormatter

logger = logging.getLogger("crawler_agent")

# Retry schedule: delay in seconds after each failed attempt.
# Total wait across 7 attempts: 1+2+3+5+8+10 = 29s.
_RETRY_DELAYS = [1.0, 2.0, 3.0, 5.0, 8.0, 10.0]
_MAX_RETRIES = 7

# After this many consecutive failures, run the recovery callback.
# With the schedule above, this fires after ~11s (1+2+3+5).
_RECOVERY_AFTER_ATTEMPT = 5


async def fetch_state_with_retry(
    fetch: Callable[[], Awaitable[Dict[str, Any]]],
    recovery: Optional[Callable[[], Awaitable[None]]] = None,
    max_retries: int = _MAX_RETRIES,
    retry_delays: Optional[List[float]] = None,
    recovery_after: int = _RECOVERY_AFTER_ATTEMPT,
) -> Dict[str, Any]:
    """Fetch raw device state with retries, backoff, and mid-retry recovery.

    Args:
        fetch: Async callable that returns the raw state dict from Portal.
        recovery: Optional async callable invoked once after *recovery_after*
            consecutive failures (e.g. restart accessibility service).
        max_retries: Total number of attempts before giving up.
        retry_delays: Per-attempt delays. If shorter than max_retries - 1,
            the last value is reused for remaining delays.
        recovery_after: Trigger *recovery* after this many failures.

    Returns:
        The raw state dict (guaranteed to contain ``a11y_tree``,
        ``phone_state``, ``device_context``).

    Raises:
        DeviceDisconnectedError: Re-raised immediately.
        Exception: After all retries are exhausted.
    """
    delays = retry_delays or _RETRY_DELAYS
    last_error: Optional[Exception] = None
    recovery_attempted = False

    is_debug = logger.isEnabledFor(logging.DEBUG)

    for attempt in range(max_retries):
        try:
            logger.debug(f"Getting state (attempt {attempt + 1}/{max_retries})")

            t0 = time.monotonic() if is_debug else 0
            combined_data = await fetch()

            if is_debug:
                elapsed = (time.monotonic() - t0) * 1000
                logger.debug(f"State fetched in {elapsed:.0f}ms")

            if "error" in combined_data:
                raise Exception(f"Portal returned error: {combined_data}")

            required_keys = ["a11y_tree", "phone_state", "device_context"]
            missing = [k for k in required_keys if k not in combined_data]
            if missing:
                raise Exception(f"Missing data in state: {', '.join(missing)}")

            return combined_data

        except DeviceDisconnectedError:
            raise
        except Exception as e:
            last_error = e
            is_last = attempt >= max_retries - 1
            delay = delays[attempt] if attempt < len(delays) else delays[-1]

            err_desc = str(e) or type(e).__name__
            suffix = f" (retrying in {delay:.0f}s)" if not is_last else ""
            logger.warning(f"get_state attempt {attempt + 1} failed: {err_desc}{suffix}")

            # Mid-retry recovery: restart the a11y service once
            if (
                not recovery_attempted
                and recovery is not None
                and attempt + 1 >= recovery_after
                and not is_last
            ):
                recovery_attempted = True
                logger.info("State retrieval failing, attempting recovery...")
                try:
                    await recovery()
                    logger.info("Recovery action completed")
                except Exception as rec_err:
                    logger.warning(f"Recovery action failed: {rec_err}")

            if not is_last:
                await asyncio.sleep(delay)

    last_desc = str(last_error) or type(last_error).__name__
    error_msg = f"Failed to get state after {max_retries} attempts: {last_desc}"
    logger.error(error_msg)
    raise Exception(error_msg) from last_error


class StateProvider:
    """Base class — subclass to support different platforms."""

    supported: set[str] = set()

    def __init__(self, driver: "DeviceDriver") -> None:
        self.driver = driver

    async def get_state(self) -> UIState:
        raise NotImplementedError


class AndroidStateProvider(StateProvider):
    """Fetches state from an Android device via ``driver.get_ui_tree()``.

    Includes retry logic with exponential backoff and mid-retry recovery
    (accessibility service restart) for robustness against intermittent
    Portal/a11y failures.
    """

    supported = {"element_index", "convert_point"}

    def __init__(
        self,
        driver: "DeviceDriver",
        tree_filter: "TreeFilter",
        tree_formatter: "TreeFormatter",
        use_normalized: bool = False,
        stealth: bool = False,
        ui_cls: "type[UIState] | None" = None,
        ui_parser_mode: str = "boost",  # "boost", "omniparser", or "accessibility"
        omniparser_backend: str = "replicate",
        omniparser_api_key: Optional[str] = None,
        omniparser_local_url: str = "http://localhost:8000",
        omniparser_box_threshold: float = 0.05,
        omniparser_a11y_threshold: int = 5,
        target_package: Optional[str] = None,
        target_recovery_attempts: int = 3,
    ) -> None:
        super().__init__(driver)
        self.tree_filter = tree_filter
        self.tree_formatter = tree_formatter
        self.use_normalized = use_normalized
        self._ui_cls = ui_cls or (StealthUIState if stealth else UIState)

        # UI parser mode: "boost" (default), "omniparser", or "accessibility"
        self.ui_parser_mode = ui_parser_mode
        self.omniparser_backend = omniparser_backend
        self.omniparser_api_key = omniparser_api_key
        self.omniparser_local_url = omniparser_local_url
        self.omniparser_box_threshold = omniparser_box_threshold
        self.omniparser_a11y_threshold = omniparser_a11y_threshold
        self.target_package = target_package
        self.target_recovery_attempts = target_recovery_attempts

        # OmniParser client (initialized lazily)
        self._omni_client = None
        self._omni_initialized = False

    async def get_state(self) -> UIState:
        await self._ensure_target_package_active()

        # Get screenshot via driver (ADB, no Portal needed)
        screenshot_bytes = await self._capture_screenshot_with_retry()

        # Get device context
        device_context = {}
        screen_width = 1080
        screen_height = 1920

        try:
            ui_tree = await self.driver.get_ui_tree()
            device_context = ui_tree.get("device_context", {})
            screen_bounds = device_context.get("screen_bounds", {})
            screen_width = screen_bounds.get("width", 1080)
            screen_height = screen_bounds.get("height", 1920)
            phone_state = ui_tree.get("phone_state", {})
            a11y_tree = ui_tree.get("a11y_tree", [])
        except Exception as e:
            logger.warning(f"get_ui_tree failed: {e}")
            phone_state = {}
            a11y_tree = []

        # Determine UI parser mode and get elements
        omni_tree = None
        omni_source = "a11y"

        if self.ui_parser_mode == "accessibility":
            # Use a11y tree only
            filtered = self.tree_filter.filter(a11y_tree, device_context) if a11y_tree else None
            logger.debug(f"Using accessibility tree ({len(a11y_tree)} elements)")

        elif self.ui_parser_mode == "omniparser":
            # Mode 2: Always use OmniParser (ignore a11y, no fallback)
            omni_tree = await self._get_omni_parser_elements(screenshot_bytes)
            if omni_tree:
                omni_source = "omni"
                logger.info(f"Using OmniParser only ({len(omni_tree)} elements)")
            filtered = None  # Will use omni_tree in formatter
            # No fallback - if OmniParser fails, let it propagate

        else:  # "boost" mode
            # Use a11y if available, otherwise OmniParser
            if a11y_tree and len(a11y_tree) >= self.omniparser_a11y_threshold:
                filtered = self.tree_filter.filter(a11y_tree, device_context)
            else:
                # A11y sparse - try OmniParser
                try:
                    omni_tree = await self._get_omni_parser_elements(screenshot_bytes)
                    if omni_tree:
                        omni_source = "omni"
                        logger.info(f"Using OmniParser boost ({len(omni_tree)} elements)")
                    filtered = None
                except Exception as e:
                    logger.warning(f"OmniParser boost failed: {e}")
                    filtered = a11y_tree
                    omni_tree = None

        self.tree_formatter.screen_width = screen_width
        self.tree_formatter.screen_height = screen_height
        self.tree_formatter.use_normalized = self.use_normalized

        formatted_text, focused_text, elements, phone_state = self.tree_formatter.format(
            filtered, phone_state, omni_tree=omni_tree
        )

        return self._ui_cls(
            elements=elements,
            formatted_text=formatted_text,
            focused_text=focused_text,
            phone_state=phone_state,
            screen_width=screen_width,
            screen_height=screen_height,
            use_normalized=self.use_normalized,
            omni_tree=omni_tree,
            omni_source=omni_source,
        )

    async def _ensure_target_package_active(self) -> None:
        """Verify target app before screenshots or OmniParser state parsing."""
        if not self.target_package:
            return

        device_id = getattr(self.driver, "_serial", None)
        if device_id is None:
            device = getattr(self.driver, "device", None)
            device_id = getattr(device, "serial", None)

        if not device_id:
            raise RuntimeError(
                "Cannot verify target app before state capture: Android device serial is unavailable"
            )

        try:
            from mobile_crawler.domain.adb_action_executor import ADBActionExecutor
        except Exception as exc:
            raise RuntimeError(
                "Cannot verify target app before state capture: ADBActionExecutor is unavailable"
            ) from exc

        adb_executor = ADBActionExecutor(device_id=device_id)
        current_package = adb_executor.get_current_package()
        if current_package == self.target_package:
            return

        logger.warning(
            "Target app mismatch before state capture (current=%s, target=%s). "
            "Relaunching target app before screenshot/OmniParser.",
            current_package,
            self.target_package,
        )

        last_error = None
        for attempt in range(1, self.target_recovery_attempts + 1):
            launch_result = adb_executor.am_start_recovery(self.target_package)
            if not launch_result.success:
                last_error = launch_result.error_message or "ADB launch command failed"

            await asyncio.sleep(0.5)
            current_package = adb_executor.get_current_package()
            if current_package == self.target_package:
                logger.info(
                    "Recovered target app before state capture on attempt %s/%s",
                    attempt,
                    self.target_recovery_attempts,
                )
                return

        detail = f"last_error={last_error}" if last_error else f"current_package={current_package}"
        raise RuntimeError(
            f"Unable to recover target app '{self.target_package}' before state capture "
            f"after {self.target_recovery_attempts} attempts ({detail})"
        )

    async def _capture_screenshot_with_retry(self) -> bytes:
        retries = 3
        delay_seconds = 1.5
        last_error: Exception | None = None

        for attempt in range(1, retries + 1):
            try:
                return await self.driver.screenshot()
            except Exception as e:
                last_error = e
                logger.warning(
                    "UI screenshot capture failed on attempt %s/%s: %s",
                    attempt,
                    retries,
                    e,
                )
                if attempt < retries:
                    await asyncio.sleep(delay_seconds)

        raise RuntimeError("Failed to capture UI screenshot after retries") from last_error

        device_context = combined_data["device_context"]
        screen_bounds = device_context.get("screen_bounds", {})
        screen_width = screen_bounds.get("width")
        screen_height = screen_bounds.get("height")

        a11y_tree = combined_data["a11y_tree"]
        phone_state = combined_data["phone_state"]

        # Determine UI parser mode and get elements
        omni_tree = None
        omni_source = "a11y"

        if self.ui_parser_mode == "accessibility":
            # Mode 3: Always use accessibility tree only
            filtered = self.tree_filter.filter(a11y_tree, device_context) if a11y_tree else None
            logger.debug(f"Using accessibility tree ({len(a11y_tree)} elements)")

        elif self.ui_parser_mode == "omniparser":
            # Mode 2: Always use OmniParser (ignore a11y, no fallback)
            omni_tree = await self._get_omni_parser_elements()
            if omni_tree:
                omni_source = "omni"
                logger.info(f"Using OmniParser only ({len(omni_tree)} elements)")
            filtered = None  # Will use omni_tree in formatter
            # No fallback - if OmniParser fails, let it propagate

        else:  # "boost" (default)
            # Mode 1: Use a11y with OmniParser fallback when sparse
            if a11y_tree and len(a11y_tree) < self.omniparser_a11y_threshold:
                # A11y tree is sparse - try OmniParser
                try:
                    omni_tree = await self._get_omni_parser_elements()
                    if omni_tree:
                        omni_source = "omni"
                        logger.info(f"Using OmniParser boost ({len(omni_tree)} elements)")
                except Exception as e:
                    logger.warning(f"OmniParser boost failed: {e}")
                    omni_tree = None

            # Use a11y if we have enough elements, or if omni failed
            if omni_tree is None:
                filtered = self.tree_filter.filter(a11y_tree, device_context) if a11y_tree else None
            else:
                filtered = None  # Will use omni_tree in formatter

        self.tree_formatter.screen_width = screen_width
        self.tree_formatter.screen_height = screen_height
        self.tree_formatter.use_normalized = self.use_normalized

        formatted_text, focused_text, elements, phone_state = self.tree_formatter.format(
            filtered, phone_state, omni_tree=omni_tree
        )

        return self._ui_cls(
            elements=elements,
            formatted_text=formatted_text,
            focused_text=focused_text,
            phone_state=phone_state,
            screen_width=screen_width,
            screen_height=screen_height,
            use_normalized=self.use_normalized,
            omni_tree=omni_tree,
            omni_source=omni_source,
        )

    async def _get_omni_parser_elements(
        self, screenshot_bytes: bytes = None
    ) -> List[Dict[str, Any]]:
        """Get UI elements using OmniParser vision model."""
        if not self._omni_initialized:
            self._init_omni_parser()
            self._omni_initialized = True

        if not self._omni_client:
            return []

        # Use provided screenshot or take new one
        if screenshot_bytes is None:
            screenshot_bytes = await self.driver.screenshot()

        # Parse with OmniParser
        return self._omni_client.parse(screenshot_bytes)

    def _init_omni_parser(self) -> None:
        """Initialize OmniParser client."""
        import os

        try:
            from mobile_crawler.domain.crawler_agent.tools.omniparser_client import create_omni_parser_client

            # Use provided API key, or fall back to environment variable
            api_key = self.omniparser_api_key or os.environ.get("REPLICATE_API_KEY", "")

            logger.debug(
                f"Initializing OmniParser: backend={self.omniparser_backend}, "
                f"omniparser_api_key={bool(self.omniparser_api_key)}, "
                f"env_REPLICATE_API_KEY={bool(os.environ.get('REPLICATE_API_KEY'))}, "
                f"final_api_key={bool(api_key)}"
            )
            self._omni_client = create_omni_parser_client(
                backend=self.omniparser_backend,
                api_key=api_key,
                local_url=self.omniparser_local_url,
                box_threshold=self.omniparser_box_threshold,
            )
        except Exception as e:
            logger.warning(f"Failed to initialize OmniParser: {e}")
            self._omni_client = None
