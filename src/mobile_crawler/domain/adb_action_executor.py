"""ADB-based action executor for mobile crawler."""

import logging
import re
import subprocess
import time
from dataclasses import dataclass

from mobile_crawler.domain.models import ActionResult
from mobile_crawler.infrastructure.adb_client import ADBClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceReadinessResult:
    """Result of the pre-crawl device wake/readiness check."""

    success: bool
    error_message: str | None = None
    screen_on: bool | None = None
    keyguard_locked: bool | None = None
    keyguard_secure: bool | None = None


class ADBActionExecutor:
    """
    Executes actions on mobile devices via ADB commands.
    Provides compatibility with DroidRun while maintaining ActionResult interface.
    """

    def __init__(self, device_id: str, adb_client: ADBClient | None = None):
        """Initialize ADB action executor.

        Args:
            device_id: ADB device identifier
            adb_client: ADB client instance (created if not provided)
        """
        self.device_id = device_id
        self.adb_client = adb_client or ADBClient()
        self._last_action_time = 0
        self._action_delay_ms = 1500  # 1.5s between actions for stability
        self._launcher_activity_cache: dict[str, str] = {}

    def _ensure_delay(self) -> None:
        """Ensure minimum delay between actions."""
        now = time.time() * 1000
        elapsed = now - self._last_action_time
        if elapsed < self._action_delay_ms:
            time.sleep((self._action_delay_ms - elapsed) / 1000)
        self._last_action_time = time.time() * 1000

    def _execute_adb_command(self, command: list[str], timeout: float = 10.0) -> tuple[bool, str, float]:
        """Execute ADB command with timing.

        Args:
            command: ADB command parts (without 'adb -s device_id')
            timeout: Command timeout in seconds

        Returns:
            (success, output/error, duration_ms)
        """
        start_time = time.time()
        full_command = ['adb', '-s', self.device_id] + command

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            duration_ms = (time.time() - start_time) * 1000

            if result.returncode == 0:
                return True, result.stdout.strip(), duration_ms
            else:
                return False, result.stderr.strip(), duration_ms

        except subprocess.TimeoutExpired:
            duration_ms = (time.time() - start_time) * 1000
            return False, f"Command timed out after {timeout}s", duration_ms
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return False, str(e), duration_ms

    def _calculate_center(self, bounds: tuple[int, int, int, int]) -> tuple[int, int]:
        """Calculate center point from bounding box.

        Args:
            bounds: (x1, y1, x2, y2)

        Returns:
            (center_x, center_y)
        """
        x1, y1, x2, y2 = bounds
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def _get_screen_size(self) -> tuple[int, int]:
        """Get screen dimensions via ADB.

        Returns:
            (width, height) in pixels
        """
        try:
            success, output, _ = self._execute_adb_command(['shell', 'wm', 'size'])
            if success and 'Physical size:' in output:
                # Parse "Physical size: 1080x2340"
                size_part = output.split('Physical size:')[1].strip()
                width, height = map(int, size_part.split('x'))
                return width, height
            else:
                # Fallback to default Android resolution
                logger.warning(f"Could not get screen size, using default: {output}")
                return 1080, 1920
        except Exception as e:
            logger.error(f"Failed to get screen size: {e}")
            return 1080, 1920

    def _read_screen_on_state(self) -> tuple[bool, bool | None, str]:
        """Read whether the display is awake from dumpsys power."""
        success, output, _ = self._execute_adb_command(['shell', 'dumpsys', 'power'])
        if not success:
            return False, None, output

        lowered = output.lower()
        if re.search(r'mwakefulness\s*=\s*awake', lowered):
            return True, True, output
        if re.search(r'mwakefulness\s*=\s*(asleep|dozing)', lowered):
            return True, False, output
        if re.search(r'display power:\s*state\s*=\s*on', lowered):
            return True, True, output
        if re.search(r'display power:\s*state\s*=\s*off', lowered):
            return True, False, output
        if re.search(r'mscreenon\s*=\s*true', lowered):
            return True, True, output
        if re.search(r'mscreenon\s*=\s*false', lowered):
            return True, False, output

        return True, None, output

    def _read_keyguard_state(self) -> tuple[bool, bool | None, bool | None, str]:
        """Read keyguard visibility/security from dumpsys window policy."""
        success, output, _ = self._execute_adb_command(['shell', 'dumpsys', 'window', 'policy'])
        if not success:
            return False, None, None, output

        locked_patterns = (
            r'mkeyguardshowing\s*=\s*true',
            r'isstatusbarkeyguard\s*=\s*true',
            r'mshowinglockscreen\s*=\s*true',
            r'mdreaminglockscreen\s*=\s*true',
            r'^\s*showing\s*=\s*true\b',
            r'^\s*inputrestricted\s*=\s*true\b',
        )
        unlocked_patterns = (
            r'mkeyguardshowing\s*=\s*false',
            r'isstatusbarkeyguard\s*=\s*false',
            r'mshowinglockscreen\s*=\s*false',
            r'^\s*showing\s*=\s*false\b',
            r'^\s*inputrestricted\s*=\s*false\b',
        )
        secure_patterns = (
            r'mkeyguardsecure\s*=\s*true',
            r'iskeyguardsecure\s*=\s*true',
            r'msecure\s*=\s*true',
            r'^\s*secure\s*=\s*true\b',
        )
        insecure_patterns = (
            r'mkeyguardsecure\s*=\s*false',
            r'iskeyguardsecure\s*=\s*false',
            r'msecure\s*=\s*false',
            r'^\s*secure\s*=\s*false\b',
        )

        lowered = output.lower()
        locked = None
        if any(re.search(pattern, lowered, re.MULTILINE) for pattern in locked_patterns):
            locked = True
        elif any(re.search(pattern, lowered, re.MULTILINE) for pattern in unlocked_patterns):
            locked = False

        secure = None
        if any(re.search(pattern, lowered, re.MULTILINE) for pattern in secure_patterns):
            secure = True
        elif any(re.search(pattern, lowered, re.MULTILINE) for pattern in insecure_patterns):
            secure = False

        return True, locked, secure, output

    def _read_device_readiness_state(self) -> DeviceReadinessResult:
        """Read screen and keyguard state, failing closed when state is unclear."""
        power_success, screen_on, power_output = self._read_screen_on_state()
        if not power_success:
            return DeviceReadinessResult(
                success=False,
                error_message=f"Unable to read device power state: {power_output}",
            )
        if screen_on is None:
            return DeviceReadinessResult(
                success=False,
                error_message="Unable to determine whether the device screen is on.",
            )

        keyguard_success, locked, secure, keyguard_output = self._read_keyguard_state()
        if not keyguard_success:
            return DeviceReadinessResult(
                success=False,
                error_message=f"Unable to read device lock state: {keyguard_output}",
                screen_on=screen_on,
            )
        if locked is None:
            return DeviceReadinessResult(
                success=False,
                error_message="Unable to determine whether the device is locked.",
                screen_on=screen_on,
                keyguard_secure=secure,
            )

        return DeviceReadinessResult(
            success=True,
            screen_on=screen_on,
            keyguard_locked=locked,
            keyguard_secure=secure,
        )

    def _wake_device(self) -> DeviceReadinessResult:
        """Send Android's wake key event."""
        success, output, _ = self._execute_adb_command([
            'shell', 'input', 'keyevent', 'KEYCODE_WAKEUP'
        ])
        if not success:
            return DeviceReadinessResult(
                success=False,
                error_message=f"Unable to wake device: {output}",
            )
        return DeviceReadinessResult(success=True)

    def _swipe_up_to_dismiss_keyguard(self) -> DeviceReadinessResult:
        """Swipe up to dismiss non-secure keyguard or screensaver surfaces."""
        width, height = self._get_screen_size()
        center_x = width // 2
        start_y = height * 4 // 5
        end_y = height // 5
        success, output, _ = self._execute_adb_command([
            'shell', 'input', 'swipe', str(center_x), str(start_y),
            str(center_x), str(end_y), '300'
        ])
        if not success:
            return DeviceReadinessResult(
                success=False,
                error_message=f"Unable to dismiss keyguard with swipe: {output}",
            )
        return DeviceReadinessResult(success=True)

    def ensure_device_ready_for_crawl(
        self,
        timeout_seconds: float = 5.0,
        unlock_swipe: bool = True,
    ) -> DeviceReadinessResult:
        """Wake the device and verify it is not blocked by the lock screen."""
        deadline = time.time() + max(timeout_seconds, 0.1)
        power_success, screen_on, power_output = self._read_screen_on_state()
        if not power_success:
            return DeviceReadinessResult(
                success=False,
                error_message=f"Unable to read device power state: {power_output}",
            )
        if screen_on is None:
            return DeviceReadinessResult(
                success=False,
                error_message="Unable to determine whether the device screen is on.",
            )

        if screen_on is False:
            wake_result = self._wake_device()
            if not wake_result.success:
                return wake_result

            while time.time() < deadline:
                time.sleep(0.25)
                power_success, screen_on, power_output = self._read_screen_on_state()
                if not power_success:
                    return DeviceReadinessResult(
                        success=False,
                        error_message=f"Unable to read device power state: {power_output}",
                    )
                if screen_on:
                    break
            else:
                return DeviceReadinessResult(
                    success=False,
                    error_message="Device screen did not turn on after wake command.",
                    screen_on=False,
                )

        state = self._read_device_readiness_state()
        if not state.success:
            if (
                unlock_swipe
                and state.screen_on
                and state.error_message == "Unable to determine whether the device is locked."
            ):
                swipe_result = self._swipe_up_to_dismiss_keyguard()
                if not swipe_result.success:
                    return swipe_result
                time.sleep(0.5)
                state = self._read_device_readiness_state()
            if not state.success:
                return state

        if state.keyguard_locked:
            if state.keyguard_secure:
                return DeviceReadinessResult(
                    success=False,
                    error_message="Device is locked. Unlock it manually and start the crawl again.",
                    screen_on=state.screen_on,
                    keyguard_locked=True,
                    keyguard_secure=True,
                )

            if unlock_swipe:
                swipe_result = self._swipe_up_to_dismiss_keyguard()
                if not swipe_result.success:
                    return swipe_result
                time.sleep(0.5)
                state = self._read_device_readiness_state()
                if not state.success:
                    return state

        if state.keyguard_locked:
            return DeviceReadinessResult(
                success=False,
                error_message="Device is locked. Unlock it manually and start the crawl again.",
                screen_on=state.screen_on,
                keyguard_locked=state.keyguard_locked,
                keyguard_secure=state.keyguard_secure,
            )

        return DeviceReadinessResult(
            success=True,
            screen_on=True,
            keyguard_locked=False,
            keyguard_secure=state.keyguard_secure,
        )

    def click(self, bounds: tuple[int, int, int, int]) -> ActionResult:
        """Execute click action at bounding box center.

        Args:
            bounds: Bounding box (x1, y1, x2, y2)

        Returns:
            ActionResult
        """
        self._ensure_delay()
        center_x, center_y = self._calculate_center(bounds)

        success, output, duration_ms = self._execute_adb_command([
            'shell', 'input', 'tap', str(center_x), str(center_y)
        ])

        return ActionResult(
            success=success,
            action_type="click",
            target=f"({center_x}, {center_y})",
            duration_ms=duration_ms,
            error_message=output if not success else None,
            navigated_away=False
        )

    def input(self, bounds: tuple[int, int, int, int], text: str) -> ActionResult:
        """Execute input action: tap then send text.

        Args:
            bounds: Bounding box (x1, y1, x2, y2)
            text: Text to input

        Returns:
            ActionResult
        """
        self._ensure_delay()
        center_x, center_y = self._calculate_center(bounds)

        # First tap to focus on the input field
        tap_success, tap_output, tap_duration = self._execute_adb_command([
            'shell', 'input', 'tap', str(center_x), str(center_y)
        ])

        if not tap_success:
            return ActionResult(
                success=False,
                action_type="input",
                target=f"({center_x}, {center_y})",
                duration_ms=tap_duration,
                error_message=f"Failed to tap input field: {tap_output}",
                input_text=text
            )

        # Wait for focus
        time.sleep(0.5)

        # Clear existing text (send Ctrl+A then delete)
        self._execute_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_MOVE_END'])
        time.sleep(0.2)
        self._execute_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_CTRL_LEFT'])
        self._execute_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_A'])
        self._execute_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_DEL'])
        time.sleep(0.2)

        # Send the text
        # Escape special characters for shell
        escaped_text = text.replace('"', '\\"').replace("'", "\\'").replace(' ', '%s')

        text_success, text_output, text_duration = self._execute_adb_command([
            'shell', 'input', 'text', escaped_text
        ])

        total_duration = tap_duration + text_duration

        return ActionResult(
            success=text_success,
            action_type="input",
            target=f"({center_x}, {center_y})",
            duration_ms=total_duration,
            error_message=text_output if not text_success else None,
            input_text=text
        )

    def long_press(self, bounds: tuple[int, int, int, int]) -> ActionResult:
        """Execute long press action at bounding box center.

        Args:
            bounds: Bounding box (x1, y1, x2, y2)

        Returns:
            ActionResult
        """
        self._ensure_delay()
        center_x, center_y = self._calculate_center(bounds)

        # ADB swipe with same start/end coordinates and duration creates long press
        success, output, duration_ms = self._execute_adb_command([
            'shell', 'input', 'swipe', str(center_x), str(center_y),
            str(center_x), str(center_y), '1000'  # 1 second duration
        ])

        return ActionResult(
            success=success,
            action_type="long_press",
            target=f"({center_x}, {center_y})",
            duration_ms=duration_ms,
            error_message=output if not success else None,
            navigated_away=False
        )

    def scroll_up(self) -> ActionResult:
        """Execute scroll up action on screen center."""
        self._ensure_delay()
        screen_width, screen_height = self._get_screen_size()
        center_x = screen_width // 2
        start_y = screen_height * 2 // 3  # Start from 2/3 down
        end_y = screen_height // 3      # End at 1/3 down

        success, output, duration_ms = self._execute_adb_command([
            'shell', 'input', 'swipe', str(center_x), str(start_y),
            str(center_x), str(end_y), '300'
        ])

        return ActionResult(
            success=success,
            action_type="scroll_up",
            target="screen_center",
            duration_ms=duration_ms,
            error_message=output if not success else None,
            navigated_away=False
        )

    def scroll_down(self) -> ActionResult:
        """Execute scroll down action on screen center."""
        self._ensure_delay()
        screen_width, screen_height = self._get_screen_size()
        center_x = screen_width // 2
        start_y = screen_height // 3     # Start from 1/3 down
        end_y = screen_height * 2 // 3   # End at 2/3 down

        success, output, duration_ms = self._execute_adb_command([
            'shell', 'input', 'swipe', str(center_x), str(start_y),
            str(center_x), str(end_y), '300'
        ])

        return ActionResult(
            success=success,
            action_type="scroll_down",
            target="screen_center",
            duration_ms=duration_ms,
            error_message=output if not success else None,
            navigated_away=False
        )

    def swipe_left(self) -> ActionResult:
        """Execute left swipe action."""
        self._ensure_delay()
        screen_width, screen_height = self._get_screen_size()
        start_x = screen_width * 2 // 3  # Start from 2/3 right
        end_x = screen_width // 3        # End at 1/3 right
        center_y = screen_height // 2

        success, output, duration_ms = self._execute_adb_command([
            'shell', 'input', 'swipe', str(start_x), str(center_y),
            str(end_x), str(center_y), '300'
        ])

        return ActionResult(
            success=success,
            action_type="scroll_left",
            target="screen_center",
            duration_ms=duration_ms,
            error_message=output if not success else None,
            navigated_away=False
        )

    def swipe_right(self) -> ActionResult:
        """Execute right swipe action."""
        self._ensure_delay()
        screen_width, screen_height = self._get_screen_size()
        start_x = screen_width // 3      # Start from 1/3 right
        end_x = screen_width * 2 // 3    # End at 2/3 right
        center_y = screen_height // 2

        success, output, duration_ms = self._execute_adb_command([
            'shell', 'input', 'swipe', str(start_x), str(center_y),
            str(end_x), str(center_y), '300'
        ])

        return ActionResult(
            success=success,
            action_type="scroll_right",
            target="screen_center",
            duration_ms=duration_ms,
            error_message=output if not success else None,
            navigated_away=False
        )

    def back(self) -> ActionResult:
        """Execute back button action."""
        self._ensure_delay()

        success, output, duration_ms = self._execute_adb_command([
            'shell', 'input', 'keyevent', 'KEYCODE_BACK'
        ])

        return ActionResult(
            success=success,
            action_type="back",
            target="system_back",
            duration_ms=duration_ms,
            error_message=output if not success else None,
            navigated_away=True
        )

    def home(self) -> ActionResult:
        """Execute home button action."""
        self._ensure_delay()

        success, output, duration_ms = self._execute_adb_command([
            'shell', 'input', 'keyevent', 'KEYCODE_HOME'
        ])

        return ActionResult(
            success=success,
            action_type="home",
            target="system_home",
            duration_ms=duration_ms,
            error_message=output if not success else None,
            navigated_away=True
        )

    def recent_apps(self) -> ActionResult:
        """Execute recent apps button action."""
        self._ensure_delay()

        success, output, duration_ms = self._execute_adb_command([
            'shell', 'input', 'keyevent', 'KEYCODE_APP_SWITCH'
        ])

        return ActionResult(
            success=success,
            action_type="recent_apps",
            target="system_recent",
            duration_ms=duration_ms,
            error_message=output if not success else None,
            navigated_away=True
        )

    def hide_keyboard(self) -> ActionResult:
        """Hide the on-screen keyboard."""
        success, output, duration_ms = self._execute_adb_command([
            'shell', 'input', 'keyevent', 'KEYCODE_BACK'
        ])

        return ActionResult(
            success=success,
            action_type="hide_keyboard",
            target="system_keyboard",
            duration_ms=duration_ms,
            error_message=output if not success else None,
            navigated_away=False
        )

    def take_screenshot(self, output_path: str) -> ActionResult:
        """Take a screenshot and save to specified path.

        Args:
            output_path: Local file path to save screenshot

        Returns:
            ActionResult indicating success/failure
        """
        # Take screenshot to device
        success, output, duration_ms = self._execute_adb_command([
            'shell', 'screencap', '/sdcard/screenshot.png'
        ], timeout=15.0)

        if not success:
            return ActionResult(
                success=False,
                action_type="screenshot",
                target=output_path,
                duration_ms=duration_ms,
                error_message=f"Failed to capture screenshot: {output}"
            )

        # Pull screenshot from device
        pull_success, pull_output, pull_duration = self._execute_adb_command([
            'pull', '/sdcard/screenshot.png', output_path
        ], timeout=15.0)

        total_duration = duration_ms + pull_duration

        if pull_success:
            # Clean up device screenshot
            self._execute_adb_command(['shell', 'rm', '/sdcard/screenshot.png'])

        return ActionResult(
            success=pull_success,
            action_type="screenshot",
            target=output_path,
            duration_ms=total_duration,
            error_message=pull_output if not pull_success else None
        )

    def get_current_package(self) -> str | None:
        """Get the currently focused app package.

        Uses adb shell with a single command string (pipe processed on device)
        to avoid the bug where '|' was passed as a literal subprocess argument.

        Returns:
            Package name of current app or None if failed
        """
        try:
            success, output, _ = self._execute_adb_command([
                'shell', 'dumpsys window | grep -E mCurrentFocus'
            ])

            if success and output:
                match = re.search(r'([a-zA-Z0-9_.]+)/([a-zA-Z0-9_.]+)', output)
                if match:
                    return match.group(1)
            return None

        except Exception as e:
            logger.error(f"Failed to get current package: {e}")
            return None

    def get_current_activity(self) -> str | None:
        """Get the currently focused app activity component.

        Extracts the activity name from dumpsys window output, returning
        the component after the '/' (e.g., 'com.example.app.MainActivity').

        Returns:
            Activity component string, or None if extraction fails.
        """
        try:
            success, output, _ = self._execute_adb_command([
                'shell', 'dumpsys window | grep -E mCurrentFocus'
            ])

            if success and output:
                match = re.search(r'([a-zA-Z0-9_.]+)/([a-zA-Z0-9_.]+)', output)
                if match:
                    # Return the full activity component: package.activity
                    activity = match.group(2)
                    # Remove trailing } or ) that may appear in dumpsys output
                    activity = activity.rstrip('})')
                    return activity
            return None

        except Exception as e:
            logger.error(f"Failed to get current activity: {e}")
            return None

    def get_resumed_activity(self) -> tuple[str, str] | None:
        """Get the resumed (foreground) activity from ActivityManager.

        Uses dumpsys activity activities to capture the resumed activity,
        which is often more reliable than window focus when launch is
        intercepted by another app (e.g., Play Store).

        Returns:
            Tuple of (package, activity) or None if not found.
        """
        try:
            success, output, _ = self._execute_adb_command([
                'shell', 'dumpsys activity activities | grep -E "mResumedActivity|ResumedActivity"'
            ])

            if success and output:
                match = re.search(r'([a-zA-Z0-9_.]+)/([a-zA-Z0-9_.]+)', output)
                if match:
                    activity = match.group(2).rstrip('})')
                    return match.group(1), activity
            return None

        except Exception as e:
            logger.error(f"Failed to get resumed activity: {e}")
            return None

    def force_stop_package(self, package_name: str) -> ActionResult:
        """Force-stop a package via ActivityManager.

        Args:
            package_name: Package name to stop

        Returns:
            ActionResult indicating success/failure
        """
        success, output, duration_ms = self._execute_adb_command([
            'shell', 'am', 'force-stop', package_name
        ])

        return ActionResult(
            success=success,
            action_type="force_stop",
            target=package_name,
            duration_ms=duration_ms,
            error_message=output if not success else None,
            navigated_away=False
        )

    def resolve_launcher_activity(self, package_name: str) -> str | None:
        """Resolve the main launcher activity for a given package.

        Per D-07: Always recovers to the main launcher activity, never a deep activity.
        Uses adb shell cmd package resolve-activity first, falls back to
        dumpsys package parsing if resolution fails. Results are cached
        per package so we only resolve once.

        Args:
            package_name: App package name (e.g., 'com.example.app').

        Returns:
            Launcher activity component (e.g., '.MainActivity') or None if
            resolution fails.
        """
        # Return cached result if available
        if package_name in self._launcher_activity_cache:
            return self._launcher_activity_cache[package_name]

        # Primary method: resolve-activity --brief
        try:
            success, output, _ = self._execute_adb_command([
                'shell',
                'cmd package resolve-activity --brief '
                '-c android.intent.category.LAUNCHER ' + package_name,
            ])

            if success and output:
                lines = output.strip().split('\n')
                # Output format:
                #   Line 0: category header (e.g., "android.intent.category.LAUNCHER")
                #   Line 1: component (e.g., "com.example.app/com.example.app.MainActivity")
                for line in lines:
                    line = line.strip()
                    if line and '/' in line:
                        # Extract activity part after the slash
                        _, activity = line.rsplit('/', 1)
                        activity = activity.strip()
                        if activity:
                            self._launcher_activity_cache[package_name] = activity
                            logger.debug(
                                f"Resolved launcher activity for {package_name}: "
                                f"{activity} (via resolve-activity)"
                            )
                            return activity
        except Exception as e:
            logger.debug(f"resolve-activity failed for {package_name}: {e}")

        # Fallback method: dumpsys package parsing for MAIN+LAUNCHER intent filter
        try:
            success, output, _ = self._execute_adb_command([
                'shell',
                f'dumpsys package {package_name}',
            ])

            if success and output:
                # Search for MAIN action followed by LAUNCHER category
                lines = output.strip().split('\n')
                found_main = False
                for line in lines:
                    stripped = line.strip()
                    if 'android.intent.action.MAIN' in stripped:
                        found_main = True
                        continue
                    if found_main and 'android.intent.category.LAUNCHER' in stripped:
                        # The activity name is typically in a preceding
                        # "Activity" line or we scan backwards
                        continue
                    if found_main:
                        # Look for the activity component pattern
                        match = re.search(
                            rf'{re.escape(package_name)}/([a-zA-Z0-9_.]+)',
                            stripped,
                        )
                        if match:
                            activity = match.group(1)
                            self._launcher_activity_cache[package_name] = activity
                            logger.debug(
                                f"Resolved launcher activity for {package_name}: "
                                f"{activity} (via dumpsys)"
                            )
                            return activity
                        found_main = False
        except Exception as e:
            logger.debug(f"dumpsys package fallback failed for {package_name}: {e}")

        logger.warning(f"Could not resolve launcher activity for {package_name}")
        return None

    def am_start_recovery(self, package_name: str) -> ActionResult:
        """Recover from an app switch by relaunching the target app.

        Per D-05: Uses `adb shell am start` with the launcher activity to
        navigate back to the target app. Per D-07: always launches to the
        main launcher activity, never a deep activity. Falls back to monkey
        if launcher activity resolution fails.

        Args:
            package_name: App package name to recover to.

        Returns:
            ActionResult with action_type="am_start_recovery" and navigated_away
            set to False (we're navigating *back* to the target app).
        """
        launcher_activity = self.resolve_launcher_activity(package_name)

        time.time()

        if launcher_activity:
            # Primary path: am start with resolved launcher activity (per D-05)
            success, output, duration_ms = self._execute_adb_command([
                'shell',
                f'am start -n {package_name}/{launcher_activity}',
            ])

            # Add post-launch delay to allow activity to start (per D-07)
            time.sleep(0.5)

            return ActionResult(
                success=success,
                action_type="am_start_recovery",
                target=f"{package_name}/{launcher_activity}",
                duration_ms=duration_ms,
                error_message=output if not success else None,
                navigated_away=False,
            )
        else:
            # Fallback: monkey launcher (if resolver fails)
            success, output, duration_ms = self._execute_adb_command([
                'shell', 'monkey', '-p', package_name, '-c',
                'android.intent.category.LAUNCHER', '1',
            ])

            # Add post-launch delay for monkey fallback too
            time.sleep(0.5)

            return ActionResult(
                success=success,
                action_type="am_start_recovery",
                target=package_name,
                duration_ms=duration_ms,
                error_message=output if not success else None,
                navigated_away=False,
            )

    def launch_app(self, package_name: str) -> ActionResult:
        """Launch an app by package name.

        Args:
            package_name: App package name to launch

        Returns:
            ActionResult indicating success/failure
        """
        success, output, duration_ms = self._execute_adb_command([
            'shell', 'monkey', '-p', package_name, '-c',
            'android.intent.category.LAUNCHER', '1'
        ])

        return ActionResult(
            success=success,
            action_type="launch_app",
            target=package_name,
            duration_ms=duration_ms,
            error_message=output if not success else None,
            navigated_away=True
        )
