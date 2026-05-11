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
            "pcapdroid_package": "com.emanuelef.remote_capture",
            "pcapdroid_activity": "com.emanuelef.remote_capture/.activities.CaptureCtrl",
            "pcapdroid_api_key": "test_api_key",
            "device_pcap_dir": "/sdcard/Download/PCAPdroid",
            "adb_executable_path": "adb",
            "pcapdroid_init_wait": 0.0,
            "pcapdroid_finalize_wait": 0.0,
            "pcapdroid_tls_decryption": False,
            "pcapdroid_consent_timeout_seconds": 0.0,
            "pcapdroid_consent_poll_interval_seconds": 0.01,
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

    def test_adb_commands_include_device_id_when_provided(self, mock_config_manager, mock_adb_client):
        """ADB calls should target the selected device when a device ID is provided."""
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=mock_adb_client,
            device_id="emulator-5554",
        )

        asyncio.run(manager._run_adb_command_async(["shell", "echo", "ok"]))

        mock_adb_client.execute_async.assert_awaited_once_with(
            ["-s", "emulator-5554", "shell", "echo", "ok"],
            False,
        )

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

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    @patch.object(TrafficCaptureManager, '_maybe_accept_pcapdroid_consent_async', new_callable=AsyncMock)
    def test_start_flow_calls_consent_helper_after_start_intent(
        self, mock_consent, mock_run_adb, mock_config_manager
    ):
        """Start flow should inspect PCAPdroid consent after sending the start intent."""
        events = []

        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "pm list packages" in joined:
                return ("package:com.emanuelef.remote_capture\n", 0)
            if "dumpsys package" in joined:
                return ("android.permission.INTERNET\nandroid.permission.ACCESS_NETWORK_STATE\n", 0)
            if "dumpsys connectivity" in joined:
                return ("VPN com.emanuelef.remote_capture NetworkAgentInfo", 0)
            if "am start" in joined and "pcap_dump_mode" in joined:
                events.append("start_intent")
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "am start" in joined:
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "test -d" in joined:
                return ("", 0)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return ("<hierarchy></hierarchy>", 0)
            return ("", 0)

        async def consent_side_effect():
            events.append("consent_helper")
            return True

        mock_run_adb.side_effect = adb_side_effect
        mock_consent.side_effect = consent_side_effect

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = TrafficCaptureManager(
                config_manager=mock_config_manager,
                adb_client=Mock(),
            )
            success, _ = asyncio.run(manager.start_capture_async(
                run_id=1, step_num=1, session_path=temp_dir
            ))

        assert success is True
        assert events == ["start_intent", "consent_helper"]

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    def test_start_capture_async_when_enabled(self, mock_run_adb, mock_config_manager):
        """Test starting capture when enabled."""
        async def adb_side_effect(cmd, suppress_stderr=False):
            if "pm list packages" in " ".join(cmd):
                return ("package:com.emanuelef.remote_capture\n", 0)
            if "dumpsys package" in " ".join(cmd):
                return ("android.permission.INTERNET\n", 0)
            if "dumpsys connectivity" in " ".join(cmd):
                return ("VPN com.emanuelef.remote_capture NetworkAgentInfo", 0)
            if "am start" in " ".join(cmd):
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "test -d" in " ".join(cmd):
                return ("", 0)
            if "uiautomator dump /sdcard/ui_dump.xml" in " ".join(cmd):
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in " ".join(cmd):
                return ("<hierarchy></hierarchy>", 0)
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = TrafficCaptureManager(
                config_manager=mock_config_manager,
                adb_client=Mock(),
            )

            success, message = asyncio.run(manager.start_capture_async(
                run_id=1, step_num=1, session_path=temp_dir
            ))

            assert success is True
            assert "successfully" in message
            assert manager._is_currently_capturing is True
            assert manager.pcap_filename_on_device is not None
            assert manager.local_pcap_file_path is not None
            assert manager._last_capture_readiness_diagnostics["readiness_source"] == "vpn_or_service"
            assert manager._last_capture_readiness_diagnostics["final_reason"] == "api_readiness_confirmed"

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    def test_start_command_includes_pcap_tls_filter_name_and_api_key(self, mock_run_adb, mock_config_manager):
        """Start intent should include the PCAP file mode, app filter, TLS flag, name, and API key."""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "enable_traffic_capture": True,
            "app_package": "com.test.app",
            "pcapdroid_api_key": "test_api_key",
            "device_pcap_dir": "/sdcard/Download/PCAPdroid",
            "pcapdroid_init_wait": 0.0,
            "pcapdroid_tls_decryption": True,
            "pcapdroid_consent_timeout_seconds": 0.0,
        }.get(key, default)

        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "pm list packages" in joined:
                return ("package:com.emanuelef.remote_capture\n", 0)
            if "dumpsys package" in joined:
                return ("android.permission.INTERNET\nandroid.permission.ACCESS_NETWORK_STATE\n", 0)
            if "dumpsys connectivity" in joined:
                return ("VPN com.emanuelef.remote_capture NetworkAgentInfo", 0)
            if "am start" in joined:
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "test -d" in joined:
                return ("", 0)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return ("<hierarchy></hierarchy>", 0)
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = TrafficCaptureManager(
                config_manager=mock_config_manager,
                adb_client=Mock(),
            )
            success, _ = asyncio.run(manager.start_capture_async(
                run_id=1, step_num=0, session_path=temp_dir
            ))

        assert success is True
        start_commands = [
            call.args[0]
            for call in mock_run_adb.call_args_list
            if " ".join(call.args[0]).startswith("shell am start")
            and "action" in call.args[0]
            and "start" in call.args[0]
            and "pcap_dump_mode" in call.args[0]
        ]
        assert len(start_commands) == 1
        start_command = start_commands[0]
        assert start_command[start_command.index("pcap_dump_mode") + 1] == "pcap_file"
        assert start_command[start_command.index("app_filter") + 1] == "com.test.app"
        assert start_command[start_command.index("pcap_name") + 1].endswith(".pcap")
        assert start_command[start_command.index("tls_decryption") + 1] == "true"
        assert start_command[start_command.index("api_key") + 1] == "test_api_key"

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

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    def test_start_capture_async_already_capturing(self, mock_run_adb, mock_config_manager):
        """Test starting capture when already capturing stops first then restarts."""
        async def adb_side_effect(cmd, suppress_stderr=False):
            if "pm list packages" in " ".join(cmd):
                return ("package:com.emanuelef.remote_capture\n", 0)
            if "dumpsys package" in " ".join(cmd):
                return ("android.permission.INTERNET\n", 0)
            if "dumpsys connectivity" in " ".join(cmd):
                return ("VPN com.emanuelef.remote_capture NetworkAgentInfo", 0)
            if "am start" in " ".join(cmd) and "action stop" in " ".join(cmd):
                return ("", 0)
            if "am start" in " ".join(cmd):
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "test -d" in " ".join(cmd):
                return ("", 0)
            if "uiautomator dump /sdcard/ui_dump.xml" in " ".join(cmd):
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in " ".join(cmd):
                return ("<hierarchy></hierarchy>", 0)
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect

        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=Mock(),
        )
        # First start capture to set state
        asyncio.run(manager.start_capture_async(run_id=1, step_num=1))
        assert manager._is_currently_capturing is True

        # Now start again - should succeed after stopping first
        success, message = asyncio.run(manager.start_capture_async(run_id=1, step_num=1))

        assert success is True
        assert "started successfully" in message

    def test_start_capture_async_no_app_package(self, mock_adb_client):
        """Test starting capture fails without app_package configured."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "enable_traffic_capture": True,
            "app_package": "",  # Empty app package
            "pcapdroid_init_wait": 0.0,
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

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    def test_generates_correct_filename(self, mock_run_adb, mock_config_manager):
        """Test that filenames are generated with correct format."""
        async def adb_side_effect(cmd, suppress_stderr=False):
            if "pm list packages" in " ".join(cmd):
                return ("package:com.emanuelef.remote_capture\n", 0)
            if "dumpsys package" in " ".join(cmd):
                return ("android.permission.INTERNET\n", 0)
            if "dumpsys connectivity" in " ".join(cmd):
                return ("VPN com.emanuelef.remote_capture NetworkAgentInfo", 0)
            if "am start" in " ".join(cmd) and "action stop" in " ".join(cmd):
                return ("", 0)
            if "am start" in " ".join(cmd):
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "test -d" in " ".join(cmd):
                return ("", 0)
            if "uiautomator dump /sdcard/ui_dump.xml" in " ".join(cmd):
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in " ".join(cmd):
                return ("<hierarchy></hierarchy>", 0)
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect

        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=Mock(),
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

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    def test_output_dir_resolution_with_session_path(self, mock_run_adb, mock_config_manager):
        """Test that output directory is correctly resolved when session_path is provided."""
        async def adb_side_effect(cmd, suppress_stderr=False):
            if "pm list packages" in " ".join(cmd):
                return ("package:com.emanuelef.remote_capture\n", 0)
            if "dumpsys package" in " ".join(cmd):
                return ("android.permission.INTERNET\n", 0)
            if "dumpsys connectivity" in " ".join(cmd):
                return ("VPN com.emanuelef.remote_capture NetworkAgentInfo", 0)
            if "am start" in " ".join(cmd) and "action stop" in " ".join(cmd):
                return ("", 0)
            if "am start" in " ".join(cmd):
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "test -d" in " ".join(cmd):
                return ("", 0)
            if "uiautomator dump /sdcard/ui_dump.xml" in " ".join(cmd):
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in " ".join(cmd):
                return ("<hierarchy></hierarchy>", 0)
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect

        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=Mock(),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            asyncio.run(manager.start_capture_async(run_id=1, step_num=1, session_path=temp_dir))
            pcap_path = manager.local_pcap_file_path

        assert pcap_path is not None
        # Should be in the pcap subdirectory of session path
        assert os.path.basename(os.path.dirname(pcap_path)) == "pcap"

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    def test_stop_command_includes_api_key_when_configured(self, mock_run_adb, mock_config_manager):
        """Stop intent should pass the configured API key."""
        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "action stop" in joined:
                return ("", 0)
            if "get_status" in joined:
                return ("", 0)
            if "test -f" in joined:
                return ("", 1)
            if "ls -la" in joined:
                return ("", 1)
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect

        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=Mock(),
        )
        manager._is_currently_capturing = True
        manager.pcap_filename_on_device = "capture.pcap"
        manager.local_pcap_file_path = os.path.join(tempfile.gettempdir(), "capture.pcap")

        asyncio.run(manager.stop_capture_and_pull_async(run_id=1, step_num=0))

        stop_commands = [
            call.args[0]
            for call in mock_run_adb.call_args_list
            if "action" in call.args[0]
            and "stop" in call.args[0]
            and "api_key" in call.args[0]
        ]
        assert stop_commands
        assert stop_commands[0][stop_commands[0].index("api_key") + 1] == "test_api_key"

    def test_consent_helper_taps_allow_with_capture_context(self, mock_config_manager):
        """Consent helper should tap the center of Allow only in capture/VPN context."""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "enable_traffic_capture": True,
            "app_package": "com.test.app",
            "pcapdroid_auto_accept_consent": True,
            "pcapdroid_consent_timeout_seconds": 1.0,
            "pcapdroid_consent_poll_interval_seconds": 0.01,
        }.get(key, default)
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=Mock(),
        )
        ui_xml = """<hierarchy>
  <node text="PCAPdroid" bounds="[0,0][100,50]" />
  <node text="An app wants to capture your device traffic." bounds="[0,50][500,100]" />
  <node text="ALLOW" bounds="[10,20][110,70]" />
