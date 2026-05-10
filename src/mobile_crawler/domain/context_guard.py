"""Device context capture and UI dump validation module for crawl step guardrails.

Provides:
- DeviceContext / DeviceContextCapture for app-switch detection (Plan 01)
- UIDumpValidator / UIDumpValidationResult for UI dump validation gate (Plan 02)
- StepSkipReason enum for skip reason tracking (Plan 02+)
- AppSwitchRecovery / RecoveryAttempt for app-switch recovery loop (Plan 03)
"""

import enum
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, List, Optional, Tuple

from mobile_crawler.domain.adb_action_executor import ADBActionExecutor

logger = logging.getLogger(__name__)


@dataclass
class DeviceContext:
    """Snapshot of the device's active app context at a point in time."""

    package: str
    activity: str
    is_target_app: bool
    captured_at: datetime


class DeviceContextCapture:
    """Captures device context (package/activity) for app-switch detection.

    Takes a target package name and ADB executor, provides async capture
    of current device context with comparison against the expected target app.
    """

    def __init__(self, target_package: str, adb_executor: ADBActionExecutor):
        """Initialize context capture.

        Args:
            target_package: The expected app package (e.g., 'com.example.app').
            adb_executor: ADBActionExecutor instance for running device commands.
        """
        self.target_package = target_package
        self.adb_executor = adb_executor

    async def capture(self) -> DeviceContext:
        """Capture the current device context.

        Queries ADB for the current package and activity, compares against
        the target package to determine if we're still in the expected app.

        Returns:
            DeviceContext with package, activity, is_target_app flag, and timestamp.
        """
        package = self.adb_executor.get_current_package()
        activity = self.adb_executor.get_current_activity()

        activity = activity or ""

        if not package:
            # ADB returned None - transient state during Activity transitions.
            # Don't treat this as a confirmed app switch; let the next step verify.
            return DeviceContext(
                package="",
                activity=activity,
                is_target_app=True,
                captured_at=datetime.now(),
            )

        is_target_app = package == self.target_package if self.target_package else False

        return DeviceContext(
            package=package,
            activity=activity,
            is_target_app=is_target_app,
            captured_at=datetime.now(),
        )

    def get_context_dict(self, ctx: DeviceContext) -> dict:
        """Convert a DeviceContext to a dict suitable for persistence.

        Args:
            ctx: DeviceContext to convert.

        Returns:
            Dict with current_package and current_activity keys.
        """
        return {
            "current_package": ctx.package,
            "current_activity": ctx.activity,
        }


class StepSkipReason(enum.Enum):
    """Reasons a crawl step may be skipped instead of proceeding to DECIDE/EXECUTE.

    Used by both the UI dump validation gate (INVALID_UI_DUMP) and the
    context pre-check (TARGET_APP_MISMATCH) to persist skip metadata in
    step phase transitions.
    """

    TARGET_APP_MISMATCH = "target_app_mismatch"
    INVALID_UI_DUMP = "invalid_ui_dump"


@dataclass
class UIDumpValidationResult:
    """Result of validating a UI dump before the decision layer processes it.

    Per D-03: UI dumps must be both parseable and non-empty before reaching
    the AI decision layer. Invalid dumps are retried once (D-04) and then
    the step is marked SKIPPED — the run never aborts on a bad dump.
    """

    is_valid: bool
    is_parseable: bool
    element_count: int
    error: Optional[str] = None


