"""Action executor for mobile app interactions."""

import time
from typing import Optional, Tuple

from mobile_crawler.domain.models import ActionResult
from mobile_crawler.infrastructure.appium_driver import AppiumDriver
from mobile_crawler.infrastructure.gesture_handler import GestureHandler
from mobile_crawler.infrastructure.adb_input_handler import ADBInputHandler
from mobile_crawler.infrastructure.gmail.service import GmailService
from mobile_crawler.infrastructure.gmail.config import GmailSearchQuery


class ActionExecutor:
    """
    Executes actions on mobile devices via Appium.
    """

    def __init__(self, appium_driver: AppiumDriver, gesture_handler: GestureHandler,
                 adb_input_handler: Optional[ADBInputHandler] = None,
                 gmail_service: Optional[GmailService] = None):
        """Initialize action executor.

        Args:
            appium_driver: Appium driver instance
            gesture_handler: Gesture handler instance
            adb_input_handler: ADB input handler for text input (optional, created if not provided)
            gmail_service: Gmail service for email automation (optional)
        """
        self.appium_driver = appium_driver
        self.gesture_handler = gesture_handler
        self.adb_input_handler = adb_input_handler or ADBInputHandler()
        self.gmail_service = gmail_service
        self._last_action_time = 0
        self._action_delay_ms = 2000  # 2s between actions for visual observability

    def _ensure_delay(self):
        """Ensure minimum delay between actions."""
        now = time.time() * 1000
        elapsed = now - self._last_action_time
        if elapsed < self._action_delay_ms:
            time.sleep((self._action_delay_ms - elapsed) / 1000)
        self._last_action_time = time.time() * 1000

    def _calculate_center(self, bounds: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """Calculate center point from bounding box.

        Args:
            bounds: (x1, y1, x2, y2)

        Returns:
            (center_x, center_y)
        """
        x1, y1, x2, y2 = bounds
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def _get_screen_center(self) -> Tuple[int, int]:
        """Get screen center coordinates.

        Returns:
            (center_x, center_y)
        """
        # Get screen size from driver
        size = self.appium_driver.get_driver().get_window_size()
        return (size['width'] // 2, size['height'] // 2)

    def _execute_with_timing(self, action_func, *args, **kwargs) -> Tuple[bool, float, Optional[str]]:
        """Execute action function with timing.

        Args:
            action_func: Function to execute
            *args: Positional args for function
            **kwargs: Keyword args for function

        Returns:
            (success, duration_ms, error_message)
        """
        start_time = time.time()
        try:
            action_func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
        duration_ms = (time.time() - start_time) * 1000
        
        # Add post-action delay to ensure action is visible and completes
        time.sleep(1.5)
        
        return success, duration_ms, error

    def click(self, bounds: Tuple[int, int, int, int]) -> ActionResult:
        """Execute click action at bounding box center.

        Args:
            bounds: Bounding box (x1, y1, x2, y2)

        Returns:
            ActionResult
        """
        self._ensure_delay()
        center_x, center_y = self._calculate_center(bounds)

        success, duration_ms, error = self._execute_with_timing(
            self.gesture_handler.tap_at, center_x, center_y
        )

        return ActionResult(
            success=success,
            action_type="click",
            target=f"({center_x}, {center_y})",
            duration_ms=duration_ms,
            error_message=error,
            navigated_away=False  # TODO: Implement screen change detection
        )

    def input(self, bounds: Tuple[int, int, int, int], text: str) -> ActionResult:
        """Execute input action: tap then send text via ADB (image-only mode).

        This method uses ADB shell input text command instead of Appium's
        send_keys to avoid accessing the DOM/XML page source.

        Args:
            bounds: Bounding box (x1, y1, x2, y2)
            text: Text to input

        Returns:
            ActionResult
        """
        self._ensure_delay()
        center_x, center_y = self._calculate_center(bounds)

        def input_action():
            # First tap to focus on the input field
            self.gesture_handler.tap_at(center_x, center_y)
            # Wait a moment for focus to be established
            time.sleep(0.5)
            # Clear existing text using backspace via ADB
            self.adb_input_handler.clear_text_field()
            # Send text via ADB (image-only, no DOM access)
            self.adb_input_handler.input_text(text)

        success, duration_ms, error = self._execute_with_timing(input_action)

        return ActionResult(
            success=success,
            action_type="input",
            target=f"({center_x}, {center_y})",
            duration_ms=duration_ms,
            error_message=error,
            navigated_away=False
        )

    def long_press(self, bounds: Tuple[int, int, int, int]) -> ActionResult:
        """Execute long press action at bounding box center.

        Args:
            bounds: Bounding box (x1, y1, x2, y2)

        Returns:
            ActionResult
        """
        self._ensure_delay()
        center_x, center_y = self._calculate_center(bounds)

        success, duration_ms, error = self._execute_with_timing(
            self.gesture_handler.long_press_at, center_x, center_y
        )

        return ActionResult(
            success=success,
            action_type="long_press",
            target=f"({center_x}, {center_y})",
            duration_ms=duration_ms,
            error_message=error,
            navigated_away=False
        )

    def scroll_up(self) -> ActionResult:
        """Execute scroll up from screen center.

        Returns:
            ActionResult
        """
        self._ensure_delay()
        center_x, center_y = self._get_screen_center()

        success, duration_ms, error = self._execute_with_timing(
            self.gesture_handler.scroll, "up"
        )

        return ActionResult(
            success=success,
            action_type="scroll_up",
            target=f"({center_x}, {center_y})",
            duration_ms=duration_ms,
            error_message=error,
            navigated_away=False
        )

    def scroll_down(self) -> ActionResult:
        """Execute scroll down from screen center.

        Returns:
            ActionResult
        """
        self._ensure_delay()
        center_x, center_y = self._get_screen_center()

        success, duration_ms, error = self._execute_with_timing(
            self.gesture_handler.scroll, "down"
        )

        return ActionResult(
            success=success,
            action_type="scroll_down",
            target=f"({center_x}, {center_y})",
            duration_ms=duration_ms,
            error_message=error,
            navigated_away=False
        )

    def swipe_left(self) -> ActionResult:
        """Execute swipe left from screen center.

        Returns:
            ActionResult
        """
        self._ensure_delay()
        center_x, center_y = self._get_screen_center()

        success, duration_ms, error = self._execute_with_timing(
            self.gesture_handler.scroll, "left"
        )

        return ActionResult(
            success=success,
            action_type="swipe_left",
            target=f"({center_x}, {center_y})",
            duration_ms=duration_ms,
            error_message=error,
            navigated_away=False
        )

    def swipe_right(self) -> ActionResult:
        """Execute swipe right from screen center.

        Returns:
            ActionResult
        """
        self._ensure_delay()
        center_x, center_y = self._get_screen_center()

        success, duration_ms, error = self._execute_with_timing(
            self.gesture_handler.scroll, "right"
        )

        return ActionResult(
            success=success,
            action_type="swipe_right",
            target=f"({center_x}, {center_y})",
            duration_ms=duration_ms,
            error_message=error,
            navigated_away=False
        )

    def back(self) -> ActionResult:
        """Execute back action (press back button).

        Returns:
            ActionResult
        """
        self._ensure_delay()

        success, duration_ms, error = self._execute_with_timing(
            self.appium_driver.get_driver().back
        )

        return ActionResult(
            success=success,
            action_type="back",
            target="back_button",
            duration_ms=duration_ms,
            error_message=error,
            navigated_away=False
        )

    def extract_otp(self, sender: Optional[str] = None, subject: Optional[str] = None) -> ActionResult:
        """Execute OTP extraction from Gmail.

        Args:
            sender: Email sender filter
            subject: Subject keyword filter

        Returns:
            ActionResult (success=True, input_text=OTP if found)
        """
        if not self.gmail_service:
            return ActionResult(success=False, action_type="extract_otp", error_message="Gmail service not initialized")

        self._ensure_delay()
        query = GmailSearchQuery(sender=sender, subject_contains=subject)

        start_time = time.time()
        try:
            otp = self.gmail_service.extract_otp(query)
            success = otp is not None
            error = None if success else "OTP not found"
        except Exception as e:
            otp = None
            success = False
            error = str(e)
        duration_ms = (time.time() - start_time) * 1000

        return ActionResult(
            success=success,
            action_type="extract_otp",
            target="Gmail",
            duration_ms=duration_ms,
            error_message=error,
            input_text=otp
        )

    def click_verification_link(self, sender: Optional[str] = None, subject: Optional[str] = None) -> ActionResult:
        """Execute verification link click in Gmail.

        Args:
            sender: Email sender filter
            subject: Subject keyword filter

        Returns:
            ActionResult
        """
        if not self.gmail_service:
            return ActionResult(success=False, action_type="click_verification_link", error_message="Gmail service not initialized")

        self._ensure_delay()
        query = GmailSearchQuery(sender=sender, subject_contains=subject)

        start_time = time.time()
        try:
            success = self.gmail_service.click_verification_link(query)
            error = None if success else "Link not clicked"
        except Exception as e:
            success = False
            error = str(e)
        duration_ms = (time.time() - start_time) * 1000

        return ActionResult(
            success=success,
            action_type="click_verification_link",
            target="Gmail",
            duration_ms=duration_ms,
            error_message=error
        )