</hierarchy>"""

        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return (ui_xml, 0)
            if "input tap" in joined:
                return ("", 0)
            return ("", 0)

        manager._run_adb_command_async = AsyncMock(side_effect=adb_side_effect)

        accepted = asyncio.run(manager._maybe_accept_pcapdroid_consent_async())

        assert accepted is True
        manager._run_adb_command_async.assert_any_await(
            ["shell", "uiautomator", "dump", "/sdcard/ui_dump.xml"],
            suppress_stderr=True,
        )
        manager._run_adb_command_async.assert_any_await(
            ["shell", "cat", "/sdcard/ui_dump.xml"],
            suppress_stderr=True,
        )
        manager._run_adb_command_async.assert_any_await(
            ["shell", "input", "tap", "60", "45"],
            suppress_stderr=True,
        )

    def test_consent_helper_taps_content_desc_allow_with_capture_context(self, mock_config_manager):
        """Consent helper should also recognize approval labels exposed via content-desc."""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "enable_traffic_capture": True,
            "app_package": "com.test.app",
            "pcapdroid_auto_accept_consent": True,
            "pcapdroid_consent_timeout_seconds": 1.0,
            "pcapdroid_consent_poll_interval_seconds": 0.01,
        }.get(key, default)
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=Mock(),
        )
        ui_xml = """
