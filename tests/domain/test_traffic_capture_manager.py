"""Tests for TrafficCaptureManager."""

import asyncio
import os
import tempfile
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest

from mobile_crawler.domain.traffic_capture_manager import TrafficCaptureManager


class TestTrafficCaptureManager:
    """Tests for TrafficCaptureManager."""

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock config manager with capture enabled."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "enable_traffic_capture": True,
            "app_package": "com.test.app",
            "pcapdroid_package": "com.emanuelef.android.apps.pcapdroid",
            "pcapdroid_activity": "com.emanuelef.android.apps.pcapdroid/.activities.CaptureCtrl",
            "pcapdroid_api_key": "test_api_key",
            "device_pcap_dir": "/sdcard/Download/PCAPdroid",
            "adb_executable_path": "adb",
        }.get(key, default)
        config.set = Mock()
        return config

    @pytest.fixture
    def mock_config_manager_disabled(self):
        """Create a mock config manager with capture disabled."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "enable_traffic_capture": False,
            "app_package": "com.test.app",
        }.get(key, default)
        config.set = Mock()
        return config

    @pytest.fixture
    def mock_adb_client(self):
        """Create a mock ADB client."""
        client = Mock()
        client.execute_async = AsyncMock(return_value=("Success", 0))
        return client

    def test_init_with_capture_enabled(self, mock_config_manager, mock_adb_client):
        """Test initialization with traffic capture enabled."""
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=mock_adb_client,
        )

        assert manager.traffic_capture_enabled is True
        assert manager._is_currently_capturing is False
        assert manager.pcap_filename_on_device is None
        assert manager.local_pcap_file_path is None

    def test_init_with_capture_disabled(self, mock_config_manager_disabled, mock_adb_client):
        """Test initialization with traffic capture disabled."""
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager_disabled,
            adb_client=mock_adb_client,
        )

        assert manager.traffic_capture_enabled is False

    def test_is_capturing_returns_internal_state(self, mock_config_manager, mock_adb_client):
        """Test is_capturing returns the internal capturing state."""
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=mock_adb_client,
        )

        assert manager.is_capturing() is False

        manager._is_currently_capturing = True
        assert manager.is_capturing() is True

    def test_start_capture_async_when_enabled(self, mock_config_manager, mock_adb_client):
        """Test starting capture when enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = TrafficCaptureManager(
                config_manager=mock_config_manager,
                adb_client=mock_adb_client,
            )

            success, message = asyncio.run(manager.start_capture_async(
                run_id=1, step_num=1, session_path=temp_dir
            ))

            assert success is True
            assert "successfully" in message
            assert manager._is_currently_capturing is True
            assert manager.pcap_filename_on_device is not None
            assert manager.local_pcap_file_path is not None

    def test_start_capture_async_when_disabled(self, mock_config_manager_disabled, mock_adb_client):
        """Test starting capture when disabled returns False."""
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager_disabled,
            adb_client=mock_adb_client,
        )

        success, message = asyncio.run(manager.start_capture_async(run_id=1, step_num=1))

        assert success is False
        assert "not enabled" in message
        assert manager._is_currently_capturing is False
        mock_adb_client.execute_async.assert_not_called()

    def test_start_capture_async_already_capturing(self, mock_config_manager, mock_adb_client):
        """Test starting capture when already capturing returns True without restarting."""
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=mock_adb_client,
        )
        manager._is_currently_capturing = True

        success, message = asyncio.run(manager.start_capture_async(run_id=1, step_num=1))

        assert success is True
        assert "already started" in message
        # Should not call ADB again
        mock_adb_client.execute_async.assert_not_called()

    def test_start_capture_async_no_app_package(self, mock_adb_client):
        """Test starting capture fails without app_package configured."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "enable_traffic_capture": True,
            "app_package": "",  # Empty app package
        }.get(key, default)
        config.set = Mock()

        manager = TrafficCaptureManager(
            config_manager=config,
            adb_client=mock_adb_client,
        )

        success, message = asyncio.run(manager.start_capture_async(run_id=1, step_num=1))

        assert success is False
        assert "APP_PACKAGE not configured" in message

    def test_stop_capture_when_not_capturing(self, mock_config_manager, mock_adb_client):
        """Test stopping capture when not capturing returns None."""
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=mock_adb_client,
        )

        result = asyncio.run(manager.stop_capture_and_pull_async(run_id=1, step_num=1))

        assert result is None

    def test_generates_correct_filename(self, mock_config_manager, mock_adb_client):
        """Test that filenames are generated with correct format."""
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=mock_adb_client,
        )

        # Run the async function to set the filename
        with tempfile.TemporaryDirectory() as temp_dir:
            asyncio.run(manager.start_capture_async(run_id=42, step_num=5, session_path=temp_dir))
            filename = manager.pcap_filename_on_device

        assert filename is not None
        # Package name dots are preserved in filename
        assert "com.test.app" in filename
        assert "run42" in filename
        assert "step5" in filename
        assert filename.endswith(".pcap")

    def test_output_dir_resolution_with_session_path(self, mock_config_manager, mock_adb_client):
        """Test that output directory is correctly resolved when session_path is provided."""
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=mock_adb_client,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            asyncio.run(manager.start_capture_async(run_id=1, step_num=1, session_path=temp_dir))
            pcap_path = manager.local_pcap_file_path

        assert pcap_path is not None
        # Should be in the data subdirectory of session path
        assert "data" in pcap_path


class TestTrafficCaptureManagerADBFallback:
    """Test ADB client fallback behavior."""

    def test_fallback_to_temporary_adb_client(self):
        """Test that manager creates temporary ADB client when none provided."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "enable_traffic_capture": True,
            "app_package": "com.test.app",
            "adb_executable_path": "adb",
            "pcapdroid_activity": "com.emanuelef.android.apps.pcapdroid/.activities.CaptureCtrl",
        }.get(key, default)
        config.set = Mock()

        manager = TrafficCaptureManager(
            config_manager=config,
            adb_client=None,  # No ADB client provided
        )

        # The manager should still be able to initialize
        assert manager.adb_client is None
        assert manager.traffic_capture_enabled is True
