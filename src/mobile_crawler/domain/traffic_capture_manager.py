"""Traffic capture manager for PCAPdroid integration."""

import asyncio
import logging
import os
import re
import time
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
    ):
        """Initialize the traffic capture manager.

        Args:
            config_manager: Configuration manager instance
            adb_client: Optional ADB client wrapper for executing commands
            session_folder_manager: Optional session folder manager for path resolution
        """
        self.config_manager = config_manager
        self.adb_client = adb_client
        self.session_folder_manager = session_folder_manager

        self.traffic_capture_enabled: bool = bool(
            config_manager.get("enable_traffic_capture", False)
        )
        logger.debug(f"TrafficCaptureManager initialized, enabled: {self.traffic_capture_enabled}")

        self.pcap_filename_on_device: Optional[str] = None
        self.local_pcap_file_path: Optional[str] = None
        self._is_currently_capturing: bool = False

        # Package: com.emanuelef.remote_capture
        # Activity: com.emanuelef.remote_capture/.activities.CaptureCtrl

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
            return await self.adb_client.execute_async(command_list, suppress_stderr)

        # Fallback: create temporary ADB client
        from mobile_crawler.infrastructure.adb_client import ADBClient

        adb_executable = self.config_manager.get("adb_executable_path", "adb")
        temp_client = ADBClient(adb_executable=adb_executable)
        return await temp_client.execute_async(command_list, suppress_stderr)

    def is_capturing(self) -> bool:
        """Returns the internal state of whether capture is thought to be active."""
        return self._is_currently_capturing

    async def start_capture_async(
        self,
        run_id: Optional[int] = None,
        step_num: Optional[int] = None,
        session_path: Optional[str] = None,
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

        if self._is_currently_capturing:
            return True, "Traffic capture already started"

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
                "PCAPDROID_API_KEY not configured. User consent on device may be required."
            )

        stdout, retcode = await self._run_adb_command_async(start_command_args)

        # Check both return code and stderr for errors
        if retcode != 0:
            error_msg = f"Failed to start PCAPdroid. ADB retcode: {retcode}. Output: {stdout}"
            logger.error(error_msg)
            self.pcap_filename_on_device = None
            self.local_pcap_file_path = None
            self._is_currently_capturing = False
            return False, error_msg

        # Also check stdout/stderr for error messages even if retcode is 0
        error_indicators = ["Error", "error", "does not exist", "Activity class", "Unable to resolve"]
        if any(indicator in stdout for indicator in error_indicators):
            error_msg = f"PCAPdroid start failed (error in output): {stdout}"
            logger.error(error_msg)
            self.pcap_filename_on_device = None
            self.local_pcap_file_path = None
            self._is_currently_capturing = False
            return False, error_msg

        self._is_currently_capturing = True

        # Wait for PCAPdroid to initialize (configurable)
        init_wait = float(self.config_manager.get("pcapdroid_init_wait", 3.0))
        if init_wait > 0:
            await asyncio.sleep(init_wait)

        # Verify capture actually started by checking status
        logger.debug("[DEBUG] Verifying PCAPdroid capture status...")
        status_result = await self.get_capture_status_async()
        if isinstance(status_result, dict):
            running = status_result.get("running", False)
            if running:
                logger.debug("[DEBUG] PCAPdroid capture verified as running")
            else:
                logger.warning("[DEBUG] PCAPdroid capture may not have started (status check returned not running)")
        else:
            logger.debug("[DEBUG] Could not verify PCAPdroid capture status (status check failed)")

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

        logger.info(f"Traffic capture started: {self.pcap_filename_on_device}")
        return True, "Traffic capture started successfully"

    async def stop_capture_and_pull_async(
        self, run_id: int, step_num: int
    ) -> Optional[str]:
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
        logger.debug("[DEBUG] Checking PCAPdroid status after stop...")
        status_result = await self.get_capture_status_async()
        if isinstance(status_result, dict):
            running = status_result.get("running", False)
            if not running:
                logger.debug("[DEBUG] PCAPdroid capture confirmed as stopped")
            else:
                logger.warning(
                    "[DEBUG] PCAPdroid may still be running according to status check. "
                    "This could indicate a timing issue or that capture never started properly."
                )
        else:
            logger.debug("[DEBUG] Could not verify PCAPdroid status after stop")

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
            # File doesn't exist, list directory to see what files are there
            logger.warning(f"PCAP file not found at expected location: {device_pcap_full_path}")
            logger.debug(f"[DEBUG] Listing files in PCAPdroid directory: {device_pcap_base_dir}")

            list_files_args = ["shell", "ls", "-la", device_pcap_base_dir]
            stdout_list, retcode_list = await self._run_adb_command_async(list_files_args, suppress_stderr=True)

            if retcode_list == 0:
                logger.debug(f"[DEBUG] Files in {device_pcap_base_dir}:\n{stdout_list}")
                # Try to find any .pcap files that might match
                find_pcap_args = ["shell", "find", device_pcap_base_dir, "-name", "*.pcap", "-type", "f"]
                stdout_find, retcode_find = await self._run_adb_command_async(find_pcap_args, suppress_stderr=True)
                if retcode_find == 0 and stdout_find.strip():
                    logger.info(f"[DEBUG] Found PCAP files on device:\n{stdout_find}")
                    # Try to use the most recent one or one matching our pattern
                    pcap_files = [f.strip() for f in stdout_find.strip().split('\n') if f.strip()]
                    if pcap_files:
                        # Look for one that matches our expected filename pattern
                        expected_base = os.path.splitext(self.pcap_filename_on_device)[0]
                        matching_file = None
                        for pcap_file in pcap_files:
                            if expected_base in pcap_file or self.pcap_filename_on_device in pcap_file:
                                matching_file = pcap_file
                                break

                        if matching_file:
                            logger.info(f"[DEBUG] Using matching PCAP file: {matching_file}")
                            device_pcap_full_path = matching_file
                        else:
                            # Use the most recent file (last in list, or try to get by modification time)
                            logger.warning(f"[DEBUG] No exact match found, using first available: {pcap_files[0]}")
                            device_pcap_full_path = pcap_files[0]
                            # Update filename to match
                            self.pcap_filename_on_device = os.path.basename(device_pcap_full_path)
                            # Update local path to match new filename
                            self.local_pcap_file_path = os.path.join(
                                os.path.dirname(self.local_pcap_file_path),
                                self.pcap_filename_on_device
                            )

                        # Verify the fallback file actually exists before proceeding
                        logger.debug(f"[DEBUG] Verifying fallback file exists: {device_pcap_full_path}")
                        check_fallback_args = ["shell", "test", "-f", device_pcap_full_path]
                        stdout_fallback, retcode_fallback = await self._run_adb_command_async(
                            check_fallback_args, suppress_stderr=True
                        )

                        if retcode_fallback == 0:
                            logger.info("[DEBUG] Fallback file verified, proceeding with pull")
                        else:
                            logger.error(
                                f"[DEBUG] Fallback file does not exist: {device_pcap_full_path}. "
                                f"This may indicate a file system issue or timing problem."
                            )
                            # Try one more time with a longer wait
                            logger.warning("[DEBUG] Waiting 3 seconds and retrying file check...")
                            await asyncio.sleep(3)

                            stdout_retry, retcode_retry = await self._run_adb_command_async(
                                check_fallback_args, suppress_stderr=True
                            )

                            if retcode_retry != 0:
                                logger.error(
                                    f"PCAP file not found on device at '{device_pcap_full_path}'. "
                                    f"PCAPdroid may not have started capture, or file was saved with different name."
                                )
                                logger.error(
                                    "  Check if PCAPdroid is running and capturing: "
                                    "adb shell am start -n com.emanuelef.remote_capture/.activities.CaptureCtrl -e action get_status"
                                )
                                return None
                else:
                    logger.error(f"[DEBUG] No PCAP files found in {device_pcap_base_dir}")
            else:
                logger.error(f"[DEBUG] Failed to list directory {device_pcap_base_dir}: {stdout_list}")

            logger.error(
                f"PCAP file not found on device at '{device_pcap_full_path}'. "
                f"PCAPdroid may not have started capture, or file was saved with different name."
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
                logger.warning(
                    f"PCAP file pulled to '{self.local_pcap_file_path}' but it is EMPTY."
                )
                await self._cleanup_device_pcap_file_async(device_pcap_full_path)
                return os.path.abspath(self.local_pcap_file_path)
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
                "running": self._is_currently_capturing,
                "error_message": f"ADB command failed: {stdout}",
            }

        # Directly parsing complex status from 'am start' stdout is unreliable.
        # The 'running' status here is based on our manager's internal flag.
        return {
            "status": "query_sent",
            "running": self._is_currently_capturing,
            "raw_output": stdout,
        }