<hierarchy>
  <node text="PCAPdroid" bounds="[0,0][100,50]" />
  <node text="control request" bounds="[0,50][500,100]" />
  <node text="" content-desc="Allow" bounds="[10,20][110,70]" />
</hierarchy>"""

        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return (ui_xml, 0)
            if "input tap" in joined:
                return ("", 0)
            return ("", 0)

        manager._run_adb_command_async = AsyncMock(side_effect=adb_side_effect)

        accepted = asyncio.run(manager._maybe_accept_pcapdroid_consent_async())

        assert accepted is True
        manager._run_adb_command_async.assert_any_await(
            ["shell", "input", "tap", "60", "45"],
            suppress_stderr=True,
        )

    def test_consent_helper_handles_allow_then_start_now(self, mock_config_manager):
        """Consent helper should keep polling through PCAPdroid and Android VPN dialogs."""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "enable_traffic_capture": True,
            "app_package": "com.test.app",
            "pcapdroid_auto_accept_consent": True,
            "pcapdroid_consent_timeout_seconds": 1.0,
            "pcapdroid_consent_poll_interval_seconds": 0.01,
        }.get(key, default)
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=Mock(),
        )
        ui_xmls = [
            """<hierarchy>
  <node text="PCAPdroid" bounds="[0,0][100,50]" />
  <node text="control request" bounds="[0,50][500,100]" />
  <node text="ALLOW" bounds="[10,20][110,70]" />
