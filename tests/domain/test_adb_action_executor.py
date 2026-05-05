"""Tests for ADB action execution and error recovery.

All subprocess calls to ADB are mocked to avoid invoking real ADB.
"""

from unittest.mock import Mock, patch

import pytest

from mobile_crawler.domain.adb_action_executor import ADBActionExecutor
from mobile_crawler.domain.models import ActionResult


@pytest.fixture
def executor():
    """Create an ADBActionExecutor with mocked ADB client."""
    with patch('mobile_crawler.domain.adb_action_executor.ADBClient'):
        exec = ADBActionExecutor(device_id="test_device")
        return exec


class TestADBActionExecutorInitialization:
    """Tests for ADBActionExecutor initialization."""

    def test_init_with_device_id(self):
        """Test initialization with device_id."""
        with patch('mobile_crawler.domain.adb_action_executor.ADBClient'):
            exec = ADBActionExecutor(device_id="emulator-5554")
            assert exec.device_id == "emulator-5554"
            assert exec._action_delay_ms == 1500

    def test_init_with_custom_adb_client(self):
        """Test initialization with custom ADB client."""
        mock_client = Mock()
        exec = ADBActionExecutor(device_id="test", adb_client=mock_client)
        assert exec.adb_client == mock_client


class TestADBActionExecutorTap:
    """Tests for tap/click actions."""

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_click_sends_adb_tap(self, mock_subprocess, executor):
        """Test click sends correct ADB tap command."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        result = executor.click((10, 20, 110, 120))

        mock_subprocess.assert_called_once()
        cmd = mock_subprocess.call_args[0][0]
        assert 'tap' in cmd
        assert str(60) in cmd  # center_x
        assert str(70) in cmd  # center_y
        assert isinstance(result, ActionResult)
        assert result.success is True
        assert result.action_type == "click"

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_click_failure(self, mock_subprocess, executor):
        """Test click handles subprocess failure."""
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="device offline")

        result = executor.click((10, 20, 110, 120))

        assert result.success is False
        assert result.error_message == "device offline"

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_long_press_sends_swipe(self, mock_subprocess, executor):
        """Test long_press sends ADB swipe with duration."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        result = executor.long_press((10, 20, 110, 120))

        cmd = mock_subprocess.call_args[0][0]
        assert 'swipe' in cmd
        assert '1000' in cmd  # duration
        assert result.action_type == "long_press"


class TestADBActionExecutorInput:
    """Tests for text input actions."""

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_input_sends_tap_then_text(self, mock_subprocess, executor):
        """Test input sends tap followed by text command."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        result = executor.input((10, 20, 110, 120), "hello world")

        calls = mock_subprocess.call_args_list
        # Should have tap command first, then text command
        assert any('tap' in c[0][0] for c in calls)
        assert any('text' in c[0][0] for c in calls)
        assert result.action_type == "input"
        assert result.input_text == "hello world"

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_input_tap_failure(self, mock_subprocess, executor):
        """Test input handles tap failure gracefully."""
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="tap failed")

        result = executor.input((10, 20, 110, 120), "hello")

        assert result.success is False
        assert "Failed to tap input field" in result.error_message

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_input_escapes_special_chars(self, mock_subprocess, executor):
        """Test input escapes special characters for shell."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        executor.input((10, 20, 110, 120), 'hello "world"')

        calls = mock_subprocess.call_args_list
        text_call = [c for c in calls if 'text' in c[0][0]]
        assert len(text_call) > 0


class TestADBActionExecutorScroll:
    """Tests for scroll actions."""

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_scroll_up(self, mock_subprocess, executor):
        """Test scroll_up sends correct swipe command."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        result = executor.scroll_up()

        cmd = mock_subprocess.call_args[0][0]
        assert 'swipe' in cmd
        assert result.action_type == "scroll_up"
        assert result.success is True

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_scroll_down(self, mock_subprocess, executor):
        """Test scroll_down sends correct swipe command."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        result = executor.scroll_down()

        cmd = mock_subprocess.call_args[0][0]
        assert 'swipe' in cmd
        assert result.action_type == "scroll_down"

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_swipe_left(self, mock_subprocess, executor):
        """Test swipe_left sends correct swipe command."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        result = executor.swipe_left()

        cmd = mock_subprocess.call_args[0][0]
        assert 'swipe' in cmd
        assert result.action_type == "scroll_left"

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_swipe_right(self, mock_subprocess, executor):
        """Test swipe_right sends correct swipe command."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        result = executor.swipe_right()

        cmd = mock_subprocess.call_args[0][0]
        assert 'swipe' in cmd
        assert result.action_type == "scroll_right"


