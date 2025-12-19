"""
Core Appium helper class.

Provides W3C WebDriver client with session management and error recovery using Appium-Python-Client.
"""

import logging
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal
from urllib.parse import urlparse

from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from appium.options.android import UiAutomator2Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotInteractableException,
    InvalidSelectorException,
    WebDriverException,
)

from infrastructure.appium_error_handler import (
    AppiumError,
    SessionNotFoundError,
    ElementNotFoundError,
    GestureFailedError,
    is_session_terminated,
    validate_coordinates,
    with_retry_sync,
)
from infrastructure.capability_builder import AppiumCapabilities
from infrastructure.device_detection import Platform, DeviceInfo
from infrastructure.session_manager import SessionManager
from infrastructure.element_finder import ElementFinder, LocatorStrategy
from infrastructure.gesture_handler import GestureHandler

logger = logging.getLogger(__name__)


@dataclass
class ActionHistory:
    """Action history entry."""
    action: str
    target: str
    success: bool
    timestamp: float
    duration: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class SessionState:
    """Current session state."""
    driver: Optional[Any] = None
    current_platform: Optional[Platform] = None
    current_device: Optional[DeviceInfo] = None
    session_id: Optional[str] = None
    last_capabilities: Optional[AppiumCapabilities] = None
    last_appium_url: Optional[str] = None
    action_history: List[ActionHistory] = field(default_factory=list)


class AppiumHelper:
    """Core Appium helper for session management and device interaction."""
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        implicit_wait: int = 5000
    ):
        """
        Initialize AppiumHelper.
        
        Args:
            max_retries: Maximum retry attempts for operations
            retry_delay: Delay between retries in seconds
            implicit_wait: Implicit wait timeout in milliseconds
        """
        # Specialized components
        self.session_manager = SessionManager(max_retries, retry_delay, implicit_wait)
        self.element_finder: Optional[ElementFinder] = None
        self.gesture_handler: Optional[GestureHandler] = None
        
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.implicit_wait = implicit_wait
        self.action_history: List[ActionHistory] = []
        
        # Context tracking
        self.max_consecutive_context_failures: int = 3

    @property
    def driver(self) -> Optional[webdriver.Remote]:
        return self.session_manager.driver

    @property
    def last_capabilities(self) -> Optional[AppiumCapabilities]:
        return self.session_manager.last_capabilities

    @property
    def last_appium_url(self) -> Optional[str]:
        return self.session_manager.last_appium_url

    @property
    def target_package(self) -> Optional[str]:
        return self.session_manager.target_package

    @target_package.setter
    def target_package(self, value):
        self.session_manager.target_package = value
        if self.element_finder:
            self.element_finder.target_package = value

    @property
    def target_activity(self) -> Optional[str]:
        return self.session_manager.target_activity

    @target_activity.setter
    def target_activity(self, value):
        self.session_manager.target_activity = value

    @property
    def allowed_external_packages(self) -> List[str]:
        return self.session_manager.allowed_external_packages

    @allowed_external_packages.setter
    def allowed_external_packages(self, value):
        self.session_manager.allowed_external_packages = value

    @property
    def consecutive_context_failures(self) -> int:
        return self.session_manager.consecutive_context_failures

    @consecutive_context_failures.setter
    def consecutive_context_failures(self, value):
        self.session_manager.consecutive_context_failures = value

    @property
    def _current_implicit_wait(self) -> Optional[float]:
        return self.session_manager._current_implicit_wait

    @_current_implicit_wait.setter
    def _current_implicit_wait(self, value):
        self.session_manager._current_implicit_wait = value
    
    def initialize_driver(
        self,
        capabilities: AppiumCapabilities,
        appium_url: str = 'http://localhost:4723',
        context_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize WebDriver session and specialized components."""
        self.session_manager.initialize_driver(capabilities, appium_url, context_config)
        
        # Initialize specialized components with the new driver
        self.element_finder = ElementFinder(self.driver, self.target_package)
        self.gesture_handler = GestureHandler(self.driver)
    
    def _apply_performance_settings(self) -> None:
        """Apply performance settings (delegated)."""
        self.session_manager.apply_performance_settings()
    
    def validate_session(self) -> bool:
        """Validate if current session is still active (delegated)."""
        return self.session_manager.validate_session()
    
    def _attempt_session_recovery(self) -> bool:
        """Attempt to recover from session termination (delegated)."""
        return self.session_manager.recover_session()
    
    def safe_execute(self, operation, error_message: str = 'Operation failed'):
        """
        Safe execution wrapper with session validation and retry.
        
        Args:
            operation: Operation to execute (callable)
            error_message: Error message for failures
            
        Returns:
            Result of the operation
        """
        if not self.driver:
            raise SessionNotFoundError('No active Appium session')
        
        # Validate session before operation
        if not self.validate_session():
            raise SessionNotFoundError('Session validation failed')
        
        return with_retry_sync(
            operation,
            self.max_retries,
            self.retry_delay,
            error_message
        )
    
    def _get_locator(self, selector: str, strategy: LocatorStrategy) -> tuple:
        """Get locator tuple (delegated)."""
        if not self.element_finder:
            # Fallback if not initialized
            from appium.webdriver.common.appiumby import AppiumBy
            return (AppiumBy.ID, selector)
        return self.element_finder.get_locator(selector, strategy)
    
    def find_element(
        self,
        selector: str,
        strategy: LocatorStrategy = 'id',
        timeout_ms: int = 10000
    ) -> WebElement:
        """Find element (delegated)."""
        def _find():
            return self.element_finder.find_element(
                selector, strategy, timeout_ms, self.implicit_wait, 
                self._get_current_platform() or 'android'
            )
        return self.safe_execute(_find, f'Find element with {strategy}: {selector}')
        
        return self.safe_execute(_find, f'Find element with {strategy}: {selector}')
    
    def find_elements(
        self,
        selector: str,
        strategy: LocatorStrategy = 'id'
    ) -> List[WebElement]:
        """Find multiple elements (delegated)."""
        return self.element_finder.find_elements(selector, strategy)
    
    def tap_element(
        self,
        selector: str,
        strategy: LocatorStrategy = 'id'
    ) -> bool:
        """Tap element with fallback strategies (delegated)."""
        start_time = time.time()
        
        def _tap():
            element = self.find_element(selector, strategy)
            last_error: Optional[Exception] = None
            
            # Method 1: Standard click
            try:
                element.click()
                self._record_action('tap', selector, True, time.time() - start_time)
                return True
            except Exception as click_error:
                last_error = click_error
                logger.debug('Standard click failed, trying W3C Actions')
            
            # Method 2: W3C Actions API (delegated center and tap)
            try:
                x, y = self.gesture_handler.get_element_center(element)
                self.gesture_handler.perform_w3c_tap(x, y)
                self._record_action('tap', selector, True, time.time() - start_time)
                return True
            except Exception as w3c_error:
                last_error = w3c_error
                logger.debug('W3C Actions failed, trying mobile command')
            
            # Method 3: Mobile tap command
            try:
                x, y = self.gesture_handler.get_element_center(element)
                self.driver.execute_script('mobile: tap', {'x': x, 'y': y})
                self._record_action('tap', selector, True, time.time() - start_time)
                return True
            except Exception as mobile_error:
                last_error = mobile_error
            
            # All methods failed
            error_msg = str(last_error) if last_error else 'Unknown error'
            self._record_action('tap', selector, False, time.time() - start_time, error_msg)
            raise GestureFailedError(f'Failed to tap element after all fallback methods: {error_msg}')
        
        return self.safe_execute(_tap, f'Tap element: {selector}')
    
    def send_keys(
        self,
        selector: str,
        text: str,
        strategy: LocatorStrategy = 'id',
        clear_first: bool = True
    ) -> bool:
        """
        Send text to element with focus verification.
        
        Args:
            selector: Element selector
            text: Text to send
            strategy: Locator strategy
            clear_first: Whether to clear element before typing
            
        Returns:
            True if successful
        """
        start_time = time.time()
        
        def _send():
            # Re-find element right before each operation to avoid StaleElementReferenceException
            # This ensures we always have a fresh reference to the element
            
            # Find element and focus it
            element = self.find_element(selector, strategy)
            try:
                element.click()
            except Exception:
                logger.debug('Failed to click element before sending keys, continuing...')
            
            # Clear element if requested (re-find to avoid stale reference)
            if clear_first:
                try:
                    element = self.find_element(selector, strategy)
                    element.clear()
                except Exception:
                    logger.debug('Failed to clear element value, continuing...')
            
            # Re-find element right before send_keys to ensure fresh reference
            # This prevents StaleElementReferenceException
            element = self.find_element(selector, strategy)
            element.send_keys(text)
            
            # Hide keyboard on mobile
            try:
                self.driver.hide_keyboard()
            except Exception:
                pass  # Keyboard might not be present
            
            self._record_action('sendKeys', selector, True, time.time() - start_time)
            return True
        
        return self.safe_execute(_send, f'Send keys to element: {selector}')
    
    def perform_w3c_tap(self, x: float, y: float) -> None:
        """Perform W3C tap (delegated)."""
        self.gesture_handler.perform_w3c_tap(x, y)

    def _get_element_center(self, element: WebElement) -> tuple[float, float]:
        """Get element center (delegated)."""
        return self.gesture_handler.get_element_center(element)
    
    def _record_action(
        self,
        action: str,
        target: str,
        success: bool,
        duration: float,
        error_message: Optional[str] = None
    ) -> None:
        """
        Record action in history.
        
        Args:
            action: Action name
            target: Target identifier
            success: Whether action succeeded
            duration: Duration in seconds
            error_message: Optional error message
        """
        history_entry = ActionHistory(
            action=action,
            target=target,
            success=success,
            timestamp=time.time(),
            duration=duration,
            error_message=error_message
        )
        
        self.action_history.append(history_entry)
        
        # Keep only last 100 actions
        if len(self.action_history) > 100:
            self.action_history = self.action_history[-100:]
        
        logger.debug(
            f'Action recorded: {action} on {target}, success={success}, '
            f'duration={duration*1000:.0f}ms'
        )
    
    def get_action_history(self) -> List[ActionHistory]:
        """
        Get action history.
        
        Returns:
            List of action history entries
        """
        return list(self.action_history)
    
    def get_session_state(self) -> SessionState:
        """
        Get current session state.
        
        Returns:
            SessionState object
        """
        return SessionState(
            driver=self.driver,
            current_platform=self._get_current_platform(),
            current_device=None,  # Would need device detection logic
            session_id=self.driver.session_id if self.driver else None,
            last_capabilities=self.last_capabilities,
            last_appium_url=self.last_appium_url,
            action_history=self.get_action_history()
        )
    
    def _get_current_platform(self) -> Optional[Platform]:
        """
        Get current platform from capabilities.
        
        Returns:
            Platform or None
        """
        if self.last_capabilities:
            platform_name = self.last_capabilities.get('platformName', '').lower()
            if 'android' in platform_name:
                return 'android'
        return None
    
    def close_driver(self) -> None:
        """Close driver session (delegated)."""
        self.session_manager.close_session()
    
    def get_page_source(self) -> str:
        """
        Get page source.
        
        Returns:
            Page source XML string
        """
        def _get():
            return self.driver.page_source
        
        return self.safe_execute(_get, 'Get page source')
    
    def take_screenshot(self) -> str:
        """
        Take screenshot.
        
        Returns:
            Base64-encoded screenshot string
        """
        def _take():
            return self.driver.get_screenshot_as_base64()
        
        return self.safe_execute(_take, 'Take screenshot')
    
    def get_window_size(self) -> Dict[str, int]:
        """
        Get window size.
        
        Returns:
            Dictionary with 'width' and 'height'
        """
        def _get():
            size = self.driver.get_window_size()
            return {'width': size['width'], 'height': size['height']}
        
        return self.safe_execute(_get, 'Get window size')
    
    def get_driver(self) -> Optional[webdriver.Remote]:
        """
        Get driver instance (for advanced operations).
        
        Returns:
            WebDriver instance or None
        """
        return self.driver
    
    def get_current_package(self) -> Optional[str]:
        """
        Get current package name (Android only).
        
        Returns:
            Package name or None
        """
        if not self.driver:
            return None
        
        try:
            platform = self._get_current_platform()
            if platform != 'android':
                return None
            
            # Try Appium's get_current_package method
            try:
                package_name = self.driver.current_package
                if package_name:
                    return package_name
            except Exception:
                pass
            
            # Fallback: use mobile: shell to get current package via dumpsys
            try:
                result = self.driver.execute_script(
                    'mobile: shell',
                    {
                        'command': 'dumpsys',
                        'args': ['window', 'windows']
                    }
                )
                
                # Parse package name from dumpsys output
                if isinstance(result, str):
                    focus_match = re.search(r'mCurrentFocus.*?(\w+\.\w+(?:\.\w+)*)', result)
                    if focus_match and focus_match.group(1):
                        return focus_match.group(1)
            except Exception:
                pass
            
            return None
        except Exception as error:
            logger.debug(f'Failed to get current package: {error}')
            return None
    
    def get_current_activity(self) -> Optional[str]:
        """
        Get current activity name (Android only).
        
        Returns:
            Activity name or None
        """
        if not self.driver:
            return None
        
        try:
            platform = self._get_current_platform()
            if platform != 'android':
                return None
            
            # Try Appium's get_current_activity method
            try:
                activity = self.driver.current_activity
                if activity:
                    return activity
            except Exception:
                pass
            
            # Fallback: use mobile: shell to get current activity via dumpsys
            try:
                result = self.driver.execute_script(
                    'mobile: shell',
                    {
                        'command': 'dumpsys',
                        'args': ['window', 'windows']
                    }
                )
                
                # Parse activity from dumpsys output
                if isinstance(result, str):
                    focus_match = re.search(r'mCurrentFocus.*?(\w+\.\w+(?:\/\w+\.\w+)*)', result)
                    if focus_match and focus_match.group(1):
                        return focus_match.group(1)
            except Exception:
                pass
            
            return None
        except Exception as error:
            logger.debug(f'Failed to get current activity: {error}')
            return None
    
    def start_activity(
        self,
        app_package: str,
        app_activity: str,
        wait_after_launch: int = 5000
    ) -> bool:
        """
        Start an Android app activity.
        
        Args:
            app_package: Android app package name
            app_activity: Android app activity name
            wait_after_launch: Wait time in milliseconds after launching
            
        Returns:
            True if successful
        """
        if not self.driver:
            logger.error('Driver not initialized, cannot start activity')
            return False
        
        try:
            platform = self._get_current_platform()
            if platform != 'android':
                logger.warning('startActivity is only supported on Android')
                return False
            
            # Normalize activity name
            # Handle different activity name formats
            if app_activity.startswith('.'):
                # Relative activity name (e.g., ".MainActivity")
                full_activity = f'{app_package}{app_activity}'
            elif '/' in app_activity:
                # Full activity path (e.g., "com.example/.MainActivity")
                full_activity = app_activity
            elif '.' in app_activity:
                # Full qualified activity (e.g., "com.example.MainActivity")
                full_activity = app_activity
            else:
                # Simple activity name (e.g., "MainActivity")
                full_activity = f'{app_package}.{app_activity}'
            
            # Construct activity component for ADB
            activity_component = f'{app_package}/{full_activity}'
            
            logger.info(f'Attempting to start activity: {activity_component}')
            
            # Method 1: Try Appium's start_activity method (recommended)
            try:
                self.driver.start_activity(app_package, app_activity)
                logger.info(f'Started activity using Appium method: {app_package}/{app_activity}')
            except Exception as appium_error:
                logger.warning(f'Appium start_activity failed: {appium_error}, trying ADB fallback...')
                
                # Method 2: Try ADB shell command via subprocess (more reliable)
                try:
                    # Get device UDID from driver capabilities
                    device_udid = None
                    try:
                        if self.last_capabilities:
                            device_udid = self.last_capabilities.get('appium:udid')
                    except Exception:
                        pass
                    
                    # Build ADB command
                    adb_cmd = ['adb']
                    if device_udid:
                        adb_cmd.extend(['-s', device_udid])
                    adb_cmd.extend(['shell', 'am', 'start', '-W', '-n', activity_component])
                    
                    logger.debug(f'Executing ADB command: {" ".join(adb_cmd)}')
                    result = subprocess.run(
                        adb_cmd,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        logger.info(f'Started activity using ADB: {activity_component}')
                    else:
                        logger.error(f'ADB command failed: {result.stderr}')
                        # Try one more fallback with mobile: shell
                        raise Exception(f'ADB failed: {result.stderr}')
                        
                except Exception as adb_error:
                    logger.warning(f'ADB fallback failed: {adb_error}, trying mobile: shell...')
                    
                    # Method 3: Fallback to mobile: shell (last resort)
                    try:
                        self.driver.execute_script(
                            'mobile: shell',
                            {
                                'command': 'am',
                                'args': ['start', '-W', '-n', activity_component]
                            }
                        )
                        logger.info(f'Started activity using mobile: shell: {activity_component}')
                    except Exception as shell_error:
                        logger.error(f'All methods failed to start activity: {shell_error}')
                        return False
            
            # Wait for app to load
            if wait_after_launch > 0:
                logger.debug(f'Waiting {wait_after_launch}ms for app to fully load...')
                time.sleep(wait_after_launch / 1000.0)
            
            # Verify the app actually launched
            try:
                current_package = self.get_current_package()
                if current_package == app_package:
                    logger.info(f'Verified app launched successfully: {app_package}')
                    return True
                else:
                    logger.warning(
                        f'App may not have launched correctly. '
                        f'Expected: {app_package}, Current: {current_package}'
                    )
                    # Still return True if we got here without errors
                    return True
            except Exception as verify_error:
                logger.warning(f'Could not verify app launch: {verify_error}')
                # Still return True if the launch command succeeded
                return True
            
        except Exception as error:
            logger.error(f'Failed to start activity: {error}', exc_info=True)
            return False
    
    def activate_app(self, app_package: str) -> bool:
        """
        Activate an app (bring to foreground).
        
        Args:
            app_package: App package name
            
        Returns:
            True if successful
        """
        if not self.driver:
            return False
        
        try:
            self.driver.activate_app(app_package)
            logger.info(f'Activated app: {app_package}')
            return True
        except Exception as error:
            logger.debug(f'activateApp failed: {error}')
            return False
    
    def get_target_package(self) -> Optional[str]:
        """Get target package name."""
        return self.target_package
    
    def get_target_activity(self) -> Optional[str]:
        """Get target activity name."""
        return self.target_activity
    
    def get_allowed_external_packages(self) -> List[str]:
        """Get allowed external packages."""
        return list(self.allowed_external_packages)
    
    def set_allowed_external_packages(self, packages: List[str]) -> None:
        """Set allowed external packages."""
        self.allowed_external_packages = list(packages)
    
    def ensure_in_app(self) -> bool:
        """
        Ensure we are in the correct app context before performing actions.
        
        Checks if current package matches target or allowed external packages.
        Attempts recovery if not in correct context.
        
        Returns:
            True if in correct app context
        """
        if not self.driver:
            logger.error('Driver not connected, cannot ensure app context')
            self.consecutive_context_failures += 1
            return False
        
        # Skip check if no target package is set (not configured)
        if not self.target_package:
            logger.debug('No target package set, skipping app context check')
            return True
        
        platform = self._get_current_platform()
        if platform != 'android':
            logger.debug('App context check skipped for non-Android platform')
            return True
        
        # Get current package with retry
        current_package: Optional[str] = None
        max_context_retries = 2
        for retry in range(max_context_retries + 1):
            try:
                current_package = self.get_current_package()
                if current_package:
                    break
            except Exception as error:
                logger.warning(f'Error getting app context (retry {retry}): {error}')
                if retry < max_context_retries:
                    time.sleep(1.0)
                    continue
        
        if not current_package:
            logger.warning('Could not get app context after retries. Attempting recovery.')
            # Try to relaunch target app
            if self.target_package and self.target_activity:
                if self.start_activity(self.target_package, self.target_activity):
                    time.sleep(2.0)
                    context_after_relaunch = self.get_current_package()
                    if context_after_relaunch == self.target_package:
                        logger.info(
                            'Recovery successful: Relaunched target application after unknown context'
                        )
                        self.consecutive_context_failures = 0
                        return True
            logger.error('Failed to recover context even after relaunch from unknown state')
            self.consecutive_context_failures += 1
            return False
        
        # Build allowed packages set
        allowed_packages_set = {self.target_package, *self.allowed_external_packages}
        
        logger.debug(
            f'Current app context: {current_package}. '
            f'Allowed: {", ".join(allowed_packages_set)}'
        )
        
        if current_package in allowed_packages_set:
            logger.debug(f'App context OK (In \'{current_package}\')')
            self.consecutive_context_failures = 0
            return True
        
        # Not in correct app context
        logger.warning(
            f'App context incorrect: In \'{current_package}\', '
            f'expected one of {", ".join(allowed_packages_set)}'
        )
        self.consecutive_context_failures += 1
        
        if self.consecutive_context_failures >= self.max_consecutive_context_failures:
            logger.error(
                'Maximum consecutive context failures reached. '
                'No further recovery attempts this step.'
            )
            return False
        
        # Attempt recovery: press back button first
        logger.info('Attempting recovery: Pressing back button...')
        try:
            self.driver.back()
            time.sleep(1.0)
        except Exception as error:
            logger.debug(f'Failed to press back button during recovery: {error}')
        
        # Check if back button worked
        context_after_back = self.get_current_package()
        if context_after_back and context_after_back in allowed_packages_set:
            logger.info(
                'Recovery successful: Returned to target/allowed package after back press'
            )
            self.consecutive_context_failures = 0
            return True
        
        # Back button didn't work, try relaunching target app
        logger.warning(
            f'Recovery still not successful after back press '
            f'(current: {context_after_back or "Unknown"}). '
            f'Relaunching target application.'
        )
        if self.target_package and self.target_activity:
            if self.start_activity(self.target_package, self.target_activity):
                time.sleep(2.0)
                context_after_relaunch = self.get_current_package()
                if context_after_relaunch and context_after_relaunch in allowed_packages_set:
                    logger.info('Recovery successful: Relaunched target application')
                    self.consecutive_context_failures = 0
                    return True
        elif self.target_package:
            # Try activateApp if we don't have activity
            if self.activate_app(self.target_package):
                time.sleep(2.0)
                context_after_activate = self.get_current_package()
                if context_after_activate and context_after_activate in allowed_packages_set:
                    logger.info('Recovery successful: Activated target application')
                    self.consecutive_context_failures = 0
                    return True
        
        current_pkg_after_all = self.get_current_package() or 'Unknown'
        logger.error(
            f'All recovery attempts failed. Could not return to target/allowed application. '
            f'Currently in \'{current_pkg_after_all}\'.'
        )
        return False