</hierarchy>""",
            """<hierarchy>
  <node text="Connection request" bounds="[0,0][500,50]" />
  <node text="PCAPdroid wants to set up a VPN connection" bounds="[0,50][500,100]" />
  <node text="Start now" bounds="[20,30][180,90]" />
</hierarchy>""",
            "<hierarchy></hierarchy>",
        ]

        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return (ui_xmls.pop(0), 0)
            if "input tap" in joined:
                return ("", 0)
            return ("", 0)

        manager._run_adb_command_async = AsyncMock(side_effect=adb_side_effect)

        accepted = asyncio.run(manager._maybe_accept_pcapdroid_consent_async())

        assert accepted is True
        assert manager._last_consent_labels_tapped == ["ALLOW", "Start now"]
        tap_calls = [
            call.args[0]
            for call in manager._run_adb_command_async.await_args_list
            if " ".join(call.args[0]).startswith("shell input tap")
        ]
        assert tap_calls == [
            ["shell", "input", "tap", "60", "45"],
            ["shell", "input", "tap", "100", "60"],
        ]

    def test_consent_helper_ignores_allow_without_capture_context(self, mock_config_manager):
        """Generic permission dialogs should not be auto-approved."""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "enable_traffic_capture": True,
            "app_package": "com.test.app",
            "pcapdroid_auto_accept_consent": True,
            "pcapdroid_consent_timeout_seconds": 0.02,
            "pcapdroid_consent_poll_interval_seconds": 0.01,
        }.get(key, default)
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=Mock(),
        )
        ui_xml = """<hierarchy>
  <node text="Allow" bounds="[10,20][110,70]" />
</hierarchy>"""

        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return (ui_xml, 0)
            return ("", 0)

        manager._run_adb_command_async = AsyncMock(side_effect=adb_side_effect)

        accepted = asyncio.run(manager._maybe_accept_pcapdroid_consent_async())

        assert accepted is False
        tap_calls = [
            call for call in manager._run_adb_command_async.await_args_list
            if "input" in call.args[0] and "tap" in call.args[0]
        ]
        assert tap_calls == []

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    def test_start_capture_fails_when_consent_dialog_remains(
        self, mock_run_adb, mock_config_manager
    ):
        """Startup should fail and clear state if a PCAPdroid/VPN dialog remains."""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "enable_traffic_capture": True,
            "app_package": "com.test.app",
            "pcapdroid_package": "com.emanuelef.remote_capture",
            "pcapdroid_activity": "com.emanuelef.remote_capture/.activities.CaptureCtrl",
            "pcapdroid_api_key": "test_api_key",
            "device_pcap_dir": "/sdcard/Download/PCAPdroid",
            "pcapdroid_init_wait": 0.0,
            "pcapdroid_tls_decryption": False,
            "pcapdroid_auto_accept_consent": True,
            "pcapdroid_consent_timeout_seconds": 0.03,
            "pcapdroid_consent_poll_interval_seconds": 0.01,
        }.get(key, default)
        ui_xml = """<hierarchy>
  <node text="PCAPdroid wants to set up a VPN connection" bounds="[0,0][500,100]" />
  <node text="Start now" bounds="[20,30][180,90]" />