class TestADBActionExecutorNavigation:
    """Tests for navigation actions."""

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_back(self, mock_subprocess, executor):
        """Test back sends KEYCODE_BACK."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        result = executor.back()

        cmd = mock_subprocess.call_args[0][0]
        assert 'KEYCODE_BACK' in cmd
        assert result.action_type == "back"
        assert result.navigated_away is True

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_home(self, mock_subprocess, executor):
        """Test home sends KEYCODE_HOME."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        result = executor.home()

        cmd = mock_subprocess.call_args[0][0]
        assert 'KEYCODE_HOME' in cmd
        assert result.action_type == "home"
        assert result.navigated_away is True

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_recent_apps(self, mock_subprocess, executor):
        """Test recent_apps sends KEYCODE_APP_SWITCH."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        result = executor.recent_apps()

        cmd = mock_subprocess.call_args[0][0]
        assert 'KEYCODE_APP_SWITCH' in cmd
        assert result.action_type == "recent_apps"

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_hide_keyboard(self, mock_subprocess, executor):
        """Test hide_keyboard sends KEYCODE_BACK."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        result = executor.hide_keyboard()

        cmd = mock_subprocess.call_args[0][0]
        assert 'KEYCODE_BACK' in cmd
        assert result.action_type == "hide_keyboard"


class TestADBActionExecutorScreenshot:
    """Tests for screenshot action."""

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_take_screenshot(self, mock_subprocess, executor):
        """Test take_screenshot captures and pulls screenshot."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        result = executor.take_screenshot("/tmp/screenshot.png")

        calls = mock_subprocess.call_args_list
        assert any('screencap' in c[0][0] for c in calls)
        assert any('pull' in c[0][0] for c in calls)
        assert result.action_type == "screenshot"

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_take_screenshot_capture_failure(self, mock_subprocess, executor):
        """Test take_screenshot handles capture failure."""
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="permission denied")

        result = executor.take_screenshot("/tmp/screenshot.png")

        assert result.success is False
        assert "Failed to capture screenshot" in result.error_message


class TestADBActionExecutorPackageDetection:
    """Tests for package/activity detection."""

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_get_current_package(self, mock_subprocess, executor):
        """Test get_current_package parses package from dumpsys."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="mCurrentFocus=Window{12345 u0 com.example.app/com.example.app.MainActivity}",
            stderr=""
        )

        package = executor.get_current_package()

        assert package == "com.example.app"

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_get_current_package_failure(self, mock_subprocess, executor):
        """Test get_current_package returns None on failure."""
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="error")

        package = executor.get_current_package()

        assert package is None

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_get_current_activity(self, mock_subprocess, executor):
        """Test get_current_activity parses activity from dumpsys."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="mCurrentFocus=Window{12345 u0 com.example.app/com.example.app.MainActivity}",
            stderr=""
        )

        activity = executor.get_current_activity()

        assert activity == "com.example.app.MainActivity"


class TestADBActionExecutorLauncherActivity:
    """Tests for launcher activity resolution."""

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_resolve_launcher_activity(self, mock_subprocess, executor):
        """Test resolve_launcher_activity parses activity from resolve-activity."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="android.intent.category.LAUNCHER\ncom.example.app/com.example.app.MainActivity",
            stderr=""
        )

        activity = executor.resolve_launcher_activity("com.example.app")

        assert activity == "com.example.app.MainActivity"

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_resolve_launcher_activity_fallback(self, mock_subprocess, executor):
        """Test resolve_launcher_activity falls back to dumpsys."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="android.intent.action.MAIN\n  android.intent.category.LAUNCHER\ncom.example.app/com.example.app.MainActivity",
            stderr=""
        )

        activity = executor.resolve_launcher_activity("com.example.app")

        assert activity == "com.example.app.MainActivity"

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_resolve_launcher_activity_failure(self, mock_subprocess, executor):
        """Test resolve_launcher_activity returns None on failure."""
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="error")

        activity = executor.resolve_launcher_activity("com.example.app")

        assert activity is None

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_resolve_launcher_activity_caching(self, mock_subprocess, executor):
        """Test resolve_launcher_activity caches results."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="com.example.app/com.example.app.MainActivity",
            stderr=""
        )

        activity1 = executor.resolve_launcher_activity("com.example.app")
        activity2 = executor.resolve_launcher_activity("com.example.app")

        # Should only call subprocess once due to caching
        assert mock_subprocess.call_count == 1
        assert activity1 == activity2