class UIDumpValidator:
    """Validates UI tree dumps before the decision layer processes them.

    Implements D-03 (parseable AND non-empty) and D-04 (retry once, then skip).
    Never raises exceptions — always returns a UIDumpValidationResult. Invalid
    UI data should cause the step to be skipped, not the run to abort.
    """

    def validate(self, ui_data: Any) -> UIDumpValidationResult:
        """Validate raw UI data for parseability and non-emptiness.

        Accepts lists (a11y tree), dicts (state with a11y_tree key), XML strings,
        or None. Returns a result indicating whether the data is safe for the
        decision layer.

        Args:
            ui_data: Raw UI data from DroidRun state. Can be a list of a11y
                elements, a dict with an 'a11y_tree' or 'elements' key, an XML
                string, or None/empty values indicating a failed dump.

        Returns:
            UIDumpValidationResult with is_valid, is_parseable, element_count,
            and optional error description.
        """
        # None or falsy — not parseable at all
        if ui_data is None:
            return UIDumpValidationResult(
                is_valid=False,
                is_parseable=False,
                element_count=0,
                error="ui_data_is_none",
            )

        # String — try XML parsing
        if isinstance(ui_data, str):
            return self._validate_xml(ui_data)

        # List — check it's iterable and has elements
        if isinstance(ui_data, list):
            if len(ui_data) == 0:
                return UIDumpValidationResult(
                    is_valid=False,
                    is_parseable=True,
                    element_count=0,
                    error="empty_ui_dump",
                )
            return UIDumpValidationResult(
                is_valid=True,
                is_parseable=True,
                element_count=len(ui_data),
            )

        # Dict — look for a11y_tree or elements key
        if isinstance(ui_data, dict):
            # Try a11y_tree first (DroidRun convention)
            a11y = ui_data.get("a11y_tree")
            if a11y is not None:
                return self.validate(a11y)

            # Try elements key (alternate convention)
            elements = ui_data.get("elements")
            if elements is not None:
                return self.validate(elements)

            # Dict without recognizable key — treat as single element if non-empty
            if len(ui_data) > 0:
                return UIDumpValidationResult(
                    is_valid=True,
                    is_parseable=True,
                    element_count=1,
                )
            return UIDumpValidationResult(
                is_valid=False,
                is_parseable=True,
                element_count=0,
                error="empty_ui_dump",
            )

        # Any other type — check if it's iterable
        try:
            count = sum(1 for _ in ui_data)
            if count == 0:
                return UIDumpValidationResult(
                    is_valid=False,
                    is_parseable=True,
                    element_count=0,
                    error="empty_ui_dump",
                )
            return UIDumpValidationResult(
                is_valid=True,
                is_parseable=True,
                element_count=count,
            )
        except TypeError:
            return UIDumpValidationResult(
                is_valid=False,
                is_parseable=False,
                element_count=0,
                error="ui_data_unparseable_type",
            )

    def _validate_xml(self, xml_string: str) -> UIDumpValidationResult:
        """Validate an XML string UI dump.

        Empty string is treated as not parseable. Malformed XML returns
        is_parseable=False. Valid XML with no child elements returns
        is_valid=False with element_count=0.
        """
        if not xml_string.strip():
            return UIDumpValidationResult(
                is_valid=False,
                is_parseable=False,
                element_count=0,
                error="empty_xml_string",
            )

        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            return UIDumpValidationResult(
                is_valid=False,
                is_parseable=False,
                element_count=0,
                error=f"xml_parse_error: {e}",
            )

        # Count child elements (direct children of root)
        child_count = len(root)
        if child_count == 0:
            return UIDumpValidationResult(
                is_valid=False,
                is_parseable=True,
                element_count=0,
                error="empty_ui_dump",
            )

        return UIDumpValidationResult(
            is_valid=True,
            is_parseable=True,
            element_count=child_count,
        )

    async def validate_ui_dump_with_retry(
        self,
        ui_data_getter: Callable[[], Awaitable[Any]],
        max_retries: int = 1,
    ) -> UIDumpValidationResult:
        """Validate UI dump with one retry for transient failures (per D-04).

        Calls ui_data_getter to obtain fresh data, validates it, and if
        invalid with retries remaining, calls the getter again (one retry
        for transient failures like stale ADB state). If still invalid
        after retry, returns the invalid result. Never raises.

        Args:
            ui_data_getter: Callable that returns fresh UI data when invoked.
            max_retries: Number of retry attempts. Defaults to 1 per D-04.

        Returns:
            UIDumpValidationResult for the final validation attempt.
        """
        result = self.validate(await ui_data_getter())

        if result.is_valid:
            return result

        retries = 0
        while retries < max_retries and not result.is_valid:
            logger.info(
                f"UI dump validation failed ({result.error}), "
                f"retrying ({retries + 1}/{max_retries})"
            )
            result = self.validate(await ui_data_getter())
            retries += 1

        if not result.is_valid:
            logger.warning(
                f"UI dump validation still invalid after {max_retries} "
                f"retries: {result.error}"
            )

        return result


@dataclass
class RecoveryAttempt:
    """Record of a single app-switch recovery attempt."""

    attempt_number: int
    success: bool
    package_before: str
    package_after: str
    duration_ms: float


class AppSwitchRecovery:
    """Detects app switches and recovers by relaunching to the target app.

    Per D-06: Aborts after 3 consecutive failed recovery attempts.
    Per D-05: Uses am start with launcher activity for recovery.
    Per D-07: Always relaunches to main launcher activity, never deep activity.
    """

    MAX_CONSECUTIVE_FAILURES = 3

    def __init__(
        self,
        target_package: str,
        adb_executor: ADBActionExecutor,
        context_capture: DeviceContextCapture,
    ):
        """Initialize app-switch recovery.

        Args:
            target_package: The expected app package name.
            adb_executor: ADBActionExecutor instance for running am start recovery.
            context_capture: DeviceContextCapture for verifying recovery success.
        """
        self.target_package = target_package
        self.adb_executor = adb_executor
        self.context_capture = context_capture
        self._consecutive_failures = 0
        self._total_recoveries = 0

    async def detect_and_recover(self) -> Tuple[bool, List[RecoveryAttempt]]:
        """Detect app switch and attempt recovery. Returns (recovered, attempts).

        If recovered=True, the app is back on target.
        If recovered=False, MAX_CONSECUTIVE_FAILURES reached — caller should abort.

        Returns:
            Tuple of (recovered: bool, attempts: list of RecoveryAttempt).
        """
        attempts: List[RecoveryAttempt] = []

        for attempt_num in range(1, self.MAX_CONSECUTIVE_FAILURES + 1):
            # Try recovery via am start
            result = self.adb_executor.am_start_recovery(self.target_package)

            # Re-capture context to verify recovery
            new_ctx = await self.context_capture.capture()

            attempt = RecoveryAttempt(
                attempt_number=attempt_num,
                success=new_ctx.is_target_app,
                package_before="",  # filled by caller if needed
                package_after=new_ctx.package,
                duration_ms=result.duration_ms,
            )
            attempts.append(attempt)

            if new_ctx.is_target_app:
                self._consecutive_failures = 0
                self._total_recoveries += 1
                logger.info(
                    f"App switch recovery succeeded on attempt {attempt_num} "
                    f"(package: {new_ctx.package})"
                )
                return True, attempts

            self._consecutive_failures += 1
            logger.warning(
                f"App switch recovery attempt {attempt_num} failed: "
                f"package_after={new_ctx.package}, expected={self.target_package}"
            )

        # All attempts failed — signal abort
        logger.error(
            f"App switch recovery failed after {len(attempts)} attempts — aborting"
        )
        return False, attempts

    def should_abort(self) -> bool:
        """Check if consecutive failures warrant run abort."""
        return self._consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES
