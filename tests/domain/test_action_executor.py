"""Unit tests for ADBActionExecutor."""

from unittest.mock import MagicMock, patch

import pytest

from mobile_crawler.domain.adb_action_executor import ADBActionExecutor


class TestADBActionExecutor:
    @pytest.fixture
    def executor(self):
        return ADBActionExecutor(device_id="test_device")

    @patch("subprocess.run")
    def test_click_executes_adb_tap(self, mock_run, executor):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = executor.click((100, 200, 300, 400))
        assert result.success is True
        assert result.action_type == "click"
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd == ['adb', '-s', 'test_device', 'shell', 'input', 'tap', '200', '300']

    @patch("subprocess.run")
    def test_scroll_up_executes_adb_swipe(self, mock_run, executor):
        mock_run.return_value = MagicMock(returncode=0, stdout="Physical size: 1080x1920", stderr="")
        result = executor.scroll_up()
        assert result.success is True
        assert result.action_type == "scroll_up"

    @patch("subprocess.run")
    def test_back_executes_keyevent(self, mock_run, executor):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = executor.back()
        assert result.success is True
        assert result.action_type == "back"
        assert result.navigated_away is True
        cmd = mock_run.call_args[0][0]
        assert "KEYCODE_BACK" in cmd

    @patch("subprocess.run")
    def test_screenshot_pulls_file(self, mock_run, executor):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = executor.take_screenshot("/tmp/test.png")
        assert result.success is True
        assert result.action_type == "screenshot"
        calls = [c[0][0] for c in mock_run.call_args_list]
        assert any("screencap" in c for c in calls)
        assert any("pull" in c for c in calls)

    @patch("subprocess.run")
    def test_click_failure_returns_error(self, mock_run, executor):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="device offline")
        result = executor.click((0, 0, 10, 10))
        assert result.success is False
        assert "device offline" in result.error_message

    @patch("subprocess.run")
    def test_input_taps_then_sends_text(self, mock_run, executor):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = executor.input((100, 200, 300, 400), "hello")
        assert result.success is True
        assert result.action_type == "input"
        assert result.input_text == "hello"