class TestADBActionExecutorRecovery:
    """Tests for app recovery actions."""

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_am_start_recovery(self, mock_subprocess, executor):
        """Test am_start_recovery launches app with resolved activity."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="com.example.app/com.example.app.MainActivity",
            stderr=""
        )

        result = executor.am_start_recovery("com.example.app")

        assert result.action_type == "am_start_recovery"
        assert result.success is True
        cmd = mock_subprocess.call_args_list[-1][0][0]
        assert 'am start' in ' '.join(cmd)

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_am_start_recovery_monkey_fallback(self, mock_subprocess, executor):
        """Test am_start_recovery falls back to monkey when activity unresolved."""
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="error")

        result = executor.am_start_recovery("com.example.app")

        assert result.action_type == "am_start_recovery"
        # Falls back to monkey
        cmd = mock_subprocess.call_args_list[-1][0][0]
        assert 'monkey' in cmd

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_launch_app(self, mock_subprocess, executor):
        """Test launch_app sends monkey command."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        result = executor.launch_app("com.example.app")

        cmd = mock_subprocess.call_args[0][0]
        assert 'monkey' in cmd
        assert 'com.example.app' in cmd
        assert result.action_type == "launch_app"
        assert result.navigated_away is True


class TestADBActionExecutorErrorHandling:
    """Tests for error handling."""

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_subprocess_timeout(self, mock_subprocess, executor):
        """Test subprocess timeout is handled gracefully."""
        import subprocess
        mock_subprocess.side_effect = subprocess.TimeoutExpired(cmd=['adb'], timeout=10)

        result = executor.click((10, 20, 110, 120))

        assert result.success is False
        assert "timed out" in result.error_message.lower()

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_subprocess_exception(self, mock_subprocess, executor):
        """Test generic subprocess exceptions are handled."""
        mock_subprocess.side_effect = Exception("adb not found")

        result = executor.click((10, 20, 110, 120))

        assert result.success is False
        assert "adb not found" in result.error_message

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_get_screen_size_fallback(self, mock_subprocess, executor):
        """Test get_screen_size falls back to default on failure."""
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="error")

        width, height = executor._get_screen_size()

        assert width == 1080
        assert height == 1920

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    def test_get_screen_size_parses_output(self, mock_subprocess, executor):
        """Test get_screen_size parses Physical size from output."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="Physical size: 1440x3200",
            stderr=""
        )

        width, height = executor._get_screen_size()

        assert width == 1440
        assert height == 3200


class TestADBActionExecutorDelay:
    """Tests for action delay."""

    @patch('mobile_crawler.domain.adb_action_executor.subprocess.run')
    @patch('mobile_crawler.domain.adb_action_executor.time.time')
    @patch('mobile_crawler.domain.adb_action_executor.time.sleep')
    def test_ensure_delay_enforces_minimum(self, mock_sleep, mock_time, mock_subprocess, executor):
        """Test _ensure_delay enforces minimum delay between actions."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        # Simulate very fast successive calls
        mock_time.side_effect = [0, 100, 100, 100]

        executor._last_action_time = 0
        executor.click((10, 20, 110, 120))

        # Should have called sleep because not enough time elapsed
        mock_sleep.assert_called_once()
