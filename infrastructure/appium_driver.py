"""
Appium driver wrapper for direct Appium-Python-Client integration.

Provides a high-level interface for Appium operations using AppiumHelper.
"""

import base64
import logging
import time
from functools import wraps
from typing import Any, Dict, Optional, Tuple, Union

from config.app_config import Config
from infrastructure.appium_helper import AppiumHelper
from infrastructure.device_detection import (
    detect_all_devices,
    select_best_device,
    validate_device,
    DeviceInfo,
    Platform,
)
from infrastructure.capability_builder import (
    build_android_capabilities,
    AppiumCapabilities,
)
from infrastructure.appium_error_handler import AppiumError

logger = logging.getLogger(__name__)


def require_helper(func):
    """Decorator to ensure helper is initialized."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self._ensure_helper():
            logger.error(f"Cannot execute {func.__name__}: Helper not available")
            return None if func.__name__.startswith('get_') else False
        return func(self, *args, **kwargs)
    return wrapper


class AppiumDriver:
    """High-level Appium driver wrapper."""
    
    # Gesture constants
    SCROLL_DURATION = 0.8  # seconds
    FLICK_DURATION = 0.2   # seconds
    TEXT_INPUT_DELAY = 0.3  # seconds
    TOAST_DEFAULT_TIMEOUT = 1200  # milliseconds
    
    # Coordinate ratios
    SCROLL_DISTANCE_RATIO = 0.6
    FLICK_DISTANCE_RATIO = 0.7
    
    # Default window size
    DEFAULT_WINDOW_SIZE = {"width": 1080, "height": 1920}
    
    # Android key codes
    ANDROID_KEY_HOME = 3

    def __init__(self, app_config: Config):
        """
        Initialize AppiumDriver.
        
        Args:
            app_config: Application configuration
        """
        self.cfg = app_config
        self.helper: Optional[AppiumHelper] = None
        self._session_initialized = False
        self._session_info: Optional[Dict[str, Any]] = None
        self._last_screenshot_was_blocked = False  # Track if last screenshot was blocked by FLAG_SECURE
    
    def disconnect(self):
        """Disconnect Appium helper and close session."""
        if self.helper:
            try:
                if self._session_initialized:
                    try:
                        self.helper.close_driver()
                    except Exception as e:
                        logger.warning(f"Error closing Appium session: {e}")
                    finally:
                        self._session_initialized = False
                        self._session_info = None
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.helper = None
    
    def _ensure_helper(self) -> bool:
        """Ensure AppiumHelper is initialized."""
        if not self.helper:
            # Create helper with config values
            max_retries = self.cfg.get('APPIUM_MAX_RETRIES', 2)  
            retry_delay = self.cfg.get('APPIUM_RETRY_DELAY', 1.0)
            implicit_wait = self.cfg.get('APPIUM_IMPLICIT_WAIT', 3000)
            
            self.helper = AppiumHelper(
                max_retries=max_retries,
                retry_delay=retry_delay,
                implicit_wait=implicit_wait
            )
        return True

    @property
    def driver(self):
        """Get the underlying Appium driver."""
        return self.helper.get_driver() if self.helper else None

    def _calculate_gesture_coordinates(
        self, 
        direction: str, 
        distance_ratio: float = 0.6
    ) -> Optional[Tuple[float, float, float, float]]:
        """
        Calculate start and end coordinates for gestures.
        
        Args:
            direction: Gesture direction ('up', 'down', 'left', 'right')
            distance_ratio: How much of the screen to traverse (0.0-1.0)
        
        Returns:
            (start_x, start_y, end_x, end_y) or None if invalid
        """
        window_size = self.get_window_size()
        width = window_size['width']
        height = window_size['height']
        
        # Default ratios to match original scroll logic (0.2 to 0.8)
        # distance_ratio 0.6 means traverse 60% of screen. 
        # Center is 0.5. Start: 0.5 - 0.3 = 0.2. End: 0.5 + 0.3 = 0.8.
        
        half_dist = distance_ratio / 2
        mid_w = width / 2
        mid_h = height / 2
        
        direction_lower = direction.lower()
        if direction_lower == 'up':
            # Original: 0.2 to 0.8 (Top to Bottom)
            # This logic: 0.5 - 0.3 = 0.2 start, 0.5 + 0.3 = 0.8 end.
            return (mid_w, height * (0.5 - half_dist), mid_w, height * (0.5 + half_dist))
        elif direction_lower == 'down':
             # Original: 0.8 to 0.2 (Bottom to Top)
            return (mid_w, height * (0.5 + half_dist), mid_w, height * (0.5 - half_dist))
        elif direction_lower == 'left':
             # Original: 0.8 to 0.2 (Right to Left)
            return (width * (0.5 + half_dist), mid_h, width * (0.5 - half_dist), mid_h)
        elif direction_lower == 'right':
             # Original: 0.2 to 0.8 (Left to Right)
            return (width * (0.5 - half_dist), mid_h, width * (0.5 + half_dist), mid_h)
        
        return None

    def _extract_bbox_center(self, bbox: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
        """Extract center coordinates from bounding box."""
        top_left = bbox.get('top_left')
        bottom_right = bbox.get('bottom_right')
        
        if top_left and bottom_right:
            x = (top_left[0] + bottom_right[0]) / 2
            y = (top_left[1] + bottom_right[1]) / 2
            return int(x), int(y)
        return None, None

    def _interact_with_text_element(
        self, 
        target_identifier: str, 
        text: str, 
        clear_first: bool = False
    ) -> bool:
        """Internal method to handle text input operations."""
        try:
            element = self.helper.find_element(target_identifier, strategy='id')
            
            # Click to focus
            try:
                element.click()
                time.sleep(self.TEXT_INPUT_DELAY)
            except Exception as e:
                logger.warning(f"Could not click element: {e}")
            
            # Clear if requested
            if clear_first:
                element.clear()
            
            # Send text
            element.send_keys(text)
            return True
            
        except Exception as e:
            logger.error(f"Error interacting with text element: {e}")
            return False

    def _is_flag_secure_error(self, error: Exception) -> bool:
        """Check if error is due to FLAG_SECURE blocking."""
        error_keywords = ['secure', 'flag_secure', 'screenshot blocked']
        error_msg = str(error).lower()
        return any(keyword in error_msg for keyword in error_keywords)
    
    def initialize_session(
        self,
        app_package: Optional[str] = None,
        app_activity: Optional[str] = None,
        device_udid: Optional[str] = None,
        platform_name: str = "Android"
    ) -> bool:
        """
        Initialize Appium session with device auto-detection.
        
        Args:
            app_package: Android app package name
            app_activity: Android app activity name
            device_udid: Device UDID (optional, will auto-detect if not provided)
            platform_name: Platform name ("Android")
            
        Returns:
            True if session initialized successfully, False otherwise
        """
        if not self._ensure_helper():
            return False
        
        try:
            # Detect available devices
            all_devices = detect_all_devices()
            if not all_devices:
                logger.error(
                    "No devices found. Please ensure:\n"
                    "- Android: Android SDK is installed and devices/emulators are connected"
                )
                return False
            
            # Select best device
            platform: Platform = 'android'
            selected_device = select_best_device(
                all_devices,
                platform,
                None  # device_name
            )
            
            if not selected_device:
                logger.error(
                    f"No suitable {platform_name} device found. Available devices:\n" +
                    "\n".join(f"- {d.name} ({d.platform}, {d.type})" for d in all_devices)
                )
                return False
            
            # Override with explicit UDID if provided
            if device_udid:
                for device in all_devices:
                    if device.id == device_udid:
                        selected_device = device
                        break
                else:
                    logger.warning(f"Device with UDID {device_udid} not found, using auto-selected device")
            
            # Validate device is ready
            if not validate_device(selected_device):
                logger.error(
                    f"Device {selected_device.name} is not ready for automation.\n"
                    "Please ensure the device is responsive and try again."
                )
                return False
            
            # Set device UDID and name in path manager for session path generation (before session path is accessed)
            # This ensures the output directory uses the correct device ID instead of "unknown_device"
            # Prefer device name over UDID for folder names (more readable)
            if hasattr(self.cfg, '_path_manager'):
                # Set device info in path manager (this will invalidate cached session path)
                self.cfg._path_manager.set_device_info(udid=selected_device.id, name=selected_device.name)
                
                # Get the session path (it will be generated with the correct device info)
                self.cfg._path_manager.get_session_path(force_regenerate=False)
            
            # Build capabilities for Android
            capabilities = build_android_capabilities(
                selected_device,
                app_package=app_package,
                app_activity=app_activity,
                app=None,
                additional_caps={
                    'appium:noReset': True,
                }
            )
            
            # Get allowed external packages from config
            allowed_external_packages = self.cfg.get('ALLOWED_EXTERNAL_PACKAGES')
            if allowed_external_packages:
                if isinstance(allowed_external_packages, str):
                    allowed_external_packages = [
                        pkg.strip() for pkg in allowed_external_packages.split('\n')
                        if pkg.strip()
                    ]
                elif isinstance(allowed_external_packages, (list, tuple)):
                    allowed_external_packages = [
                        str(pkg).strip() for pkg in allowed_external_packages
                        if pkg and str(pkg).strip()
                    ]
                else:
                    allowed_external_packages = []
            
            # Get Appium server URL
            from config.urls import ServiceURLs
            appium_url = self.cfg.get('APPIUM_SERVER_URL', ServiceURLs.APPIUM)
            
            # Initialize session with app context configuration
            context_config = {
                'targetPackage': app_package,
                'targetActivity': app_activity,
                'allowedExternalPackages': allowed_external_packages or []
            }
            
            self.helper.initialize_driver(
                capabilities,
                appium_url,
                context_config
            )
            
            self._session_initialized = True
            session_state = self.helper.get_session_state()
            self._session_info = {
                'sessionId': session_state.session_id,
                'platform': selected_device.platform,
                'device': selected_device.name,
                'udid': selected_device.id,
            }
            
            return True
            
        except AppiumError as e:
            logger.error(f"Appium error initializing session: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error initializing session: {e}", exc_info=True)
            return False
    
    @require_helper
    def validate_session(self) -> bool:
        """
        Validate that the current session is still active.
        
        Returns:
            True if session is valid, False otherwise
        """
        try:
            is_valid = self.helper.validate_session()
            if not is_valid:
                self._invalidate_session()
            return is_valid
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            self._invalidate_session()
            return False

    def _invalidate_session(self):
        """Mark session as invalid and clear session info."""
        self._session_initialized = False
        self._session_info = None
    
    @require_helper
    def get_page_source(self) -> Optional[str]:
        """Get page source."""
        try:
            return self.helper.get_page_source()
        except Exception as e:
            logger.error(f"Error getting page source: {e}")
            return None
    
    @require_helper
    def get_screenshot_as_base64(self) -> Optional[str]:
        """Get screenshot as base64 string."""
        try:
            screenshot = self.helper.take_screenshot()
            if not screenshot:
                logger.warning("Screenshot returned empty/None")
                return None
            
            # Clean up data URI if present
            if screenshot.startswith("data:image"):
                screenshot = screenshot.split(",", 1)[1]
            
            self._last_screenshot_was_blocked = False
            return screenshot
            
        except Exception as e:
            # Check for FLAG_SECURE blocking
            if self._is_flag_secure_error(e):
                logger.warning("Screenshot blocked by FLAG_SECURE")
                self._last_screenshot_was_blocked = True
                return None
            
            logger.error(f"Error getting screenshot: {e}")
            self._last_screenshot_was_blocked = False
            return None
    
    def get_screenshot_bytes(self) -> Optional[bytes]:
        """Get screenshot as raw bytes."""
        screenshot_base64 = self.get_screenshot_as_base64()
        if screenshot_base64:
            try:
                return base64.b64decode(screenshot_base64)
            except Exception as e:
                logger.error(f"Error decoding screenshot to bytes: {e}")
                return None
        return None
    
    @require_helper
    def tap(
        self,
        target_identifier: Optional[str] = None,
        bbox: Optional[Dict[str, Any]] = None,
        x: Optional[int] = None,
        y: Optional[int] = None
    ) -> bool:
        """
        Tap element or coordinates.
        Priority: coordinates (x,y) > bbox > identifier
        """
        try:
            # Get tap coordinates
            tap_x, tap_y = None, None
            
            if x is not None and y is not None:
                tap_x, tap_y = x, y
            elif bbox:
                tap_x, tap_y = self._extract_bbox_center(bbox)
            elif target_identifier:
                return self.helper.tap_element(target_identifier, strategy='id')
            else:
                logger.error("tap() requires coordinates, bbox, or identifier")
                return False
            
            # Execute tap at coordinates
            if tap_x is not None and tap_y is not None:
                if self.driver:
                    self.driver.tap([(int(tap_x), int(tap_y))])
                    return True
                else:
                    logger.error("Driver not available for tap")
                    return False
                
            return False
            
        except Exception as e:
            context = f"identifier='{target_identifier}'" if target_identifier else f"bbox={bbox}"
            logger.error(f"Error during tap ({context}): {e}", exc_info=True)
            return False
    
    @require_helper
    def input_text(self, target_identifier: str, text: str) -> bool:
        """Input text into element (appends to existing text)."""
        return self._interact_with_text_element(target_identifier, text, clear_first=False)
    
    @require_helper
    def scroll(self, direction: str) -> bool:
        """
        Scroll in specified direction.
        
        Args:
            direction: Scroll direction ('up', 'down', 'left', 'right')
            
        Returns:
            True if scroll successful
        """
        try:
            coords = self._calculate_gesture_coordinates(direction, distance_ratio=self.SCROLL_DISTANCE_RATIO)
            if not coords:
                logger.error(f"Invalid scroll direction: {direction}")
                return False
            
            if self.helper.gesture_handler:
                self.helper.gesture_handler.perform_w3c_swipe(*coords, duration_sec=self.SCROLL_DURATION)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error during scroll: {e}")
            return False
    
    @require_helper
    def long_press(self, target_identifier: str, duration: int) -> bool:
        """
        Long press element.
        
        Args:
            target_identifier: Element identifier
            duration: Press duration in milliseconds
            
        Returns:
            True if successful
        """
        try:
            # Find element and get its center
            element = self.helper.find_element(target_identifier, strategy='id')
            x, y = self.helper._get_element_center(element)
            
            # Perform long press using specialized GestureHandler
            if self.helper.gesture_handler:
                self.helper.gesture_handler.perform_w3c_long_press(x, y, duration)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error during long_press: {e}")
            return False
    
    @require_helper
    def press_back(self) -> bool:
        """Press back button."""
        try:
            if self.driver:
                self.driver.back()
                return True
            return False
        except Exception as e:
            logger.error(f"Error during press_back: {e}", exc_info=True)
            return False

    @require_helper
    def press_home(self) -> bool:
        """Press home button."""
        try:
            if self.driver:
                self.driver.press_keycode(self.ANDROID_KEY_HOME)
                return True
            return False
        except Exception as e:
            logger.error(f"Error during press_home: {e}")
            return False
    
    def wait_for_toast_to_dismiss(self, timeout_ms: int = 1200):
        """Wait for toast to dismiss."""
        time.sleep(timeout_ms / 1000.0)
    
    @require_helper
    def get_window_size(self) -> Dict[str, int]:
        """Get window size."""
        try:
            return self.helper.get_window_size()
        except Exception as e:
            logger.error(f"Error getting window size: {e}")
            return self.DEFAULT_WINDOW_SIZE
    
    @require_helper
    def start_video_recording(self, max_retries: int = 2, **kwargs) -> bool:
        """
        Starts recording the screen using Appium's built-in method.
        
        Args:
            max_retries: Number of retries for transient errors
            **kwargs: Optional recording options to pass to start_recording_screen()
            
        Returns:
            True if recording started successfully, False otherwise
        """
        if not self.driver:
            logger.error("Cannot start video recording: Driver not available")
            return False
        
        for attempt in range(max_retries):
            try:
                self.driver.start_recording_screen(**kwargs)
                return True
            except Exception as e:
                error_str = str(e).lower()
                # Retry for known transient errors
                if attempt < max_retries - 1 and ('no such process' in error_str or 'screenrecord' in error_str):
                    logger.debug(f"Retrying video recording start (attempt {attempt + 2}/{max_retries})")
                    continue
                
                logger.error(f"Failed to start video recording: {e}")
                return False
        
        return False
    
    @require_helper
    def stop_video_recording(self) -> Optional[str]:
        """
        Stops recording the screen and returns the video data as base64 string.
        
        Returns:
            Video data as base64-encoded string, or None on error
        """
        try:
            if not self.driver:
                logger.error("Cannot stop video recording: Driver not available")
                return None
            
            video_data = self.driver.stop_recording_screen()
            return video_data
            
        except Exception as e:
            logger.error(f"Failed to stop video recording: {e}", exc_info=True)
            return None
    
    def save_video_recording(self, video_data: str, file_path: str) -> bool:
        """Saves the video data to a file.
        
        Args:
            video_data: Video data as base64-encoded string
            file_path: Path to save the video file
            
        Returns:
            True if saved successfully, False otherwise
        """
        if not video_data:
            logger.error("Video data is empty, cannot save video.")
            return False
        
        try:
            import os
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(video_data))
            
            return True
        except Exception as e:
            logger.error(f"Failed to save video to {file_path}: {e}", exc_info=True)
            return False
    
    @require_helper
    def get_current_package(self) -> Optional[str]:
        """Get current package name (Android only)."""
        try:
            return self.helper.get_current_package()
        except Exception as e:
            logger.warning(f"Error getting current package: {e}")
            return None
    
    @require_helper
    def get_current_activity(self) -> Optional[str]:
        """Get current activity name (Android only)."""
        try:
            return self.helper.get_current_activity()
        except Exception as e:
            logger.error(f"Error getting current activity: {e}")
            return None
    
    def get_current_app_context(self) -> Optional[Tuple[Optional[str], Optional[str]]]:
        """Get current app context (package, activity)."""
        package = self.get_current_package()
        activity = self.get_current_activity()
        return package, activity
    
    @require_helper
    def terminate_app(self, package_name: str) -> bool:
        """Terminate app."""
        try:
            if self.driver:
                self.driver.terminate_app(package_name)
                return True
            return False
        except Exception as e:
            logger.error(f"Error terminating app: {e}")
            return False
    
    @require_helper
    def launch_app(self) -> bool:
        """Launch app."""
        try:
            if self.driver:
                self.driver.launch_app()
                return True
            return False
        except Exception as e:
            logger.error(f"Error launching app: {e}")
            return False
    
    @require_helper
    def start_activity(
        self,
        app_package: str,
        app_activity: str,
        wait_after_launch: float = 5.0
    ) -> bool:
        """
        Start an Android app activity.
        
        Args:
            app_package: Android app package name
            app_activity: Android app activity name
            wait_after_launch: Time to wait after launching activity (seconds)
            
        Returns:
            True if activity was started successfully, False otherwise
        """
        try:
            wait_ms = int(wait_after_launch * 1000)
            return self.helper.start_activity(app_package, app_activity, wait_ms)
        except Exception as e:
            logger.error(f"Error starting activity: {e}")
            return False
    
    @require_helper
    def double_tap(
        self,
        target_identifier: Optional[str],
        bbox: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Double tap element or coordinates.
        Priority: element identifier (currently requires it)
        """
        try:
            # Only use element lookup
            if target_identifier:
                element = self.helper.find_element(target_identifier, strategy='id')
                x, y = self.helper._get_element_center(element)
            else:
                logger.error("double_tap() called without target_identifier")
                return False
            
            # Perform double tap using specialized GestureHandler (delegated)
            if self.helper.gesture_handler:
                self.helper.gesture_handler.perform_w3c_double_tap(x, y)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error during double_tap: {e}")
            return False
    
    @require_helper
    def clear_text(self, target_identifier: str) -> bool:
        """
        Clear text from input element.
        
        Args:
            target_identifier: Element identifier
            
        Returns:
            True if clear successful
        """
        try:
            element = self.helper.find_element(target_identifier, strategy='id')
            
            # Try element.clear() first
            try:
                element.clear()
                return True
            except Exception:
                # Fallback: send empty string
                try:
                    element.send_keys("")
                    return True
                except Exception as e:
                    logger.error(f"Failed to clear text from element {target_identifier}: {e}")
                    return False
            
        except Exception as e:
            logger.error(f"Error during clear_text: {e}")
            return False
    
    @require_helper
    def replace_text(self, target_identifier: str, text: str) -> bool:
        """
        Replace existing text in input element.
        
        Clicks the element first to focus it, clears existing text, then types new text.
        
        Args:
            target_identifier: Element identifier
            text: New text to set
            
        Returns:
            True if replace successful
        """
        return self._interact_with_text_element(target_identifier, text, clear_first=True)
    
    @require_helper
    def flick(self, direction: str) -> bool:
        """
        Perform a fast flick gesture in specified direction.
        
        Args:
            direction: Flick direction ('up', 'down', 'left', 'right')
            
        Returns:
            True if flick successful
        """
        try:
            coords = self._calculate_gesture_coordinates(direction, distance_ratio=self.FLICK_DISTANCE_RATIO)
            if not coords:
                logger.error(f"Invalid flick direction: {direction}")
                return False
            
            if self.helper.gesture_handler:
                self.helper.gesture_handler.perform_w3c_swipe(*coords, duration_sec=self.FLICK_DURATION)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error during flick: {e}")
            return False

            

    
    @require_helper
    def reset_app(self) -> bool:
        """
        Reset app to initial state.
        
        Returns:
            True if reset successful
        """
        try:
            if self.driver:
                self.driver.reset()
                return True
            return False
        except Exception as e:
            logger.error(f"Error during reset_app: {e}")
            return False
    
    def press_back_button(self) -> bool:
        """Press back button (deprecated, use press_back instead)."""
        import warnings
        warnings.warn("press_back_button is deprecated, use press_back instead", DeprecationWarning)
        return self.press_back()
    
    @require_helper
    def hide_keyboard(self) -> bool:
        """
        Hide the on-screen keyboard if it's visible.
        
        Returns:
            True if keyboard was hidden or wasn't visible, False on error
        """
        try:
            if self.driver:
                self.driver.hide_keyboard()
                return True
            return False
        except Exception as e:
            # Keyboard might not be present, which is fine
            return True  # Return True since keyboard being absent is not an error
