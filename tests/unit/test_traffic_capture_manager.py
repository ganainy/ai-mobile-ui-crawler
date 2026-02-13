"""Unit tests for TrafficCaptureManager stop-before-start behavior."""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from mobile_crawler.domain.traffic_capture_manager import TrafficCaptureManager

class TestTrafficCaptureManagerStopBeforeStart:
    @pytest.fixture
    def mock_config_manager(self):
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "enable_traffic_capture": True,
            "app_package": "com.test.app",
            "pcapdroid_package": "com.emanuelef.remote_capture",
            "pcapdroid_activity": "com.emanuelef.remote_capture/.activities.CaptureCtrl",
            "device_pcap_dir": "/sdcard/Download/PCAPdroid",
        }.get(key, default)
        return config

    @pytest.fixture
    def mock_adb_client(self):
        client = Mock()
        client.execute_async = AsyncMock(return_value=("Success", 0))
        return client

    def test_start_capture_always_sends_stop_first(self, mock_config_manager, mock_adb_client):
        """Test that start_capture_async always sends a stop command before starting."""
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=mock_adb_client,
        )
        
        async def run_test():
            with patch.object(TrafficCaptureManager, "_run_adb_command_async", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = ("com.emanuelef.remote_capture", 0)
                
                await manager.start_capture_async(run_id=1, step_num=1, session_path="/tmp")
                
                # Find indices of am start commands
                history = [str(c) for c in mock_run.call_args_list]
                stop_idx = -1
                start_idx = -1
                
                for i, cmd in enumerate(history):
                    if "am" in cmd and "action" in cmd:
                        if "stop" in cmd:
                            stop_idx = i
                        elif "start" in cmd:
                            start_idx = i
                
                # Verify both were found and stop came before start
                assert stop_idx != -1, f"Stop command not found in history: {history}"
                assert start_idx != -1, f"Start command not found in history: {history}"
                assert stop_idx < start_idx, f"Stop command ({stop_idx}) must come before start command ({start_idx})"

        asyncio.run(run_test())

    def test_stop_any_existing_capture_async(self, mock_config_manager, mock_adb_client):
        """Test the private helper method directly."""
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=mock_adb_client,
        )
        
        async def run_test():
            with patch.object(TrafficCaptureManager, "_run_adb_command_async", new_callable=AsyncMock) as mock_run:
                await manager._stop_any_existing_capture_async()
                
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert "am" in args
                assert "start" in args
                assert "stop" in args
                assert "com.emanuelef.remote_capture/.activities.CaptureCtrl" in args

        asyncio.run(run_test())
