"""Traffic capture manager for PCAPdroid integration."""

import asyncio
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from mobile_crawler.config.config_manager import ConfigManager
    from mobile_crawler.infrastructure.adb_client import ADBClient
    from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager

logger = logging.getLogger(__name__)


class TrafficCaptureManager:
    """Manages traffic capture using PCAPdroid.

    Handles starting/stopping traffic capture via ADB intent API,
    pulling PCAP files from device, and graceful handling when
    PCAPdroid is not installed.
    """

    def __init__(
        self,
        config_manager: "ConfigManager",
        adb_client: Optional["ADBClient"] = None,
        session_folder_manager: Optional["SessionFolderManager"] = None,
        device_id: str | None = None,
    ):
        """Initialize the traffic capture manager.

        Args:
            config_manager: Configuration manager instance
            adb_client: Optional ADB client wrapper for executing commands
            session_folder_manager: Optional session folder manager for path resolution
            device_id: Optional Android device ID for ADB targeting
        """
        self.config_manager = config_manager
        self.adb_client = adb_client
        self.session_folder_manager = session_folder_manager
        self.device_id = device_id

        self.traffic_capture_enabled: bool = bool(
            config_manager.get("enable_traffic_capture", False)
        )
        logger.debug(f"TrafficCaptureManager initialized, enabled: {self.traffic_capture_enabled}")

        self.pcap_filename_on_device: str | None = None
        self.local_pcap_file_path: str | None = None
        self._is_currently_capturing: bool = False
        self._capture_startup_readiness_passed: bool | None = None
        self._last_consent_labels_tapped: list[str] = []
        self._last_capture_readiness_diagnostics: dict[str, Any] = {}
        self._last_capture_startup_diagnostics: dict[str, Any] = {}

        # Package: com.emanuelef.remote_capture
        # Activity: com.emanuelef.remote_capture/.activities.CaptureCtrl

    def _device_scoped_args(self, command_list: list[str]) -> list[str]:
        """Prefix an ADB argument list with the selected device when available."""
        if self.device_id:
            return ["-s", self.device_id, *command_list]
        return command_list

    async def _run_adb_command_async(
        self, command_list: list[str], suppress_stderr: bool = False
    ) -> tuple[str, int]:
        """Async helper to run ADB commands.

        Args:
            command_list: List of ADB command arguments (without 'adb' prefix)
            suppress_stderr: If True, don't log stderr output

        Returns:
            Tuple of (combined_output, return_code)
        """
        if self.adb_client:
            return await self.adb_client.execute_async(
                self._device_scoped_args(command_list), suppress_stderr
            )

        # Fallback: create temporary ADB client
        from mobile_crawler.infrastructure.adb_client import ADBClient

        adb_executable = self.config_manager.get("adb_executable_path", "adb")
        temp_client = ADBClient(adb_executable=adb_executable)
        return await temp_client.execute_async(
            self._device_scoped_args(command_list), suppress_stderr
        )

    def is_capturing(self) -> bool:
        """Returns the internal state of whether capture is thought to be active."""
        return self._is_currently_capturing

    async def _stop_any_existing_capture_async(self) -> None:
        """Stop any running capture as a precaution."""
        pcapdroid_activity = "com.emanuelef.remote_capture/.activities.CaptureCtrl"
        stop_command_args = [
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            pcapdroid_activity,
            "-e",
            "action",
            "stop",
        ]
        logger.debug("[DEBUG] Sending precautionary STOP command to PCAPdroid...")
        await self._run_adb_command_async(stop_command_args, suppress_stderr=True)
        # Brief wait to ensure PCAPdroid has time to stop and release resources
        await asyncio.sleep(1.0)

    async def start_capture_async(
        self,
        run_id: int | None = None,
        step_num: int | None = None,
        session_path: str | None = None,
    ) -> tuple[bool, str]:
        """Starts PCAPdroid traffic capture using the official API.

        Args:
            run_id: Optional run ID for filename generation
            step_num: Optional step number for filename generation
            session_path: Optional session directory path for output

        Returns:
            Tuple of (success, message)
        """
        logger.info(f"start_capture_async called: traffic_capture_enabled={self.traffic_capture_enabled}, run_id={run_id}, session_path={session_path}")

        if not self.traffic_capture_enabled:
            return False, "Traffic capture is not enabled in TrafficCaptureManager"

        # Always stop any existing capture first to avoid conflicts
        await self._stop_any_existing_capture_async()

        if self._is_currently_capturing:
            # This check is now less critical but we keep it for state management
            logger.debug("Internal state says already capturing, but stop was sent anyway.")

        target_app_package = str(self.config_manager.get("app_package", ""))
        if not target_app_package:
            return False, "APP_PACKAGE not configured"

        # Verify PCAPdroid is installed
        logger.debug("[DEBUG] Checking if PCAPdroid is installed...")
        check_package_args = ["shell", "pm", "list", "packages", "com.emanuelef.remote_capture"]
        stdout_pkg, retcode_pkg = await self._run_adb_command_async(check_package_args, suppress_stderr=True)

        if retcode_pkg != 0 or "com.emanuelef.remote_capture" not in stdout_pkg:
            error_msg = (
                "PCAPdroid is not installed on the device. "
                "Please install it from the Play Store or F-Droid: "
                "https://github.com/emanuele-f/PCAPdroid/releases"
            )
            logger.error(error_msg)
            return False, error_msg

        logger.debug("[DEBUG] PCAPdroid is installed")

        # Check if PCAPdroid has the necessary permissions
        logger.debug("[DEBUG] Checking PCAPdroid permissions...")
        check_perms_args = ["shell", "dumpsys", "package", "com.emanuelef.remote_capture"]
        stdout_perms, retcode_perms = await self._run_adb_command_async(
            check_perms_args, suppress_stderr=True
        )

        if retcode_perms == 0:
            # Check for critical permissions
            critical_perms = ["android.permission.INTERNET", "android.permission.ACCESS_NETWORK_STATE"]
            missing_perms = []
            for perm in critical_perms:
                if perm not in stdout_perms:
                    missing_perms.append(perm)

            if missing_perms:
                logger.warning(
                    f"[DEBUG] PCAPdroid may be missing permissions: {', '.join(missing_perms)}. "
                    "This may affect capture functionality."
                )
        else:
            logger.warning("[DEBUG] Could not verify PCAPdroid permissions")

        # PCAPdroid package and activity are fixed values
        # According to PCAPdroid API docs: https://github.com/emanuele-f/PCAPdroid/blob/master/docs/app_api.md
        pcapdroid_activity = "com.emanuelef.remote_capture/.activities.CaptureCtrl"

        logger.info(f"Resolved PCAPdroid activity: {pcapdroid_activity}")

        # Generate filename
        sanitized_package = re.sub(r"[^\w.-]+", "_", target_app_package)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.pcap_filename_on_device = (
            f"{sanitized_package}_run{run_id or 'X'}_step{step_num or 'Y'}_{timestamp}.pcap"
        )

        # Resolve output directory - PCAP files go to "pcap" folder
        if session_path:
            traffic_capture_dir = os.path.join(session_path, "pcap")
        elif self.session_folder_manager and run_id:
            # Try to get session path from manager
            from mobile_crawler.infrastructure.database import DatabaseManager
            from mobile_crawler.infrastructure.run_repository import RunRepository

            db_manager = DatabaseManager()
            run_repo = RunRepository(db_manager)
            run = run_repo.get_run_by_id(run_id)
            if run and self.session_folder_manager:
                traffic_capture_dir = self.session_folder_manager.get_subfolder(run, "pcap")
            else:
                traffic_capture_dir = os.path.join("output_data", "traffic_captures")
        else:
            traffic_capture_dir = os.path.join("output_data", "traffic_captures")

        os.makedirs(traffic_capture_dir, exist_ok=True)
        self.local_pcap_file_path = os.path.join(
            traffic_capture_dir, self.pcap_filename_on_device
        )

        # According to PCAPdroid API docs:
        # Command format: adb shell am start -e action [ACTION] -e api_key [API_KEY] -e [SETTINGS] -n com.emanuelef.remote_capture/.activities.CaptureCtrl
        pcap_filename_only = os.path.basename(self.pcap_filename_on_device)

        start_command_args = [
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            pcapdroid_activity,
            "-e",
            "action",
            "start",
            "-e",
            "pcap_dump_mode",
            "pcap_file",
            "-e",
            "app_filter",
            target_app_package,
            "-e",
            "pcap_name",
            pcap_filename_only,
        ]

        if self.config_manager.get("pcapdroid_tls_decryption", False):
            start_command_args.extend(["-e", "tls_decryption", "true"])

        api_key = self.config_manager.get("pcapdroid_api_key")
        if api_key:
            start_command_args.extend(["-e", "api_key", str(api_key)])
        else:
            logger.warning(
                "PCAPDROID_API_KEY not configured. "
                "To avoid PCAPdroid API control prompts, configure an API key that matches "
                "PCAPdroid's Control Permissions API key. Android VPN consent may still need "
                "to be accepted on the device."
            )

        start_ok, start_error = await self._send_start_intent_async(start_command_args)
        if not start_ok:
            logger.error(start_error)
            self.pcap_filename_on_device = None
            self.local_pcap_file_path = None
            self._is_currently_capturing = False
            return False, start_error

        self._is_currently_capturing = True
        self._capture_startup_readiness_passed = None
        self._last_consent_labels_tapped = []
        self._last_capture_startup_diagnostics = {
            "api_start_sent": True,
            "api_start_resent_after_consent": False,
            "consent_accepted_initial": False,
            "consent_labels_tapped": [],
            "api_status_checks": [],
            "ui_action_start_tapped": False,
        }
        consent_accepted_initial = await self._maybe_accept_pcapdroid_consent_async()
        self._last_capture_startup_diagnostics["consent_accepted_initial"] = bool(
            consent_accepted_initial
        )
        self._last_capture_startup_diagnostics["consent_labels_tapped"] = list(
            self._last_consent_labels_tapped
        )

        # Wait for PCAPdroid to initialize (configurable)
        init_wait = float(self.config_manager.get("pcapdroid_init_wait", 3.0))
        if init_wait > 0:
            await asyncio.sleep(init_wait)

        # Verify capture actually started by checking status
        logger.debug("[DEBUG] Sending PCAPdroid capture status query...")
        status_result = await self.get_capture_status_async()
        if isinstance(status_result, dict) and status_result.get("status") == "query_sent":
            logger.debug("[DEBUG] PCAPdroid capture status query sent; no running state parsed from intent output")
        else:
            logger.debug("[DEBUG] Could not send PCAPdroid capture status query")

        # Additional verification: check if PCAPdroid directory exists and is accessible
        device_pcap_base_dir = str(
            self.config_manager.get("device_pcap_dir", "/sdcard/Download/PCAPdroid")
        )
        logger.debug(f"[DEBUG] Checking if PCAPdroid directory exists: {device_pcap_base_dir}")
        check_dir_args = ["shell", "test", "-d", device_pcap_base_dir]
        stdout_dir, retcode_dir = await self._run_adb_command_async(
            check_dir_args, suppress_stderr=True
        )

        if retcode_dir != 0:
            logger.warning(
                f"[DEBUG] PCAPdroid directory does not exist: {device_pcap_base_dir}. "
                f"Attempting to create it..."
            )
            mkdir_args = ["shell", "mkdir", "-p", device_pcap_base_dir]
            stdout_mkdir, retcode_mkdir = await self._run_adb_command_async(
                mkdir_args, suppress_stderr=True
            )
            if retcode_mkdir != 0:
                logger.warning(
                    f"[DEBUG] Failed to create PCAPdroid directory: {stdout_mkdir}. "
                    f"PCAPdroid may create it automatically when capture starts."
                )
        else:
            logger.debug("[DEBUG] PCAPdroid directory exists and is accessible")

        readiness = await self._ensure_capture_started_after_api_async(start_command_args)
        self._last_capture_readiness_diagnostics = readiness
        self._capture_startup_readiness_passed = bool(readiness.get("ready"))
        logger.info(
            "PCAPdroid capture readiness checked: "
            f"ready={readiness.get('ready')}, "
            f"source={readiness.get('readiness_source')}, "
            f"unresolved_consent={readiness.get('unresolved_consent')}, "
            f"vpn_hint={readiness.get('vpn_hint')}, "
            f"pcapdroid_foreground={readiness.get('pcapdroid_foreground')}, "
            f"tapped_consent_labels={self._last_consent_labels_tapped}"
        )
        if not self._capture_startup_readiness_passed:
            error_msg = (
                "PCAPdroid capture did not become ready after startup. "
                "Capture consent may still be pending or the VPN did not become active."
            )
            logger.error(f"{error_msg} Diagnostics: {readiness}")
            self._clear_capture_state()
            return False, error_msg

        logger.info(f"Traffic capture readiness passed: {self.pcap_filename_on_device}")
        return True, "Traffic capture started successfully"

    async def stop_capture_and_pull_async(
        self, run_id: int, step_num: int
    ) -> str | None:
        """Stops PCAPdroid capture, pulls the file, and optionally cleans up.

        Args:
            run_id: Run ID for logging
            step_num: Step number for logging

        Returns:
            Path to the saved PCAP file, or None if failed
        """
        if not self.traffic_capture_enabled:
            return None

        if not self._is_currently_capturing or not self.pcap_filename_on_device:
            logger.warning(
                "Traffic capture not started by this manager or filename not set. Cannot stop/pull."
            )
            return None

        pcapdroid_activity = "com.emanuelef.remote_capture/.activities.CaptureCtrl"

        # Stop capture
        stop_command_args = [
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            pcapdroid_activity,
            "-e",
            "action",
            "stop",
        ]

        api_key = self.config_manager.get("pcapdroid_api_key")
        if api_key:
            stop_command_args.extend(["-e", "api_key", str(api_key)])

        stdout_stop, retcode_stop = await self._run_adb_command_async(
            stop_command_args, suppress_stderr=True
        )
        self._is_currently_capturing = False

        if retcode_stop != 0:
            logger.warning(
                f"PCAPdroid 'stop' command may have failed. ADB retcode: {retcode_stop}. "
                f"Output: {stdout_stop}. Proceeding with pull attempt."
            )
        else:
            logger.debug("[DEBUG] PCAPdroid stop command sent successfully")

        # Wait for file finalization (configurable)
        finalize_wait = float(self.config_manager.get("pcapdroid_finalize_wait", 2.0))
        if finalize_wait > 0:
            logger.debug(f"[DEBUG] Waiting {finalize_wait}s for PCAP file finalization...")
            await asyncio.sleep(finalize_wait)

        # Check PCAPdroid status after stop to verify capture ended
        logger.debug("[DEBUG] Sending PCAPdroid status query after stop...")
        status_result = await self.get_capture_status_async()
        if isinstance(status_result, dict) and status_result.get("status") == "query_sent":
            logger.debug("[DEBUG] PCAPdroid status query after stop sent; no running state parsed from intent output")
        else:
            logger.debug("[DEBUG] Could not send PCAPdroid status query after stop")

        # Pull the file
        if not self.local_pcap_file_path:
            logger.error("Local PCAP file path not set. Cannot pull.")
            return None

        device_pcap_base_dir = str(
            self.config_manager.get("device_pcap_dir", "/sdcard/Download/PCAPdroid")
        )
        device_pcap_full_path = os.path.join(
            device_pcap_base_dir, self.pcap_filename_on_device
        ).replace("\\", "/")

        # Verify file exists on device before attempting to pull
        logger.debug(f"[DEBUG] Checking if PCAP file exists on device: {device_pcap_full_path}")
        check_file_args = ["shell", "test", "-f", device_pcap_full_path]
        stdout_check, retcode_check = await self._run_adb_command_async(check_file_args, suppress_stderr=True)

        if retcode_check != 0:
            logger.warning(f"PCAP file not found at expected location: {device_pcap_full_path}")
            logger.debug(f"[DEBUG] Listing files in PCAPdroid directory: {device_pcap_base_dir}")

            list_files_args = ["shell", "ls", "-la", device_pcap_base_dir]
            stdout_list, retcode_list = await self._run_adb_command_async(list_files_args, suppress_stderr=True)

            if retcode_list == 0:
                logger.debug(f"[DEBUG] Files in {device_pcap_base_dir}:\n{stdout_list}")
                find_pcap_args = ["shell", "find", device_pcap_base_dir, "-name", "*.pcap", "-type", "f"]
                stdout_find, retcode_find = await self._run_adb_command_async(find_pcap_args, suppress_stderr=True)
                if retcode_find == 0 and stdout_find.strip():
                    logger.info(
                        f"PCAP files present in {device_pcap_base_dir}, but not the expected file:\n{stdout_find}"
                    )
                else:
                    logger.error(f"No PCAP files found in {device_pcap_base_dir}")
            else:
                logger.error(f"Failed to list directory {device_pcap_base_dir}: {stdout_list}")

            await self._log_missing_pcap_diagnostics_async()
            logger.error(
                f"PCAP file not found on device at '{device_pcap_full_path}'. "
                "Likely causes: PCAPdroid/API/VPN consent dialog was not accepted, "
                "capture never started, or PCAPdroid saved the file under another name."
            )
            logger.error(
                "  Check if PCAPdroid is running and capturing: "
                "adb shell am start -n com.emanuelef.remote_capture/.activities.CaptureCtrl -e action get_status"
            )
            return None

        logger.debug(f"[DEBUG] PCAP file exists on device, attempting to pull: {device_pcap_full_path}")
        pull_command_args = ["pull", device_pcap_full_path, self.local_pcap_file_path]
        stdout_pull, retcode_pull = await self._run_adb_command_async(pull_command_args)

        if retcode_pull != 0:
            logger.error(
                f"Failed to pull PCAP file '{device_pcap_full_path}'. "
                f"ADB retcode: {retcode_pull}. Output: {stdout_pull}"
            )
            logger.error(
                "  File exists on device but pull failed. Check ADB permissions and device connection."
            )
            return None

        if os.path.exists(self.local_pcap_file_path):
            if os.path.getsize(self.local_pcap_file_path) > 0:
                # Always cleanup device PCAP file after successful pull
                await self._cleanup_device_pcap_file_async(device_pcap_full_path)
                logger.info(f"PCAP file saved: {self.local_pcap_file_path}")
                return os.path.abspath(self.local_pcap_file_path)
            else:
                logger.error(
                    f"PCAP file pulled to '{self.local_pcap_file_path}' but it is EMPTY."
                )
                await self._cleanup_device_pcap_file_async(device_pcap_full_path)
                return None
        else:
            logger.error(
                f"ADB pull command for '{device_pcap_full_path}' seemed to succeed, "
                f"but local file '{self.local_pcap_file_path}' not found."
            )
            return None

    async def _cleanup_device_pcap_file_async(self, device_pcap_full_path: str):
        """Deletes the PCAP file from the device.

        Args:
            device_pcap_full_path: Full path to PCAP file on device
        """
        rm_command_args = ["shell", "rm", device_pcap_full_path]
        stdout_rm, retcode_rm = await self._run_adb_command_async(
            rm_command_args, suppress_stderr=True
        )
        if retcode_rm == 0:
            logger.debug(f"Cleaned up device PCAP file: {device_pcap_full_path}")
        else:
            logger.warning(
                f"Failed to delete device PCAP file '{device_pcap_full_path}'. "
                f"ADB retcode: {retcode_rm}. Output: {stdout_rm}"
            )

    def _clear_capture_state(self) -> None:
        """Clear local capture state after a failed startup."""
        self._is_currently_capturing = False
        self.pcap_filename_on_device = None
        self.local_pcap_file_path = None

    async def _maybe_accept_pcapdroid_consent_async(self) -> bool:
        """Best-effort approval for PCAPdroid/API/VPN consent shown during startup."""
        if not bool(self.config_manager.get("pcapdroid_auto_accept_consent", True)):
            logger.debug("[DEBUG] PCAPdroid consent auto-approval disabled by config")
            return False

        timeout = float(self.config_manager.get("pcapdroid_consent_timeout_seconds", 15.0))
        poll_interval = float(
            self.config_manager.get("pcapdroid_consent_poll_interval_seconds", 1.0)
        )
        if timeout <= 0:
            logger.debug("[DEBUG] PCAPdroid consent auto-approval skipped because timeout is 0")
            return False

        deadline = time.monotonic() + timeout
        inspected = False
        accepted_any = False
        while time.monotonic() < deadline:
            stdout = await self._dump_current_ui_async(
                purpose="PCAPdroid consent inspection"
            )
            if stdout is None:
                await asyncio.sleep(poll_interval)
                continue

            inspected = True
            tap_target = self._find_pcapdroid_consent_button(stdout)
            if tap_target:
                x, y, label = tap_target
                tap_output, tap_retcode = await self._run_adb_command_async(
                    ["shell", "input", "tap", str(x), str(y)],
                    suppress_stderr=True,
                )
                if tap_retcode == 0:
                    logger.info(f"Accepted PCAPdroid capture consent via '{label}' button")
                    self._last_consent_labels_tapped.append(label)
                    accepted_any = True
                    await asyncio.sleep(poll_interval)
                    continue
                logger.warning(
                    f"Found PCAPdroid consent button '{label}' but tap failed: {tap_output}"
                )
                return False

            if accepted_any:
                logger.debug("[DEBUG] No further PCAPdroid capture consent dialog found")
                return True
            await asyncio.sleep(poll_interval)

        if inspected:
            logger.debug("[DEBUG] No PCAPdroid capture consent dialog found during startup")
        else:
            logger.debug("[DEBUG] PCAPdroid consent dialog could not be inspected")
        return accepted_any

    async def _dump_current_ui_async(self, purpose: str) -> str | None:
        dump_path = "/sdcard/ui_dump.xml"
        dump_output, dump_retcode = await self._run_adb_command_async(
            ["shell", "uiautomator", "dump", dump_path],
            suppress_stderr=True,
        )
        if dump_retcode != 0:
            logger.debug(f"[DEBUG] Could not dump UI for {purpose}. Output: {dump_output}")
            return None

        stdout, retcode = await self._run_adb_command_async(
            ["shell", "cat", dump_path],
            suppress_stderr=True,
        )
        if retcode != 0:
            logger.debug(f"[DEBUG] Could not read UI dump for {purpose}. Output: {stdout}")
            return None
        return stdout

    async def _check_capture_readiness_async(self, api_status_running: bool | None = None) -> dict[str, Any]:
        ui_dump = await self._dump_current_ui_async(purpose="PCAPdroid readiness check")
        unresolved = bool(ui_dump and self._find_pcapdroid_consent_button(ui_dump))
        pcapdroid_foreground = self._ui_dump_has_package(ui_dump or "")
        ui_running_hint = self._ui_dump_has_running_capture_hint(ui_dump or "")

        connectivity_output, connectivity_retcode = await self._run_adb_command_async(
            ["shell", "dumpsys", "connectivity"],
            suppress_stderr=True,
        )
        services_output, services_retcode = await self._run_adb_command_async(
            ["shell", "dumpsys", "activity", "services", "com.emanuelef.remote_capture"],
            suppress_stderr=True,
        )
        connectivity_lower = connectivity_output.lower()
        services_lower = services_output.lower()
        package_name = "com.emanuelef.remote_capture"
        vpn_hint = (
            (
                connectivity_retcode == 0
                and "vpn" in connectivity_lower
                and package_name in connectivity_lower
            )
            or (
                services_retcode == 0
                and package_name in services_lower
                and any(term in services_lower for term in ("vpn", "capture", "pcap"))
            )
        )
        readiness_source = None
        if not unresolved and api_status_running is True:
            readiness_source = "api_status_running"
        elif not unresolved and ui_running_hint:
            readiness_source = "ui_status_running"
        elif not unresolved and vpn_hint:
            readiness_source = "vpn_or_service"
        ready = readiness_source is not None
        return {
            "ready": ready,
            "readiness_source": readiness_source,
            "unresolved_consent": unresolved,
            "pcapdroid_foreground": pcapdroid_foreground,
            "api_status_running": api_status_running,
            "ui_running_hint": ui_running_hint,
            "vpn_hint": vpn_hint,
            "connectivity_retcode": connectivity_retcode,
            "services_retcode": services_retcode,
            "connectivity_snippet": self._diagnostic_snippet(connectivity_output),
            "services_snippet": self._diagnostic_snippet(services_output),
            "ui_snippet": self._diagnostic_snippet(ui_dump or ""),
        }

    async def _ensure_capture_started_after_api_async(self, start_command_args: list[str]) -> dict[str, Any]:
        """Ensure API startup reaches active capture, including post-consent re-send and strict start fallback."""
        timeout = float(self.config_manager.get("pcapdroid_startup_timeout_seconds", 15.0))
        poll_interval = float(
            self.config_manager.get("pcapdroid_startup_poll_interval_seconds", 1.0)
        )
        deadline = time.monotonic() + max(timeout, 0.0)
        api_checks: list[dict[str, Any]] = []
        last_readiness: dict[str, Any] = {}
        restarted_after_consent = False
        ui_start_tapped = False
        consent_seen_during_startup = bool(
            self._last_capture_startup_diagnostics.get("consent_accepted_initial")
        ) or bool(self._last_consent_labels_tapped)

        while True:
            api_status = await self.get_capture_status_async()
            api_running = api_status.get("running") if isinstance(api_status, dict) else None
            readiness = await self._check_capture_readiness_async(
                api_status_running=api_running if isinstance(api_running, bool) else None
            )
            readiness["startup_phase"] = "api_status_polling"
            readiness["api_start_sent"] = bool(
                self._last_capture_startup_diagnostics.get("api_start_sent")
            )
            readiness["consent_labels_tapped"] = list(self._last_consent_labels_tapped)
            readiness["api_status"] = api_status
            readiness["api_start_resent_after_consent"] = restarted_after_consent
            readiness["ui_action_start_tapped"] = ui_start_tapped
            api_checks.append(
                {
                    "running": api_status.get("running") if isinstance(api_status, dict) else None,
                    "status": api_status.get("status") if isinstance(api_status, dict) else "unknown",
                }
            )
            last_readiness = readiness

            if readiness.get("ready"):
                readiness["final_reason"] = "api_readiness_confirmed"
                self._last_capture_startup_diagnostics.update(
                    {
                        "consent_labels_tapped": list(self._last_consent_labels_tapped),
                        "api_status_checks": api_checks,
                    }
                )
                return readiness

            if time.monotonic() >= deadline:
                break

            consented = await self._maybe_accept_pcapdroid_consent_async()
            self._last_capture_startup_diagnostics["consent_labels_tapped"] = list(
                self._last_consent_labels_tapped
            )
            if consented:
                consent_seen_during_startup = True
            if consent_seen_during_startup and not restarted_after_consent:
                logger.info(
                    "PCAPdroid consent accepted; re-sending API start intent to apply capture settings"
                )
                await asyncio.sleep(1.0)
                resend_ok, resend_error = await self._send_start_intent_async(start_command_args)
                if not resend_ok:
                    last_readiness["final_reason"] = "api_resend_failed_after_consent"
                    last_readiness["api_resend_error"] = resend_error
                    self._last_capture_startup_diagnostics.update(
                        {
                            "consent_labels_tapped": list(self._last_consent_labels_tapped),
                            "api_status_checks": api_checks,
                            "api_start_resent_after_consent": restarted_after_consent,
                            "ui_action_start_tapped": ui_start_tapped,
                        }
                    )
                    return last_readiness
                restarted_after_consent = True
                self._last_capture_startup_diagnostics["api_start_resent_after_consent"] = True
            elif (
                not consented
                and not ui_start_tapped
                and not bool(readiness.get("unresolved_consent"))
            ):
                ui_start_tapped = await self._tap_pcapdroid_start_button_if_visible_async()
                self._last_capture_startup_diagnostics["ui_action_start_tapped"] = ui_start_tapped
            await asyncio.sleep(max(poll_interval, 0.1))

        last_readiness["final_reason"] = "not_ready_after_api_polling"
        self._last_capture_startup_diagnostics.update(
            {
                "consent_labels_tapped": list(self._last_consent_labels_tapped),
                "api_status_checks": api_checks,
                "api_start_resent_after_consent": restarted_after_consent,
                "ui_action_start_tapped": ui_start_tapped,
            }
        )
        return last_readiness

    async def _send_start_intent_async(self, start_command_args: list[str]) -> tuple[bool, str]:
        stdout, retcode = await self._run_adb_command_async(start_command_args)
        if retcode != 0:
            return False, f"Failed to start PCAPdroid. ADB retcode: {retcode}. Output: {stdout}"
        error_indicators = ["Error", "error", "does not exist", "Activity class", "Unable to resolve"]
        if any(indicator in stdout for indicator in error_indicators):
            return False, f"PCAPdroid start failed (error in output): {stdout}"
        return True, ""

    async def _tap_pcapdroid_start_button_if_visible_async(self) -> bool:
        """Tap only PCAPdroid's action_start control when present on the foreground UI."""
        ui_dump = await self._dump_current_ui_async(purpose="PCAPdroid action_start fallback")
        if not ui_dump:
            return False

        xml_text = self._extract_uiautomator_xml(ui_dump)
        if not xml_text:
            return False

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return False

        for node in root.iter("node"):
            if str(node.attrib.get("package", "")).lower() != "com.emanuelef.remote_capture":
                continue
            resource_id = str(node.attrib.get("resource-id", "")).strip()
            text = str(node.attrib.get("text", "")).strip().lower()
            if resource_id != "com.emanuelef.remote_capture:id/action_start" and text != "start":
                continue
            bounds = str(node.attrib.get("bounds", ""))
            center = self._bounds_center(bounds)
            if not center:
                continue
            x, y = center
            tap_output, tap_retcode = await self._run_adb_command_async(
                ["shell", "input", "tap", str(x), str(y)],
                suppress_stderr=True,
            )
            if tap_retcode != 0:
                logger.warning(
                    f"Failed to tap PCAPdroid action_start fallback at ({x}, {y}): {tap_output}"
                )
                return False
            logger.info(f"Tapped PCAPdroid action_start fallback at ({x}, {y})")
            await asyncio.sleep(1.5)
            return True
        return False

    def _ui_dump_has_running_capture_hint(self, ui_dump: str) -> bool:
        xml_text = self._extract_uiautomator_xml(ui_dump)
        if not xml_text:
            return False
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return False
        status_text = ""
        for node in root.iter("node"):
            resource_id = str(node.attrib.get("resource-id", "")).strip()
            if resource_id.endswith("/status_view"):
                status_text = str(
                    node.attrib.get("text", "") or node.attrib.get("content-desc", "")
                ).strip().lower()
                break
        if not status_text:
            return False
        return "running" in status_text and "ready" not in status_text

    def _ui_dump_has_package(self, ui_dump: str) -> bool:
        xml_text = self._extract_uiautomator_xml(ui_dump)
        if not xml_text:
            return False
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return False
        return any(
            str(node.attrib.get("package", "")).lower() == "com.emanuelef.remote_capture"
            for node in root.iter("node")
        )

    async def _log_missing_pcap_diagnostics_async(self) -> None:
        ui_dump = await self._dump_current_ui_async(purpose="missing PCAP diagnostics")
        connectivity_output, connectivity_retcode = await self._run_adb_command_async(
            ["shell", "dumpsys", "connectivity"],
            suppress_stderr=True,
        )
        services_output, services_retcode = await self._run_adb_command_async(
            ["shell", "dumpsys", "activity", "services", "com.emanuelef.remote_capture"],
            suppress_stderr=True,
        )
        logger.error(
            "Missing PCAP diagnostics: "
            f"startup_readiness_passed={self._capture_startup_readiness_passed}, "
            f"tapped_consent_labels={self._last_consent_labels_tapped}, "
            f"startup_diagnostics={self._last_capture_startup_diagnostics}, "
            f"last_readiness={self._last_capture_readiness_diagnostics}"
        )
        logger.error(
            "Missing PCAP final UI dump snippet: "
            f"{self._diagnostic_snippet(ui_dump or '')}"
        )
        logger.error(
            "Missing PCAP connectivity diagnostics "
            f"(retcode={connectivity_retcode}): "
            f"{self._diagnostic_snippet(connectivity_output)}"
        )
        logger.error(
            "Missing PCAP PCAPdroid service diagnostics "
            f"(retcode={services_retcode}): "
            f"{self._diagnostic_snippet(services_output)}"
        )

    @staticmethod
    def _diagnostic_snippet(text: str, limit: int = 1000) -> str:
        compact = " ".join(str(text).split())
        if len(compact) <= limit:
            return compact
        return compact[:limit] + "..."

    def _find_pcapdroid_consent_button(self, ui_dump: str) -> tuple[int, int, str] | None:
        """Return the center of a safe consent button when the dump has capture context."""
        xml_text = self._extract_uiautomator_xml(ui_dump)
        if not xml_text:
            logger.debug("[DEBUG] No XML hierarchy found in UI dump")
            return None

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.debug(f"[DEBUG] XML parse error while checking PCAPdroid consent: {exc}")
            return None

        context_terms = (
            "capture your device traffic",
            "control request",
            "pcapdroid",
            "vpn",
        )
        approval_labels = {"allow", "ok", "start now"}
        dump_text_parts: list[str] = []
        for node in root.iter("node"):
            dump_text_parts.extend(
                str(node.attrib.get(attr, ""))
                for attr in ("text", "content-desc", "resource-id", "package")
            )
        dump_text = " ".join(dump_text_parts).lower()
        logger.debug(f"[DEBUG] Full UI dump text while checking PCAPdroid consent: {dump_text}")
        if not any(term in dump_text for term in context_terms):
            logger.debug("[DEBUG] No PCAPdroid context terms found in UI dump")
            return None

        for node in root.iter("node"):
            label = str(node.attrib.get("text", "") or node.attrib.get("content-desc", "")).strip()
            if label.lower() not in approval_labels:
                continue
            bounds = str(node.attrib.get("bounds", ""))
            center = self._bounds_center(bounds)
            if center:
                logger.debug(f"[DEBUG] Found consent button '{label}' at {center}")
                return center[0], center[1], label
            logger.debug(
                f"[DEBUG] Found label '{label}' but could not parse bounds: '{bounds}'"
            )
        return None

    @staticmethod
    def _extract_uiautomator_xml(ui_dump: str) -> str | None:
        start = ui_dump.find("<hierarchy")
        end = ui_dump.rfind("</hierarchy>")
        if start == -1 or end == -1:
            return None
        return ui_dump[start : end + len("</hierarchy>")]

    @staticmethod
    def _bounds_center(bounds: str) -> tuple[int, int] | None:
        parsed = TrafficCaptureManager._parse_bounds(bounds)
        if not parsed:
            return None
        left, top, right, bottom = parsed
        return (left + right) // 2, (top + bottom) // 2

    @staticmethod
    def _parse_bounds(bounds: str) -> tuple[int, int, int, int] | None:
        match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
        if not match:
            return None
        left, top, right, bottom = (int(value) for value in match.groups())
        return left, top, right, bottom

    async def get_capture_status_async(self) -> dict[str, Any]:
        """Gets the current capture status using PCAPdroid API.

        Returns:
            Dictionary with status information
        """
        if not self.traffic_capture_enabled:
            return {
                "status": "disabled",
                "running": False,
                "error": "Traffic capture not enabled by config.",
            }

        pcapdroid_activity = "com.emanuelef.remote_capture/.activities.CaptureCtrl"

        status_command_args = [
            "shell",
            "am",
            "start",
            "-W",
            "-n",
            pcapdroid_activity,
            "-e",
            "action",
            "get_status",
        ]

        api_key = self.config_manager.get("pcapdroid_api_key")
        if api_key:
            status_command_args.extend(["-e", "api_key", str(api_key)])

        stdout, retcode = await self._run_adb_command_async(status_command_args)

        if retcode != 0:
            logger.error(
                f"Failed to send 'get_status' command to PCAPdroid. "
                f"ADB retcode: {retcode}. Output: {stdout}"
            )
            return {
                "status": "error",
                "error_message": f"ADB command failed: {stdout}",
            }

        running = self._parse_running_from_status_output(stdout)
        return {
            "status": "query_sent",
            "running": running,
            "raw_output": stdout,
        }

    @staticmethod
    def _parse_running_from_status_output(output: str) -> bool | None:
        lowered = str(output).lower()
        if re.search(r"\brunning\s*[:=]\s*true\b", lowered):
            return True
        if re.search(r"\brunning\s*[:=]\s*false\b", lowered):
            return False
        return None
