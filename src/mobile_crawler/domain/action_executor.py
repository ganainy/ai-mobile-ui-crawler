"""Action executor for mobile app interactions."""

import time
import logging
import subprocess
from typing import Optional, Tuple

from mobile_crawler.domain.models import ActionResult
from mobile_crawler.infrastructure.appium_driver import AppiumDriver
from mobile_crawler.infrastructure.gesture_handler import GestureHandler
from mobile_crawler.infrastructure.adb_input_handler import ADBInputHandler
from mobile_crawler.infrastructure.mailosaur.service import MailosaurService
from mobile_crawler.infrastructure.mailosaur.models import MailosaurConfig

logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    Executes actions on mobile devices via Appium.
    """

    def __init__(self, appium_driver: AppiumDriver, gesture_handler: GestureHandler,
                 adb_input_handler: Optional[ADBInputHandler] = None,
                 mailosaur_service: Optional[MailosaurService] = None,
                 test_email: Optional[str] = None):
        """Initialize action executor.

        Args:
            appium_driver: Appium driver instance
            gesture_handler: Gesture handler instance
            adb_input_handler: ADB input handler for text input (optional, created if not provided)
            mailosaur_service: Mailosaur service for email automation (optional)
            test_email: Optional fallback email address for extraction
        """
        self.appium_driver = appium_driver
        self.gesture_handler = gesture_handler
        self.adb_input_handler = adb_input_handler or ADBInputHandler()
        self.mailosaur_service = mailosaur_service
        self.test_email = test_email
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

    def extract_otp(self, email: Optional[str] = None, timeout: int = 60) -> ActionResult:
        """Execute OTP extraction from Mailosaur.

        Args:
            email: The email address to check for OTP.
                   If None, uses configured test email.
            timeout: Maximum time to wait for email (seconds)

        Returns:
            ActionResult with success=True and input_text=OTP if found
        """
        if not self.mailosaur_service:
            logger.error("extract_otp failed: Mailosaur service not configured")
            return ActionResult(success=False, action_type="extract_otp", target="Email", error_message="Mailosaur service not configured")

        self._ensure_delay()
        target_email = email or self.test_email
        if not target_email:
            logger.error("extract_otp failed: No email address provided or configured")
            return ActionResult(success=False, action_type="extract_otp", target="Email", error_message="No email address provided or configured")

        logger.info(f"Extracting OTP for {target_email} (timeout={timeout}s)...")
        start_time = time.time()
        try:
            otp = self.mailosaur_service.get_otp(target_email, timeout=timeout)
            success = otp is not None
            if success:
                logger.info(f"OTP found: {otp}")
            else:
                logger.warning(f"OTP not found for {target_email}")
            error = None if success else "OTP not found in email"
        except Exception as e:
            otp = None
            success = False
            error = str(e)
        duration_ms = (time.time() - start_time) * 1000

        return ActionResult(
            success=success,
            action_type="extract_otp",
            target=f"Mailosaur ({target_email})",
            duration_ms=duration_ms,
            error_message=error,
            input_text=otp
        )

    def click_verification_link(self, email: Optional[str] = None, link_text: Optional[str] = None, timeout: int = 60) -> ActionResult:
        """Execute verification link extraction and processing.

        Retrieves the magic link from Mailosaur and opens it using ADB.

        Args:
            email: The email address to check for verification link.
                   If None, uses configured test email.
            link_text: Optional anchor text to identify the correct link.
            timeout: Maximum time to wait for email (seconds)

        Returns:
            ActionResult
        """
        if not self.mailosaur_service:
            logger.error("click_verification_link failed: Mailosaur service not configured")
            return ActionResult(success=False, action_type="click_verification_link", target="Email", error_message="Mailosaur service not configured")

        self._ensure_delay()
        target_email = email or self.test_email
        if not target_email:
            logger.error("click_verification_link failed: No email address provided or configured")
            return ActionResult(success=False, action_type="click_verification_link", target="Email", error_message="No email address provided or configured")

        logger.info(f"Extracting magic link for {target_email} (link_text='{link_text}', timeout={timeout}s)...")
        start_time = time.time()
        try:
            url = self.mailosaur_service.get_magic_link(target_email, link_text, timeout=timeout)
            if url:
                logger.info(f"Found magic link: {url}")
                logger.info("Opening magic link via ADB...")
                self._open_url_via_adb(url)
                logger.info("Magic link opened successfully")
                success = True
                error = None
            else:
                logger.warning(f"No magic link found for {target_email}")
                success = False
                error = "No verification link found"
        except Exception as e:
            success = False
            error = str(e)
        duration_ms = (time.time() - start_time) * 1000

        return ActionResult(
            success=success,
            action_type="click_verification_link",
            target=f"Mailosaur ({target_email})",
            duration_ms=duration_ms,
            error_message=error
        )

    def _open_url_via_adb(self, url: str):
        """Open URL on device using ADB."""
        device_id = self.appium_driver.device_id
        cmd = [
            "adb", "-s", device_id,
            "shell", "am", "start",
            "-a", "android.intent.action.VIEW",
            "-d", url
        ]
        logger.info(f"Running ADB command to open URL: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            if result.stdout:
                logger.debug(f"ADB stdout: {result.stdout.strip()}")
            if result.stderr:
                logger.debug(f"ADB stderr: {result.stderr.strip()}")
        except subprocess.CalledProcessError as e:
            logger.error(f"ADB command failed (code {e.returncode}): {e.stderr.strip()}")
            raise