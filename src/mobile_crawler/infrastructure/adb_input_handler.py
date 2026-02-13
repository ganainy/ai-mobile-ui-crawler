"""ADB input handler for text input without XML/DOM access."""

import subprocess
import shlex
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ADBInputHandler:
    """Handles text input via ADB shell commands without accessing DOM/XML.

    This handler provides text input capabilities using ADB's shell input command,
    which bypasses the need for find_element or XML page source access.
    """

    def __init__(self, device_id: Optional[str] = None):
        """Initialize ADB input handler.

        Args:
            device_id: Optional device ID for multi-device setups
        """
        self.device_id = device_id

    def _build_adb_command(self, command: str) -> list[str]:
        """Build ADB command with optional device ID.

        Args:
            command: The shell command to execute

        Returns:
            List of command parts for subprocess
        """
        if self.device_id:
            return ["adb", "-s", self.device_id, "shell", command]
        return ["adb", "shell", command]

    def input_text(self, text: str) -> bool:
        """Send text input via ADB shell.

        Args:
            text: Text to input (will be escaped for shell)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Escape special characters for shell
            # Replace spaces with %s, other special chars may need handling
            escaped_text = self._escape_text_for_adb(text)
            command = f"input text {shlex.quote(escaped_text)}"
            result = subprocess.run(
                self._build_adb_command(command),
                capture_output=True,
                text=True,
                timeout=10
            )
            success = result.returncode == 0
            if not success:
                logger.warning(f"ADB input text failed: {result.stderr}")
            return success
        except subprocess.TimeoutExpired:
            logger.error("ADB input text timed out")
            return False
        except Exception as e:
            logger.error(f"ADB input text error: {e}")
            return False

    def input_keycode(self, keycode: int) -> bool:
        """Send a keycode event via ADB.

        Args:
            keycode: Android keycode (e.g., 66 for Enter, 67 for Backspace)

        Returns:
            True if successful, False otherwise
        """
        try:
            command = f"input keyevent {keycode}"
            result = subprocess.run(
                self._build_adb_command(command),
                capture_output=True,
                text=True,
                timeout=5
            )
            success = result.returncode == 0
            if not success:
                logger.warning(f"ADB input keycode {keycode} failed: {result.stderr}")
            return success
        except subprocess.TimeoutExpired:
            logger.error(f"ADB input keycode {keycode} timed out")
            return False
        except Exception as e:
            logger.error(f"ADB input keycode {keycode} error: {e}")
            return False

    def clear_text_field(self) -> bool:
        """Clear text field using backspace key events.

        Note: This is a best-effort approach. The number of backspaces
        is arbitrary and may not clear all text.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Send a reasonable number of backspace events
            # This is a heuristic - in practice, you might want to detect
            # the current text length first
            for _ in range(50):
                if not self.input_keycode(67):  # KEYCODE_DEL
                    break
            return True
        except Exception as e:
            logger.error(f"ADB clear text field error: {e}")
            return False

    def press_enter(self) -> bool:
        """Press Enter key.

        Returns:
            True if successful, False otherwise
        """
        return self.input_keycode(66)  # KEYCODE_ENTER

    def press_backspace(self) -> bool:
        """Press Backspace key.

        Returns:
            True if successful, False otherwise
        """
        return self.input_keycode(67)  # KEYCODE_DEL

    def _escape_text_for_adb(self, text: str) -> str:
        """Escape text for ADB input command.

        ADB input text has limitations:
        - Spaces should be replaced with %s
        - Some special characters may not work

        Args:
            text: Original text

        Returns:
            Escaped text suitable for ADB input
        """
        # Replace spaces with %s (ADB shell input text format)
        escaped = text.replace(" ", "%s")
        # Note: Other special characters like quotes, backslashes, etc.
        # may need additional handling depending on the Android version
        return escaped

    def test_connection(self) -> bool:
        """Test if ADB connection is working.

        Returns:
            True if ADB is responsive, False otherwise
        """
        try:
            result = subprocess.run(
                self._build_adb_command("echo test"),
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
