"""Device context capture module for recording package/activity state.

Provides the DeviceContext dataclass and DeviceContextCapture class for
capturing which app and activity is currently active on the device at
each step of a crawl.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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

        # Default to empty strings if ADB returns None (device offline, etc.)
        package = package or ""
        activity = activity or ""

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