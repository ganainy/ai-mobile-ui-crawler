"""Tests for TrafficCaptureManager."""

from unittest.mock import Mock, patch, MagicMock
from subprocess import CompletedProcess
import pytest

from mobile_crawler.domain.traffic_capture_manager import (
    TrafficCaptureManager,
    TrafficCaptureConfig,
)
import subprocess


class TestTrafficCaptureConfig:
    """Tests for TrafficCaptureConfig dataclass."""

    def test_creation(self):
        """Test TrafficCaptureConfig creation."""
        config = TrafficCaptureConfig(
            enabled=True,
            pcapdroid_package="com.test.pcapdroid",
            output_path="/test/path.pcap",
        )

        assert config.enabled is True
        assert config.pcapdroid_package == "com.test.pcapdroid"
        assert config.output_path == "/test/path.pcap"

    def test_defaults(self):
        """Test TrafficCaptureConfig with defaults."""
        config = TrafficCaptureConfig(enabled=False)

        assert config.enabled is False
        assert config.pcapdroid_package == "com.emanuelef.android.apps.pcapdroid"
        assert config.output_path is None


class TestTrafficCaptureManager:
    """Tests for TrafficCaptureManager."""

    def test_init(self):
        """Test initialization."""
        adb_client = Mock()
        manager = TrafficCaptureManager(adb_client=adb_client)

        assert manager._adb_client is adb_client
        assert manager._is_capturing is False
        assert manager._pcapdroid_installed is None
        assert manager._config is None

    @patch("subprocess.run")
    def test_is_installed_true(self, mock_run):
        """Test is_installed when PCAPdroid is installed."""
        mock_run.return_value = CompletedProcess(
            args=["adb", "shell", "pm", "list", "packages"],
            returncode=0,
            stdout="com.emanuelef.android.apps.pcapdroid"
        )
        manager = TrafficCaptureManager()

        result = manager.is_installed()

        assert result is True
        assert manager._pcapdroid_installed is True

    @patch("subprocess.run")
    def test_is_installed_false(self, mock_run):
        """Test is_installed when PCAPdroid is not installed."""
        mock_run.return_value = CompletedProcess(
            args=["adb", "shell", "pm", "list", "packages"],
            returncode=0,
            stdout=""
        )
        manager = TrafficCaptureManager()

        result = manager.is_installed()

        assert result is False
        assert manager._pcapdroid_installed is False

    @patch("subprocess.run")
    def test_is_installed_cached(self, mock_run):
        """Test that is_installed caches result."""
        mock_run.return_value = CompletedProcess(
            args=["adb", "shell", "pm", "list", "packages"],
            returncode=0,
            stdout="com.emanuelef.android.apps.pcapdroid"
        )
        manager = TrafficCaptureManager()

        # First call
        result1 = manager.is_installed()
        assert result1 is True

        # Second call should use cache
        result2 = manager.is_installed()
        assert result2 is True
        # Should only call subprocess once
        assert mock_run.call_count == 1

    @patch("subprocess.run")
    def test_is_installed_error(self, mock_run):
        """Test is_installed handles errors gracefully."""
        mock_run.side_effect = Exception("ADB error")
        manager = TrafficCaptureManager()

        result = manager.is_installed()

        assert result is False
        assert manager._pcapdroid_installed is False

    def test_configure(self):
        """Test configure method."""
        config = TrafficCaptureConfig(enabled=True, output_path="/test.pcap")
        manager = TrafficCaptureManager()

        manager.configure(config)

        assert manager._config is config

    def test_start_disabled(self):
        """Test start when capture is disabled."""
        config = TrafficCaptureConfig(enabled=False)
        manager = TrafficCaptureManager()
        manager.configure(config)

        result = manager.start()

        assert result is False
        assert manager._is_capturing is False

    @patch("subprocess.run")
    def test_start_not_installed(self, mock_run):
        """Test start when PCAPdroid is not installed."""
        mock_run.return_value = CompletedProcess(
            args=["adb", "shell", "pm", "list", "packages"],
            returncode=0,
            stdout=""
        )
        config = TrafficCaptureConfig(enabled=True)
        manager = TrafficCaptureManager()
        manager.configure(config)

        result = manager.start()

        assert result is False
        assert manager._is_capturing is False

    @patch("subprocess.run")
    def test_start_success(self, mock_run):
        """Test successful start of traffic capture."""
        # Configure ADB client mock to return string
        adb_client = Mock()
        adb_client.execute.return_value = "com.emanuelef.android.apps.pcapdroid"
        
        config = TrafficCaptureConfig(enabled=True)
        manager = TrafficCaptureManager(adb_client=adb_client)
        manager.configure(config)

        result = manager.start()

        assert result is True
        assert manager._is_capturing is True

    @patch("subprocess.run")
    def test_start_failure(self, mock_run):
        """Test start failure."""
        mock_run.side_effect = Exception("ADB command failed")
        config = TrafficCaptureConfig(enabled=True)
        manager = TrafficCaptureManager(adb_client=Mock())
        manager.configure(config)

        result = manager.start()

        assert result is False
        assert manager._is_capturing is False

    @patch("subprocess.run")
    @patch("time.strftime")
    def test_stop_and_pull_with_default_path(self, mock_strftime, mock_run):
        """Test stop_and_pull generates default path."""
        mock_strftime.return_value = "20260110_143000"
        
        # Configure ADB client mock to return string
        adb_client = Mock()
        adb_client.execute.return_value = "exists"
        
        config = TrafficCaptureConfig(enabled=True)
        manager = TrafficCaptureManager(adb_client=adb_client)
        manager.configure(config)
        manager._is_capturing = True

        result = manager.stop_and_pull()

        assert result == "traffic_capture_20260110_143000.pcap"
        assert manager._is_capturing is False

    @patch("subprocess.run")
    def test_stop_and_pull_with_custom_path(self, mock_run):
        """Test stop_and_pull with custom output path."""
        # Configure ADB client mock to return string
        adb_client = Mock()
        adb_client.execute.return_value = "exists"
        
        config = TrafficCaptureConfig(enabled=True, output_path="/custom/path.pcap")
        manager = TrafficCaptureManager(adb_client=adb_client)
        manager.configure(config)
        manager._is_capturing = True

        result = manager.stop_and_pull("/custom/path.pcap")

        assert result == "/custom/path.pcap"
        assert manager._is_capturing is False

    @patch("subprocess.run")
    def test_stop_and_pull_file_not_found(self, mock_run):
        """Test stop_and_pull when PCAP file not found on device."""
        mock_run.return_value = CompletedProcess(
            args=["adb", "shell", "test"],
            returncode=0,
            stdout="not_exists"
        )
        config = TrafficCaptureConfig(enabled=True)
        manager = TrafficCaptureManager(adb_client=Mock())
        manager.configure(config)
        manager._is_capturing = True

        result = manager.stop_and_pull()

        assert result is None
        assert manager._is_capturing is False

    @patch("subprocess.run")
    def test_stop_and_pull_failure(self, mock_run):
        """Test stop_and_pull handles errors."""
        mock_run.side_effect = Exception("ADB error")
        config = TrafficCaptureConfig(enabled=True)
        manager = TrafficCaptureManager(adb_client=Mock())
        manager.configure(config)
        manager._is_capturing = True

        result = manager.stop_and_pull()

        assert result is None
        assert manager._is_capturing is False

    def test_is_capturing(self):
        """Test is_capturing method."""
        manager = TrafficCaptureManager()
        assert manager.is_capturing() is False

        manager._is_capturing = True
        assert manager.is_capturing() is True

    def test_get_status(self):
        """Test get_status method."""
        config = TrafficCaptureConfig(enabled=True)
        manager = TrafficCaptureManager()
        manager.configure(config)
        manager._pcapdroid_installed = True
        manager._is_capturing = True

        status = manager.get_status()

        assert status == {
            "capturing": True,
            "installed": True,
            "enabled": True,
        }

    def test_get_status_no_config(self):
        """Test get_status when no config is set."""
        manager = TrafficCaptureManager()
        manager._pcapdroid_installed = False
        manager._is_capturing = False

        status = manager.get_status()

        assert status == {
            "capturing": False,
            "installed": False,
            "enabled": False,
        }

    @patch("subprocess.run")
    def test_execute_adb_command_with_client(self, mock_run):
        """Test _execute_adb_command uses ADB client when available."""
        adb_client = Mock()
        adb_client.execute.return_value = "test_output"
        manager = TrafficCaptureManager(adb_client=adb_client)

        result = manager._execute_adb_command("shell test")

        assert result == "test_output"
        adb_client.execute.assert_called_once_with("shell test")
        # subprocess.run should not be called
        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_execute_adb_command_without_client(self, mock_run):
        """Test _execute_adb_command falls back to subprocess when no client."""
        mock_run.return_value = CompletedProcess(
            args=["adb", "shell", "test"],
            returncode=0,
            stdout="test_output"
        )
        manager = TrafficCaptureManager()

        result = manager._execute_adb_command("shell test")

        assert result == "test_output"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_execute_adb_command_timeout(self, mock_run):
        """Test _execute_adb_command handles timeout."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("adb", 30)
        manager = TrafficCaptureManager()

        result = manager._execute_adb_command("shell test")

        assert result is None

    @patch("subprocess.run")
    def test_execute_adb_command_file_not_found(self, mock_run):
        """Test _execute_adb_command handles ADB not found."""
        mock_run.side_effect = FileNotFoundError()
        manager = TrafficCaptureManager()

        result = manager._execute_adb_command("shell test")

        assert result is None
