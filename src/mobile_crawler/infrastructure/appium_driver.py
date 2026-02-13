"""Appium driver wrapper with session management and error handling."""

import subprocess
import time
import logging
from typing import Optional, Dict, Any, Tuple
from appium import webdriver
from appium.webdriver.webdriver import WebDriver
from appium.options.android import UiAutomator2Options
from selenium.common.exceptions import WebDriverException

from mobile_crawler.config import get_config

logger = logging.getLogger(__name__)


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

    def restart_uiautomator2(self, delay_seconds: float = 3.0) -> WebDriver:
        """
        Restart the UiAutomator2 session by reconnecting.
        
        Args:
            delay_seconds: Seconds to wait after disconnect before reconnecting.
            
        Returns:
            New Appium WebDriver instance
        """
        logger.info(f"Restarting UiAutomator2 (waiting {delay_seconds}s)...")
        self.disconnect()
        time.sleep(delay_seconds)
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

    # Gesture Methods

    def tap_at(self, x: int, y: int, duration: float = 0.1) -> bool:
        """Tap at specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            duration: Duration of tap in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            driver = self.get_driver()
            
            from selenium.webdriver.common.actions.action_builder import ActionBuilder
            from selenium.webdriver.common.actions.pointer_input import PointerInput
            from selenium.webdriver.common.actions import interaction
            
            # Create a touch pointer
            pointer = PointerInput(interaction.POINTER_TOUCH, "finger")
            action_builder = ActionBuilder(driver, mouse=pointer, duration=100)
            
            # Build tap sequence: move to location, press, release
            action_builder.pointer_action.move_to_location(x, y)
            action_builder.pointer_action.pointer_down()
            action_builder.pointer_action.pause(0.05)  # Short pause for tap
            action_builder.pointer_action.pointer_up()
            
            # Perform action
            action_builder.perform()
            
            time.sleep(duration)
            logger.info(f"Tapped at coordinates ({x}, {y})")
            return True
        except (WebDriverException, SessionLostError) as e:
            logger.error(f"Failed to tap at ({x}, {y}): {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error tapping at ({x}, {y}): {e}")
            return False

    def double_tap_at(self, x: int, y: int, interval: float = 0.1) -> bool:
        """Double tap at specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            interval: Time between taps in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            driver = self.get_driver()
            
            from selenium.webdriver.common.actions.action_builder import ActionBuilder
            from selenium.webdriver.common.actions.pointer_input import PointerInput
            from selenium.webdriver.common.actions import interaction
            
            # Create a touch pointer
            pointer = PointerInput(interaction.POINTER_TOUCH, "finger")
            action_builder = ActionBuilder(driver, mouse=pointer)
            
            # First tap
            action_builder.pointer_action.move_to_location(x, y)
            action_builder.pointer_action.pointer_down()
            action_builder.pointer_action.pause(0.05)
            action_builder.pointer_action.pointer_up()
            
            # Short pause between taps
            action_builder.pointer_action.pause(interval)
            
            # Second tap
            action_builder.pointer_action.move_to_location(x, y)
            action_builder.pointer_action.pointer_down()
            action_builder.pointer_action.pause(0.05)
            action_builder.pointer_action.pointer_up()
            
            # Perform action
            action_builder.perform()
            
            logger.info(f"Double tapped at coordinates ({x}, {y})")
            return True
        except (WebDriverException, SessionLostError) as e:
            logger.error(f"Failed to double tap at ({x}, {y}): {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error double tapping at ({x}, {y}): {e}")
            return False

    def long_press_at(self, x: int, y: int, duration: float = 2.0) -> bool:
        """Long press at specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            duration: Duration of press in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            driver = self.get_driver()
            
            from selenium.webdriver.common.actions.action_builder import ActionBuilder
            from selenium.webdriver.common.actions.pointer_input import PointerInput
            from selenium.webdriver.common.actions import interaction
            
            # Create a touch pointer
            pointer = PointerInput(interaction.POINTER_TOUCH, "finger")
            action_builder = ActionBuilder(driver, mouse=pointer)
            
            # Build long press sequence: move, press, hold, release
            action_builder.pointer_action.move_to_location(x, y)
            action_builder.pointer_action.pointer_down()
            action_builder.pointer_action.pause(duration)  # Hold for specified duration
            action_builder.pointer_action.pointer_up()
            action_builder.perform()
            
            logger.info(f"Long pressed at coordinates ({x}, {y}) for {duration}s")
            return True
        except (WebDriverException, SessionLostError) as e:
            logger.error(f"Failed to long press at ({x}, {y}): {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error long pressing at ({x}, {y}): {e}")
            return False

    def input_text(self, element, text: str, clear: bool = True) -> bool:
        """Input text into an element.

        Args:
            element: Appium WebElement
            text: Text to input
            clear: Whether to clear the field before typing

        Returns:
            True if successful, False otherwise
        """
        try:
            if clear:
                element.clear()
            element.send_keys(text)
            logger.info(f"Input text: {text}")
            return True
        except (WebDriverException, SessionLostError) as e:
            logger.error(f"Failed to input text: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error inputting text: {e}")
            return False

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int,
              duration: float = 0.5) -> bool:
        """Swipe from one point to another.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration: Duration of swipe in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            driver = self.get_driver()
            
            from selenium.webdriver.common.actions.action_builder import ActionBuilder
            from selenium.webdriver.common.actions.pointer_input import PointerInput
            from selenium.webdriver.common.actions import interaction
            
            pointer = PointerInput(interaction.POINTER_TOUCH, "finger")
            actions = ActionBuilder(driver, mouse=pointer)
            
            # Move to start position (absolute coordinates)
            actions.pointer_action.move_to_location(start_x, start_y)
            actions.pointer_action.pointer_down()
            # Pause briefly before moving
            actions.pointer_action.pause(0.05)
            # Move to end position (absolute coordinates)
            actions.pointer_action.move_to_location(end_x, end_y)
            actions.pointer_action.pointer_up()
            actions.perform()

            # Add delay for swipe to complete
            time.sleep(duration)
            logger.info(f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            return True
        except (WebDriverException, SessionLostError) as e:
            logger.error(f"Failed to swipe: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error swiping: {e}")
            return False

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int,
             duration: float = 1.0) -> bool:
        """Drag from one point to another.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration: Duration of drag in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            driver = self.get_driver()
            
            from selenium.webdriver.common.actions.action_builder import ActionBuilder
            from selenium.webdriver.common.actions.pointer_input import PointerInput
            from selenium.webdriver.common.actions import interaction
            
            pointer = PointerInput(interaction.POINTER_TOUCH, "finger")
            actions = ActionBuilder(driver, mouse=pointer)
            
            # Move to start position (absolute coordinates)
            actions.pointer_action.move_to_location(start_x, start_y)
            actions.pointer_action.pointer_down()
            actions.pointer_action.pause(0.05)
            # Move to end position (absolute coordinates)
            actions.pointer_action.move_to_location(end_x, end_y)
            actions.pointer_action.pointer_up()
            actions.perform()
            
            time.sleep(duration)
            logger.info(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            return True
        except (WebDriverException, SessionLostError) as e:
            logger.error(f"Failed to drag from ({start_x}, {start_y}) to ({end_x}, {end_y}): {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error dragging: {e}")
            return False

    def back(self) -> bool:
        """Press the back button.

        Returns:
            True if successful, False otherwise
        """
        try:
            driver = self.get_driver()
            driver.back()
            logger.info("Pressed back button")
            return True
        except (WebDriverException, SessionLostError) as e:
            logger.error(f"Failed to press back: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error pressing back: {e}")
            return False

    def hide_keyboard(self) -> bool:
        """Hide the keyboard if it is visible.

        Returns:
            True if successful (keyboard hidden or not visible), False otherwise
        """
        try:
            driver = self.get_driver()
            if driver.is_keyboard_shown():
                driver.hide_keyboard()
                logger.info("Hidden keyboard")
            return True
        except (WebDriverException, SessionLostError) as e:
            # Often throws if soft keyboard is not present, which is fine
            logger.debug(f"Failed to hide keyboard (may not be visible): {e}")
            return True
        except Exception as e:
            logger.error(f"Unexpected error hiding keyboard: {e}")
            return False

    def __enter__(self):
        """Context manager entry."""
        return self.connect()

    def start_recording_screen(self) -> bool:
        """Start screen recording using Appium's built-in recording.

        Returns:
            True if recording started successfully, False otherwise
        """
        logger.debug("[DEBUG] AppiumDriver.start_recording_screen() called")
        
        try:
            driver = self.get_driver()
            # self.get_driver() raises SessionLostError if no driver
            
            logger.debug(f"[DEBUG] Appium driver available, session_id: {getattr(driver, 'session_id', 'N/A')}")
            logger.debug("[DEBUG] Calling driver.start_recording_screen()...")
            
            driver.start_recording_screen()
            logger.info("Screen recording started")
            logger.debug("[DEBUG] driver.start_recording_screen() completed successfully")
            return True
        except SessionLostError:
            raise  # Re-raise session lost
        except WebDriverException as e:
            # Check if it's the benign "No such process" error from cleanup
            if "No such process" in str(e):
                logger.info("Screen recording started (ignoring 'No such process' cleanup error)")
                logger.debug("[DEBUG] Treating 'No such process' as success")
                return True
            error_msg = f"Failed to start screen recording: {e}"
            logger.error(error_msg)
            raise AppiumDriverError(error_msg) from e
        except AttributeError as e:
            error_msg = f"start_recording_screen method not available: {e}"
            logger.error(error_msg)
            raise AppiumDriverError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error starting screen recording: {e}"
            logger.error(error_msg, exc_info=True)
            raise AppiumDriverError(error_msg) from e

    def stop_recording_screen(self) -> Optional[str]:
        """Stop screen recording and get base64 encoded video data.

        Returns:
            Base64 encoded video data as string, or None if failed
        """
        logger.debug("[DEBUG] AppiumDriver.stop_recording_screen() called")
        
        try:
            driver = self.get_driver()
            
            logger.debug(f"[DEBUG] Appium driver available, session_id: {getattr(driver, 'session_id', 'N/A')}")
            logger.debug("[DEBUG] Calling driver.stop_recording_screen()...")
            
            video_base64 = driver.stop_recording_screen()
            
            if video_base64:
                logger.info("Screen recording stopped")
                logger.debug(f"[DEBUG] Video data received, length: {len(video_base64) if video_base64 else 0} characters")
            else:
                logger.warning("[DEBUG] stop_recording_screen() returned None or empty string")
            
            return video_base64
        except SessionLostError:
            raise
        except WebDriverException as e:
            error_msg = f"Failed to stop screen recording: {e}"
            logger.error(error_msg)
            raise AppiumDriverError(error_msg) from e
        except AttributeError as e:
            error_msg = f"stop_recording_screen method not available: {e}"
            logger.error(error_msg)
            raise AppiumDriverError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error stopping screen recording: {e}"
            logger.error(error_msg, exc_info=True)
            raise AppiumDriverError(error_msg) from e

    def __enter__(self):
        """Context manager entry."""
        return self.connect()