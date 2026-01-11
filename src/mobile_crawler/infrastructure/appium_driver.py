"""Appium driver wrapper with session management and error handling."""

import subprocess
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
                # Try to get the actual launch activity via ADB
                launch_activity = self._get_launch_activity()
                if launch_activity:
                    options.app_activity = launch_activity
                # Use wildcard to accept any activity that starts
                options.app_wait_activity = '*'

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

    def _get_launch_activity(self) -> Optional[str]:
        """Get the launch activity for the app package using ADB.

        Returns:
            Launch activity name or None if not found
        """
        if not self.app_package:
            return None
        
        try:
            # Query package manager for the launcher activity
            # Using: adb -s <device> shell cmd package resolve-activity --brief <package>
            result = subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'cmd', 'package', 
                 'resolve-activity', '--brief', '-c', 'android.intent.category.LAUNCHER', 
                 self.app_package],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                # The activity is typically on the second line in format: package/activity
                for line in lines:
                    if '/' in line:
                        parts = line.strip().split('/')
                        if len(parts) == 2:
                            return parts[1]  # Return the activity part
            
            # Fallback: try dumpsys package
            result = subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'dumpsys', 'package', self.app_package],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Look for the MAIN/LAUNCHER activity
                lines = result.stdout.split('\n')
                in_activity_resolver = False
                for i, line in enumerate(lines):
                    if 'android.intent.action.MAIN' in line:
                        # Look for the activity in nearby lines
                        for j in range(max(0, i-5), min(len(lines), i+5)):
                            if self.app_package in lines[j] and '/' in lines[j]:
                                # Extract activity from line like "pkg/activity"
                                match_line = lines[j].strip()
                                if '/' in match_line:
                                    for part in match_line.split():
                                        if '/' in part and self.app_package in part:
                                            activity = part.split('/')[1]
                                            if activity:
                                                return activity
                                            
        except Exception:
            pass
        
        return None

    def __enter__(self):
        """Context manager entry."""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()