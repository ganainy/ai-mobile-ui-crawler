"""Appium driver wrapper with session management and error handling."""

import time
from typing import Optional, Dict, Any
from appium import webdriver
from appium.webdriver.webdriver import WebDriver
from appium.options.android import UiAutomator2Options

from mobile_crawler.config import get_config


class AppiumDriverError(Exception):
    """Base exception for Appium driver errors."""
    pass


class SessionLostError(AppiumDriverError):
    """Raised when the Appium session is lost."""
    pass


class AppiumDriver:
    """Wrapper around Appium WebDriver with session management and auto-reconnection."""

    def __init__(self, device_id: str, app_package: Optional[str] = None):
        """Initialize Appium driver.

        Args:
            device_id: Android device ID (e.g., 'emulator-5554')
            app_package: Package name of the app to launch (optional)
        """
        self.device_id = device_id
        self.app_package = app_package
        self._driver: Optional[WebDriver] = None
        self._session_start_time: Optional[float] = None

        # Get configuration
        config = get_config()
        self.appium_url = config.get('appium_url', 'http://localhost:4723')
        self.connection_timeout = config.get('appium_connection_timeout', 30)
        self.implicit_wait = config.get('appium_implicit_wait', 10)

    def connect(self) -> WebDriver:
        """Establish connection to Appium server and create session.

        Returns:
            Appium WebDriver instance

        Raises:
            AppiumDriverError: If connection fails
        """
        try:
            # Build capabilities
            options = UiAutomator2Options()
            options.platform_name = 'Android'
            options.device_name = self.device_id
            options.automation_name = 'UiAutomator2'
            options.no_reset = True
            options.full_reset = False
            options.new_command_timeout = 300  # 5 minutes

            if self.app_package:
                options.app_package = self.app_package
                options.app_activity = self._get_launch_activity()

            # Connect to Appium server
            self._driver = webdriver.Remote(
                command_executor=self.appium_url,
                options=options
            )

            # Configure timeouts
            self._driver.implicitly_wait(self.implicit_wait)

            self._session_start_time = time.time()
            return self._driver

        except Exception as e:
            raise AppiumDriverError(f"Failed to connect to Appium: {e}") from e

    def disconnect(self):
        """Cleanly disconnect from Appium server."""
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                # Ignore errors during cleanup
                pass
            finally:
                self._driver = None
                self._session_start_time = None

    def get_driver(self) -> WebDriver:
        """Get the underlying Appium WebDriver instance.

        Returns:
            Appium WebDriver instance

        Raises:
            SessionLostError: If no active session
        """
        if not self._driver:
            raise SessionLostError("No active Appium session")
        return self._driver

    def is_connected(self) -> bool:
        """Check if driver has an active session.

        Returns:
            True if connected, False otherwise
        """
        if not self._driver:
            return False

        try:
            # Test connection by getting current activity
            self._driver.current_activity
            return True
        except Exception:
            # Session is dead
            self._driver = None
            return False

    def reconnect(self) -> WebDriver:
        """Reconnect to Appium server if session was lost.

        Returns:
            New Appium WebDriver instance

        Raises:
            AppiumDriverError: If reconnection fails
        """
        self.disconnect()
        return self.connect()

    def ensure_connected(self) -> WebDriver:
        """Ensure we have an active connection, reconnecting if necessary.

        Returns:
            Appium WebDriver instance
        """
        if not self.is_connected():
            return self.reconnect()
        return self._driver

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session.

        Returns:
            Dictionary with session information
        """
        info = {
            'device_id': self.device_id,
            'app_package': self.app_package,
            'connected': self.is_connected(),
            'session_duration': None,
        }

        if self._session_start_time:
            info['session_duration'] = time.time() - self._session_start_time

        if self._driver:
            try:
                info.update({
                    'current_activity': self._driver.current_activity,
                    'current_package': self._driver.current_package,
                    'device_time': self._driver.device_time,
                })
            except Exception:
                # Ignore errors when getting session info
                pass

        return info

    def _get_launch_activity(self) -> str:
        """Get the launch activity for the app package.

        Returns:
            Launch activity name

        Note:
            This is a simplified implementation. In a real scenario,
            you might need to query the Android manifest or use
            package manager to determine the correct launch activity.
        """
        # For now, return a common launcher activity
        # This should be made configurable or auto-detected
        return f"{self.app_package}.MainActivity"

    def __enter__(self):
        """Context manager entry."""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()