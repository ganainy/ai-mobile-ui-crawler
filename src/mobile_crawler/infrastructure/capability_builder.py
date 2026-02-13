"""Capability builder for Appium UiAutomator2 options."""

from typing import Optional, Dict, Any
from appium.options.android import UiAutomator2Options


class CapabilityBuilder:
    """Builder for Appium UiAutomator2 capabilities."""

    def __init__(self):
        """Initialize with default capabilities."""
        self._options = UiAutomator2Options()

        # Set defaults
        self._options.platform_name = 'Android'
        self._options.automation_name = 'UiAutomator2'
        self._options.no_reset = True
        self._options.full_reset = False
        self._options.new_command_timeout = 300  # 5 minutes

    def device_name(self, device_name: str) -> 'CapabilityBuilder':
        """Set device name.

        Args:
            device_name: Android device identifier

        Returns:
            Self for method chaining
        """
        self._options.device_name = device_name
        return self

    def app_package(self, package: str) -> 'CapabilityBuilder':
        """Set app package to launch.

        Args:
            package: Android app package name

        Returns:
            Self for method chaining
        """
        self._options.app_package = package
        return self

    def app_activity(self, activity: str) -> 'CapabilityBuilder':
        """Set app activity to launch.

        Args:
            activity: Android app activity name

        Returns:
            Self for method chaining
        """
    def app_activity(self, activity: str) -> 'CapabilityBuilder':
        """Set app activity to launch.

        Args:
            activity: Android app activity name

        Returns:
            Self for method chaining
        """
        self._options.app_activity = activity
        return self

    def app_wait_timeout(self, timeout: int) -> 'CapabilityBuilder':
        """Set app wait timeout in milliseconds.

        Args:
            timeout: Timeout in milliseconds

        Returns:
            Self for method chaining
        """
        self._options.app_wait_timeout = timeout
        return self

    def device_ready_timeout(self, timeout: int) -> 'CapabilityBuilder':
        """Set device ready timeout in milliseconds.

        Args:
            timeout: Timeout in milliseconds

        Returns:
            Self for method chaining
        """
        self._options.device_ready_timeout = timeout
        return self

    def android_device_ready_timeout(self, timeout: int) -> 'CapabilityBuilder':
        """Set Android device ready timeout in milliseconds.

        Args:
            timeout: Timeout in milliseconds

        Returns:
            Self for method chaining
        """
        self._options.android_device_ready_timeout = timeout
        return self

    def app_wait_activity(self, activity: str) -> 'CapabilityBuilder':
        """Set activity to wait for after app launch.

        Args:
            activity: Activity name to wait for

        Returns:
            Self for method chaining
        """
        self._options.app_wait_activity = activity
        return self

    def no_reset(self, no_reset: bool = True) -> 'CapabilityBuilder':
        """Set whether to reset app state between sessions.

        Args:
            no_reset: If True, don't reset app state

        Returns:
            Self for method chaining
        """
        self._options.no_reset = no_reset
        return self

    def full_reset(self, full_reset: bool = True) -> 'CapabilityBuilder':
        """Set whether to perform full reset.

        Args:
            full_reset: If True, perform full reset

        Returns:
            Self for method chaining
        """
        self._options.full_reset = full_reset
        return self

    def new_command_timeout(self, timeout: int) -> 'CapabilityBuilder':
        """Set new command timeout in seconds.

        Args:
            timeout: Timeout in seconds

        Returns:
            Self for method chaining
        """
        self._options.new_command_timeout = timeout
        return self

    def auto_grant_permissions(self, auto_grant: bool = True) -> 'CapabilityBuilder':
        """Set whether to auto-grant permissions.

        Args:
            auto_grant: If True, auto-grant permissions

        Returns:
            Self for method chaining
        """
        self._options.auto_grant_permissions = auto_grant
        return self

    def ignore_unimportant_views(self, ignore: bool = True) -> 'CapabilityBuilder':
        """Set whether to ignore unimportant views.

        Args:
            ignore: If True, ignore unimportant views

        Returns:
            Self for method chaining
        """
        self._options.ignore_unimportant_views = ignore
        return self

    def disable_window_animation(self, disable: bool = True) -> 'CapabilityBuilder':
        """Set whether to disable window animations.

        Args:
            disable: If True, disable window animations

        Returns:
            Self for method chaining
        """
        self._options.disable_window_animation = disable
        return self

    def custom_capability(self, key: str, value: Any) -> 'CapabilityBuilder':
        """Add a custom capability.

        Args:
            key: Capability key
            value: Capability value

        Returns:
            Self for method chaining
        """
        setattr(self._options, key, value)
        return self

    def build(self) -> UiAutomator2Options:
        """Build the UiAutomator2Options instance.

        Returns:
            Configured UiAutomator2Options
        """
        return self._options

    @classmethod
    def for_device(cls, device_id: str) -> 'CapabilityBuilder':
        """Create a builder pre-configured for a specific device.

        Args:
            device_id: Android device identifier

        Returns:
            CapabilityBuilder instance
        """
        return cls().device_name(device_id)

    @classmethod
    def for_app(cls, device_id: str, package: str, activity: Optional[str] = None) -> 'CapabilityBuilder':
        """Create a builder pre-configured for a specific app.

        Args:
            device_id: Android device identifier
            package: App package name
            activity: App activity name (optional)

        Returns:
            CapabilityBuilder instance
        """
        builder = cls().device_name(device_id).app_package(package)
        if activity:
            builder.app_activity(activity)
        return builder