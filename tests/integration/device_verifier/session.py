"""Appium session helper for device verification tests."""

import subprocess
import time
from typing import Optional, Dict, Any, Tuple

from appium import webdriver
from appium.webdriver.webdriver import WebDriver
from appium.options.android import UiAutomator2Options


class SessionError(Exception):
    """Raised when session creation or management fails."""
    pass


class DeviceSession:
    """Helper class to manage Appium session connection to a device.

    This class provides methods to connect to a device, manage the session,
    and retrieve device information for verification testing.
    """

    def __init__(
        self,
        device_id: Optional[str] = None,
        app_package: Optional[str] = None,
        appium_url: str = "http://localhost:4723",
        connection_timeout: int = 30,
    ):
        """Initialize device session helper.

        Args:
            device_id: Android device ID (e.g., 'emulator-5554'). If None, auto-detects.
            app_package: Package name of the app to launch (optional)
            appium_url: URL of the Appium server
            connection_timeout: Timeout in seconds for connection
        """
        self.device_id = device_id or self._detect_device()
        self.app_package = app_package
        self.appium_url = appium_url
        self.connection_timeout = connection_timeout
        self._driver: Optional[WebDriver] = None
        self._session_start_time: Optional[float] = None

    def _detect_device(self) -> str:
        """Auto-detect the connected Android device.

        Returns:
            Device ID of the first connected device

        Raises:
            SessionError: If no device is found
        """
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise SessionError(f"ADB command failed: {result.stderr}")

            lines = result.stdout.strip().split('\n')
            # Skip header line, find first device
            for line in lines[1:]:
                if line.strip() and '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    return device_id

            raise SessionError("No connected Android device found")
        except FileNotFoundError:
            raise SessionError("ADB not found. Please ensure Android SDK is installed and in PATH.")
        except subprocess.TimeoutExpired:
            raise SessionError("ADB command timed out")

    def connect(self) -> WebDriver:
        """Establish connection to Appium server and create session.

        Returns:
            Appium WebDriver instance

        Raises:
            SessionError: If connection fails
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
                options=options,
            )

            # Configure implicit wait
            self._driver.implicitly_wait(10)

            self._session_start_time = time.time()
            return self._driver

        except Exception as e:
            raise SessionError(f"Failed to connect to Appium: {e}") from e

    def disconnect(self) -> None:
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
            SessionError: If no active session
        """
        if not self._driver:
            raise SessionError("No active Appium session")
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

    def get_device_info(self) -> Dict[str, Any]:
        """Get information about the connected device.

        Returns:
            Dictionary with device information
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
                    'platform_name': self._driver.capabilities.get('platformName'),
                    'platform_version': self._driver.capabilities.get('platformVersion'),
                    'device_name': self._driver.capabilities.get('deviceName'),
                    'automation_name': self._driver.capabilities.get('automationName'),
                    'current_activity': self._driver.current_activity,
                    'current_package': self._driver.current_package,
                    'device_time': self._driver.device_time,
                })
            except Exception:
                # Ignore errors when getting device info
                pass

        return info

    def get_screen_dimensions(self) -> Tuple[int, int]:
        """Get the screen dimensions (width, height) in pixels.
        
        Returns:
            Tuple of (width, height)
        """
        if not self._driver:
            raise SessionError("No active session to get dimensions")
            
        size = self._driver.get_window_size()
        return size['width'], size['height']

    def _get_launch_activity(self) -> Optional[str]:
        """Get the launch activity for the app package using ADB.

        Returns:
            Launch activity name or None if not found
        """
        if not self.app_package:
            return None

        try:
            # Query package manager for the launcher activity
            result = subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'cmd', 'package',
                 'resolve-activity', '--brief', '-c', 'android.intent.category.LAUNCHER',
                 self.app_package],
                capture_output=True,
                text=True,
                timeout=10,
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
                timeout=10,
            )

            if result.returncode == 0:
                # Look for the MAIN/LAUNCHER activity
                lines = result.stdout.split('\n')
                for i, line in enumerate(lines):
                    if 'android.intent.action.MAIN' in line:
                        # Look for the activity in nearby lines
                        for j in range(max(0, i-5), min(len(lines), i+5)):
                            if self.app_package in lines[j] and '/' in lines[j]:
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

    def wait_for_text(self, text: str, timeout: int = 10) -> bool:
        """Wait for specific text to appear on the screen.

        Args:
            text: Text to search for
            timeout: Timeout in seconds

        Returns:
            True if text is found within timeout, False otherwise
        """
        if not self._driver:
            return False

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Find element by text or content-desc (common in Flutter/Android)
                xpath = f"//*[contains(@text, '{text}') or contains(@content-desc, '{text}')]"
                element = self._driver.find_element("xpath", xpath)
                if element and element.is_displayed():
                    return True
            except Exception:
                # Ignore and retry
                pass
            time.sleep(1)
        
        return False

    def trigger_deep_link(self, url: str) -> bool:
        """Trigger a deep link on the device.

        Args:
            url: The deep link URL to trigger

        Returns:
            True if successful, False otherwise
        """
        if not self._driver:
            return False

        try:
            # Try Appium native deep link
            # For Android, mobile: deepLink is usually supported
            self._driver.execute_script("mobile: deepLink", {
                "url": url,
                "package": self.app_package
            })
            return True
        except Exception:
            # Fallback to ADB
            try:
                cmd = ['adb', '-s', self.device_id, 'shell', 'am', 'start', '-a', 'android.intent.action.VIEW', '-d', url]
                if self.app_package:
                    cmd.append(self.app_package)
                subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                return True
            except Exception:
                return False

    def __enter__(self):
        """Context manager entry."""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
