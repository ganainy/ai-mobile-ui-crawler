"""Tests for ADB input handling.

All subprocess calls to ADB are mocked.
"""

import subprocess
from unittest.mock import Mock, patch

import pytest

from mobile_crawler.infrastructure.adb_input_handler import ADBInputHandler


class TestADBInputHandlerInitialization:
    """Tests for ADBInputHandler initialization."""

    def test_init_without_device_id(self):
        """Test initialization without device_id."""
        handler = ADBInputHandler()
        assert handler.device_id is None

    def test_init_with_device_id(self):
        """Test initialization with device_id."""
        handler = ADBInputHandler(device_id="emulator-5554")
        assert handler.device_id == "emulator-5554"


class TestADBInputHandlerCommands:
    """Tests for ADB command building and execution."""

    def test_build_adb_command_without_device(self):
        """Test command building without device_id."""
        handler = ADBInputHandler()
        cmd = handler._build_adb_command("input text hello")
        assert cmd == ["adb", "shell", "input text hello"]

    def test_build_adb_command_with_device(self):
        """Test command building with device_id."""
        handler = ADBInputHandler(device_id="emulator-5554")
        cmd = handler._build_adb_command("input text hello")
        assert cmd == ["adb", "-s", "emulator-5554", "shell", "input text hello"]

    @patch('mobile_crawler.infrastructure.adb_input_handler.subprocess.run')
    def test_input_text_success(self, mock_subprocess):
        """Test input_text sends correct command and returns True on success."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        handler = ADBInputHandler(device_id="test_device")
        result = handler.input_text("hello world")

        assert result is True
        cmd = mock_subprocess.call_args[0][0]
        assert "input text" in cmd[-1]

    @patch('mobile_crawler.infrastructure.adb_input_handler.subprocess.run')
    def test_input_text_failure(self, mock_subprocess):
        """Test input_text returns False on failure."""
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="error")

        handler = ADBInputHandler()
        result = handler.input_text("hello")

        assert result is False

    @patch('mobile_crawler.infrastructure.adb_input_handler.subprocess.run')
    def test_input_text_timeout(self, mock_subprocess):
        """Test input_text handles timeout."""
        mock_subprocess.side_effect = subprocess.TimeoutExpired(cmd=['adb'], timeout=10)

        handler = ADBInputHandler()
        result = handler.input_text("hello")

        assert result is False

    @patch('mobile_crawler.infrastructure.adb_input_handler.subprocess.run')
    def test_input_text_exception(self, mock_subprocess):
        """Test input_text handles exceptions."""
        mock_subprocess.side_effect = Exception("adb error")

        handler = ADBInputHandler()
        result = handler.input_text("hello")

        assert result is False

    @patch('mobile_crawler.infrastructure.adb_input_handler.subprocess.run')
    def test_input_keycode(self, mock_subprocess):
        """Test input_keycode sends correct command."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        handler = ADBInputHandler()
        result = handler.input_keycode(66)  # KEYCODE_ENTER

        assert result is True
        cmd = mock_subprocess.call_args[0][0]
        assert "keyevent 66" in cmd[-1]

    @patch('mobile_crawler.infrastructure.adb_input_handler.subprocess.run')
    def test_press_enter(self, mock_subprocess):
        """Test press_enter sends KEYCODE_ENTER."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        handler = ADBInputHandler()
        result = handler.press_enter()

        assert result is True
        cmd = mock_subprocess.call_args[0][0]
        assert "keyevent 66" in cmd[-1]

    @patch('mobile_crawler.infrastructure.adb_input_handler.subprocess.run')
    def test_press_backspace(self, mock_subprocess):
        """Test press_backspace sends KEYCODE_DEL."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        handler = ADBInputHandler()
        result = handler.press_backspace()

        assert result is True
        cmd = mock_subprocess.call_args[0][0]
        assert "keyevent 67" in cmd[-1]

    @patch('mobile_crawler.infrastructure.adb_input_handler.subprocess.run')
    def test_clear_text_field(self, mock_subprocess):
        """Test clear_text_field sends multiple backspace events."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        handler = ADBInputHandler()
        result = handler.clear_text_field()

        assert result is True
        # Should call input_keycode multiple times
        assert mock_subprocess.call_count == 50  # Sends 50 backspaces

    @patch('mobile_crawler.infrastructure.adb_input_handler.subprocess.run')
    def test_clear_text_field_handles_failure(self, mock_subprocess):
        """Test clear_text_field stops on failure."""
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="error")

        handler = ADBInputHandler()
        result = handler.clear_text_field()

        # Should return True even if some backspaces fail (breaks on first failure)
        assert result is True
        assert mock_subprocess.call_count == 1  # Breaks after first failure


class TestADBInputHandlerTextEscaping:
    """Tests for text escaping."""

    def test_escape_text_replaces_spaces(self):
        """Test _escape_text_for_adb replaces spaces with %s."""
        handler = ADBInputHandler()
        escaped = handler._escape_text_for_adb("hello world")
        assert escaped == "hello%sworld"

    def test_escape_text_preserves_other_chars(self):
        """Test _escape_text_for_adb preserves non-space characters."""
        handler = ADBInputHandler()
        escaped = handler._escape_text_for_adb("abc123")
        assert escaped == "abc123"

    @patch('mobile_crawler.infrastructure.adb_input_handler.subprocess.run')
    def test_input_text_with_special_chars(self, mock_subprocess):
        """Test input_text handles special characters via shlex.quote."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        handler = ADBInputHandler()
        result = handler.input_text('hello "world"')

        assert result is True
        cmd = mock_subprocess.call_args[0][0]
        # shlex.quote should wrap the text appropriately
        assert "input text" in cmd[-1]


class TestADBInputHandlerConnection:
    """Tests for connection testing."""

    @patch('mobile_crawler.infrastructure.adb_input_handler.subprocess.run')
    def test_test_connection_success(self, mock_subprocess):
        """Test test_connection returns True on success."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="test\n", stderr="")

        handler = ADBInputHandler()
        result = handler.test_connection()

        assert result is True

    @patch('mobile_crawler.infrastructure.adb_input_handler.subprocess.run')
    def test_test_connection_failure(self, mock_subprocess):
        """Test test_connection returns False on failure."""
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="error")

        handler = ADBInputHandler()
        result = handler.test_connection()

        assert result is False

    @patch('mobile_crawler.infrastructure.adb_input_handler.subprocess.run')
    def test_test_connection_exception(self, mock_subprocess):
        """Test test_connection returns False on exception."""
        mock_subprocess.side_effect = Exception("adb not found")

        handler = ADBInputHandler()
        result = handler.test_connection()

        assert result is False