</hierarchy>"""

        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "pm list packages" in joined:
                return ("package:com.emanuelef.remote_capture\n", 0)
            if "dumpsys package" in joined:
                return ("android.permission.INTERNET\nandroid.permission.ACCESS_NETWORK_STATE\n", 0)
            if "dumpsys connectivity" in joined:
                return ("VPN com.emanuelef.remote_capture NetworkAgentInfo", 0)
            if "am start" in joined:
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "test -d" in joined:
                return ("", 0)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return (ui_xml, 0)
            if "input tap" in joined:
                return ("", 0)
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect
        manager = TrafficCaptureManager(config_manager=mock_config_manager, adb_client=Mock())

        with tempfile.TemporaryDirectory() as temp_dir:
            success, message = asyncio.run(
                manager.start_capture_async(run_id=1, step_num=1, session_path=temp_dir)
            )

        assert success is False
        assert "did not become ready" in message
        assert manager._is_currently_capturing is False
        assert manager.pcap_filename_on_device is None
        assert manager.local_pcap_file_path is None

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    def test_successful_start_records_readiness_without_claiming_file(
        self, mock_run_adb, mock_config_manager, caplog
    ):
        """Successful startup should log readiness, not local PCAP production."""
        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "pm list packages" in joined:
                return ("package:com.emanuelef.remote_capture\n", 0)
            if "dumpsys package" in joined:
                return ("android.permission.INTERNET\nandroid.permission.ACCESS_NETWORK_STATE\n", 0)
            if "dumpsys connectivity" in joined:
                return ("VPN com.emanuelef.remote_capture NetworkAgentInfo", 0)
            if "am start" in joined:
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "test -d" in joined:
                return ("", 0)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return ("<hierarchy></hierarchy>", 0)
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect
        manager = TrafficCaptureManager(config_manager=mock_config_manager, adb_client=Mock())

        with tempfile.TemporaryDirectory() as temp_dir, caplog.at_level("INFO"):
            success, _ = asyncio.run(
                manager.start_capture_async(run_id=1, step_num=1, session_path=temp_dir)
            )

        assert success is True
        assert manager._capture_startup_readiness_passed is True
        assert "capture readiness checked" in caplog.text
        assert "PCAP file saved" not in caplog.text

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    def test_start_accepts_api_status_running_without_vpn_signal(
        self, mock_run_adb, mock_config_manager, caplog
    ):
        """API status running=true should be treated as readiness without any UI fallback taps."""
        ui_xml = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node package="com.emanuelef.remote_capture" text="" bounds="[0,0][1080,2400]" />
</hierarchy>"""

        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "pm list packages" in joined:
                return ("package:com.emanuelef.remote_capture\n", 0)
            if "dumpsys package" in joined:
                return ("android.permission.INTERNET\nandroid.permission.ACCESS_NETWORK_STATE\n", 0)
            if "dumpsys connectivity" in joined:
                return ("NetworkProviders for: VpnNetworkProvider:0 Active default network: 113", 0)
            if "dumpsys activity services com.emanuelef.remote_capture" in joined:
                return ("", 0)
            if "action get_status" in joined:
                return ("Status: ok running=true", 0)
            if "am start" in joined:
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "test -d" in joined:
                return ("", 0)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return (ui_xml, 0)
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect
        manager = TrafficCaptureManager(config_manager=mock_config_manager, adb_client=Mock())

        with tempfile.TemporaryDirectory() as temp_dir, caplog.at_level("INFO"):
            success, _ = asyncio.run(
                manager.start_capture_async(run_id=1, step_num=1, session_path=temp_dir)
            )

        assert success is True
        assert manager._capture_startup_readiness_passed is True
        assert manager._last_capture_readiness_diagnostics["readiness_source"] == "api_status_running"
        assert manager._last_capture_readiness_diagnostics["api_status"]["running"] is True

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    @patch.object(TrafficCaptureManager, '_maybe_accept_pcapdroid_consent_async', new_callable=AsyncMock)
    def test_start_resends_api_start_after_consent(
        self, mock_consent, mock_run_adb, mock_config_manager
    ):
        """When consent was accepted, startup should resend the start intent once to apply settings."""
        status_calls = {"count": 0}

        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "pm list packages" in joined:
                return ("package:com.emanuelef.remote_capture\n", 0)
            if "dumpsys package" in joined:
                return ("android.permission.INTERNET\nandroid.permission.ACCESS_NETWORK_STATE\n", 0)
            if "dumpsys connectivity" in joined:
                return ("NetworkProviders for: VpnNetworkProvider:0 Active default network: 113", 0)
            if "dumpsys activity services com.emanuelef.remote_capture" in joined:
                return ("", 0)
            if "action get_status" in joined:
                status_calls["count"] += 1
                if status_calls["count"] <= 2:
                    return ("Status: ok running=false", 0)
                return ("Status: ok running=true", 0)
            if "am start" in joined and "pcap_dump_mode" in joined:
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "am start" in joined:
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "test -d" in joined:
                return ("", 0)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return ("<hierarchy><node package='com.emanuelef.remote_capture'/></hierarchy>", 0)
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect
        mock_consent.side_effect = [True, False]
        manager = TrafficCaptureManager(config_manager=mock_config_manager, adb_client=Mock())

        with tempfile.TemporaryDirectory() as temp_dir:
            success, _ = asyncio.run(
                manager.start_capture_async(run_id=1, step_num=1, session_path=temp_dir)
            )

        assert success is True
        start_commands = [
            call.args[0]
            for call in mock_run_adb.call_args_list
            if "pcap_dump_mode" in call.args[0] and "action" in call.args[0] and "start" in call.args[0]
        ]
        assert len(start_commands) == 2
        assert manager._last_capture_readiness_diagnostics["api_start_resent_after_consent"] is True

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    def test_start_taps_action_start_fallback_when_visible(
        self, mock_run_adb, mock_config_manager
    ):
        """If still idle after API polling, startup may tap only PCAPdroid action_start."""
        tapped = {"value": False}
        ui_xml = """<hierarchy>
  <node package="com.emanuelef.remote_capture" text="" bounds="[0,0][1080,2400]" />
  <node package="com.emanuelef.remote_capture" resource-id="com.emanuelef.remote_capture:id/action_start" text="Start" bounds="[900,120][1060,220]" />
</hierarchy>"""

        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "pm list packages" in joined:
                return ("package:com.emanuelef.remote_capture\n", 0)
            if "dumpsys package" in joined:
                return ("android.permission.INTERNET\nandroid.permission.ACCESS_NETWORK_STATE\n", 0)
            if "dumpsys connectivity" in joined:
                return ("NetworkProviders for: VpnNetworkProvider:0 Active default network: 113", 0)
            if "dumpsys activity services com.emanuelef.remote_capture" in joined:
                return ("", 0)
            if "action get_status" in joined:
                return (f"Status: ok running={'true' if tapped['value'] else 'false'}", 0)
            if "am start" in joined:
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "test -d" in joined:
                return ("", 0)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return (ui_xml, 0)
            if "input tap" in joined:
                tapped["value"] = True
                return ("", 0)
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect
        manager = TrafficCaptureManager(config_manager=mock_config_manager, adb_client=Mock())

        with tempfile.TemporaryDirectory() as temp_dir:
            success, _ = asyncio.run(
                manager.start_capture_async(run_id=1, step_num=1, session_path=temp_dir)
            )

        assert success is True
        assert manager._last_capture_readiness_diagnostics["ui_action_start_tapped"] is True
        tap_calls = [
            call.args[0]
            for call in mock_run_adb.call_args_list
            if " ".join(call.args[0]).startswith("shell input tap")
        ]
        assert len(tap_calls) == 1

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    def test_start_fails_when_not_ready_after_api_polling(
        self, mock_run_adb, mock_config_manager
    ):
        """Startup should fail when API status and diagnostics never show active capture."""
        ui_xml = """<hierarchy>
  <node package="com.emanuelef.remote_capture" text="" bounds="[0,0][1080,2400]" />
</hierarchy>"""

        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "pm list packages" in joined:
                return ("package:com.emanuelef.remote_capture\n", 0)
            if "dumpsys package" in joined:
                return ("android.permission.INTERNET\nandroid.permission.ACCESS_NETWORK_STATE\n", 0)
            if "dumpsys connectivity" in joined:
                return ("NetworkProviders for: VpnNetworkProvider:0 Active default network: 113", 0)
            if "dumpsys activity services com.emanuelef.remote_capture" in joined:
                return ("", 0)
            if "action get_status" in joined:
                return ("Status: ok running=false", 0)
            if "am start" in joined:
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "test -d" in joined:
                return ("", 0)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return (ui_xml, 0)
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect
        manager = TrafficCaptureManager(config_manager=mock_config_manager, adb_client=Mock())

        with tempfile.TemporaryDirectory() as temp_dir:
            success, message = asyncio.run(
                manager.start_capture_async(run_id=1, step_num=1, session_path=temp_dir)
            )

        assert success is False
        assert "did not become ready" in message
        assert manager._capture_startup_readiness_passed is False
        assert manager._last_capture_readiness_diagnostics["final_reason"] == "not_ready_after_api_polling"
        assert manager._is_currently_capturing is False
        assert manager.pcap_filename_on_device is None
        assert manager.local_pcap_file_path is None

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    def test_start_does_not_attempt_start_button_taps_during_api_polling(
        self, mock_run_adb, mock_config_manager
    ):
        """Capture startup should not issue generic input tap commands for start controls."""
        ui_xml = """<hierarchy>
  <node package="com.emanuelef.remote_capture" text="" bounds="[0,0][1080,2400]" />
</hierarchy>"""

        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "pm list packages" in joined:
                return ("package:com.emanuelef.remote_capture\n", 0)
            if "dumpsys package" in joined:
                return ("android.permission.INTERNET\nandroid.permission.ACCESS_NETWORK_STATE\n", 0)
            if "dumpsys connectivity" in joined:
                return ("NetworkProviders for: VpnNetworkProvider:0 Active default network: 113", 0)
            if "dumpsys activity services com.emanuelef.remote_capture" in joined:
                return ("", 0)
            if "action get_status" in joined:
                return ("Status: ok running=false", 0)
            if "am start" in joined:
                return ("Starting: Intent { cmp=com.emanuelef.remote_capture/.activities.CaptureCtrl }\n", 0)
            if "test -d" in joined:
                return ("", 0)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return (ui_xml, 0)
            if "input tap" in joined:
                raise AssertionError("No start-button tap should be attempted")
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect
        manager = TrafficCaptureManager(config_manager=mock_config_manager, adb_client=Mock())

        with tempfile.TemporaryDirectory() as temp_dir:
            success, _ = asyncio.run(
                manager.start_capture_async(run_id=1, step_num=1, session_path=temp_dir)
            )

        assert success is False
        assert manager._last_capture_readiness_diagnostics["final_reason"] == "not_ready_after_api_polling"

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    def test_readiness_uses_ui_running_status_hint(self, mock_run_adb, mock_config_manager):
        """Status view 'running' should count as readiness even without explicit VPN hint."""
        ui_xml = """<hierarchy>
  <node package="com.emanuelef.remote_capture" resource-id="com.emanuelef.remote_capture:id/status_view" text="Running" bounds="[10,10][200,60]" />
</hierarchy>"""

        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return (ui_xml, 0)
            if "dumpsys connectivity" in joined:
                return ("NetworkProviders for: VpnNetworkProvider:0 Active default network: 113", 0)
            if "dumpsys activity services com.emanuelef.remote_capture" in joined:
                return ("", 0)
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect
        manager = TrafficCaptureManager(config_manager=mock_config_manager, adb_client=Mock())
        readiness = asyncio.run(manager._check_capture_readiness_async())

        assert readiness["ready"] is True
        assert readiness["readiness_source"] == "ui_status_running"

    def test_consent_helper_disabled_by_config(self, mock_config_manager):
        """Config should be able to disable consent auto-approval."""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "enable_traffic_capture": True,
            "app_package": "com.test.app",
            "pcapdroid_auto_accept_consent": False,
        }.get(key, default)
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=Mock(),
        )
        manager._run_adb_command_async = AsyncMock(return_value=("", 0))

        accepted = asyncio.run(manager._maybe_accept_pcapdroid_consent_async())

        assert accepted is False
        manager._run_adb_command_async.assert_not_awaited()

    @patch.object(TrafficCaptureManager, '_run_adb_command_async')
    def test_missing_pcap_logs_expected_path_and_likely_causes(
        self, mock_run_adb, mock_config_manager, caplog
    ):
        """Missing expected PCAP should produce diagnostics without claiming success."""
        async def adb_side_effect(cmd, suppress_stderr=False):
            joined = " ".join(cmd)
            if "action stop" in joined:
                return ("", 0)
            if "get_status" in joined:
                return ("", 0)
            if "test -f" in joined:
                return ("", 1)
            if "ls -la" in joined:
                return ("total 0", 0)
            if "find" in joined:
                return ("/sdcard/Download/PCAPdroid/other.pcap\n", 0)
            if "uiautomator dump /sdcard/ui_dump.xml" in joined:
                return ("UI hierchary dumped to: /sdcard/ui_dump.xml", 0)
            if "cat /sdcard/ui_dump.xml" in joined:
                return ("<hierarchy><node text=\"PCAPdroid\" /></hierarchy>", 0)
            if "dumpsys connectivity" in joined:
                return ("VPN com.emanuelef.remote_capture NetworkAgentInfo", 0)
            return ("", 0)

        mock_run_adb.side_effect = adb_side_effect
        manager = TrafficCaptureManager(
            config_manager=mock_config_manager,
            adb_client=Mock(),
        )
        manager._is_currently_capturing = True
        manager.pcap_filename_on_device = "expected.pcap"
        manager.local_pcap_file_path = os.path.join(tempfile.gettempdir(), "expected.pcap")
        manager._capture_startup_readiness_passed = True
        manager._last_consent_labels_tapped = ["ALLOW", "Start now"]
        manager._last_capture_startup_diagnostics = {
            "api_start_sent": True,
            "consent_labels_tapped": ["ALLOW", "Start now"],
            "api_status_checks": [{"running": True, "status": "query_sent"}],
        }

        with caplog.at_level("INFO"):
            result = asyncio.run(manager.stop_capture_and_pull_async(run_id=1, step_num=1))

        assert result is None
        assert "/sdcard/Download/PCAPdroid/expected.pcap" in caplog.text
        assert "other.pcap" in caplog.text
        assert "consent dialog was not accepted" in caplog.text
        assert "startup_readiness_passed=True" in caplog.text
        assert "tapped_consent_labels=['ALLOW', 'Start now']" in caplog.text
        assert "startup_diagnostics={'api_start_sent': True" in caplog.text
        assert "Missing PCAP final UI dump snippet" in caplog.text
        assert "Missing PCAP connectivity diagnostics" in caplog.text
        assert "Missing PCAP PCAPdroid service diagnostics" in caplog.text


class TestTrafficCaptureManagerADBFallback:
    """Test ADB client fallback behavior."""

    def test_fallback_to_temporary_adb_client(self):
        """Test that manager creates temporary ADB client when none provided."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "enable_traffic_capture": True,
            "app_package": "com.test.app",
            "adb_executable_path": "adb",
            "pcapdroid_activity": "com.emanuelef.remote_capture/.activities.CaptureCtrl",
        }.get(key, default)
        config.set = Mock()

        manager = TrafficCaptureManager(
            config_manager=config,
            adb_client=None,  # No ADB client provided
        )

        # The manager should still be able to initialize
        assert manager.adb_client is None
        assert manager.traffic_capture_enabled is True
