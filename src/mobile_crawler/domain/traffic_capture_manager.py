"""Traffic capture manager for PCAPdroid integration."""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class TrafficCaptureConfig:
    """Configuration for traffic capture."""
    enabled: bool
    pcapdroid_package: str = "com.emanuelef.android.apps.pcapdroid"
    output_path: Optional[str] = None


class TrafficCaptureManager:
    """Manages traffic capture using PCAPdroid.

    Handles starting/stopping traffic capture via ADB intent API,
    pulling PCAP files from device, and graceful handling when
    PCAPdroid is not installed.
    """

    def __init__(self, adb_client=None):
        """Initialize the traffic capture manager.

        Args:
            adb_client: Optional ADB client wrapper for executing commands
        """
        self._adb_client = adb_client
        self._is_capturing = False
        self._pcapdroid_installed: Optional[bool] = None
        self._config: Optional[TrafficCaptureConfig] = None

    def is_installed(self) -> bool:
        """Check if PCAPdroid is installed on the device.

        Returns:
            True if PCAPdroid is installed, False otherwise
        """
        if self._pcapdroid_installed is not None:
            return self._pcapdroid_installed

        try:
            # Check if PCAPdroid package is installed
            result = self._execute_adb_command(
                "shell pm list packages | grep pcapdroid"
            )
            self._pcapdroid_installed = "pcapdroid" in (result or "")
            return self._pcapdroid_installed
        except Exception as e:
            logger.error(f"Error checking PCAPdroid installation: {e}")
            self._pcapdroid_installed = False
            return False

    def configure(self, config: TrafficCaptureConfig) -> None:
        """Configure traffic capture settings.

        Args:
            config: TrafficCaptureConfig with capture settings
        """
        self._config = config
        logger.info(f"Traffic capture configured: enabled={config.enabled}")

    def start(self) -> bool:
        """Start traffic capture using PCAPdroid.

        Sends intent to PCAPdroid to start capturing network traffic.

        Returns:
            True if capture started successfully, False otherwise
        """
        if not self._config or not self._config.enabled:
            logger.info("Traffic capture disabled, skipping start")
            return False

        if not self.is_installed():
            logger.warning(
                "PCAPdroid not installed. Traffic capture will be skipped. "
                "Install PCAPdroid from F-Droid to enable network traffic capture."
            )
            return False

        try:
            # Send intent to start capture
            # PCAPdroid uses broadcast intents for control
            self._execute_adb_command(
                "shell am broadcast -a com.emanuelef.android.apps.pcapdroid.START_CAPTURE"
            )
            self._is_capturing = True
            logger.info("Traffic capture started via PCAPdroid")
            return True
        except Exception as e:
            logger.error(f"Failed to start traffic capture: {e}")
            self._is_capturing = False
            return False

    def stop_and_pull(self, output_path: Optional[str] = None) -> Optional[str]:
        """Stop traffic capture and pull PCAP file from device.

        Args:
            output_path: Optional local path to save PCAP file.
                        If None, uses path from config or generates default name.

        Returns:
            Path to the saved PCAP file, or None if capture wasn't running
        """
        if not self._is_capturing:
            logger.info("Traffic capture not running, nothing to stop")
            return None

        try:
            # Send intent to stop capture
            self._execute_adb_command(
                "shell am broadcast -a com.emanuelef.android.apps.pcapdroid.STOP_CAPTURE"
            )
            self._is_capturing = False
            logger.info("Traffic capture stopped")

            # Determine output path
            if output_path is None:
                output_path = self._config.output_path if self._config else None

            if output_path is None:
                import time
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                output_path = f"traffic_capture_{timestamp}.pcap"

            # Pull PCAP file from device
            # PCAPdroid saves to /sdcard/Download/ by default
            device_pcap_path = "/sdcard/Download/pcapdroid_capture.pcap"

            # Check if file exists on device
            file_exists = self._execute_adb_command(
                f"shell test -f {device_pcap_path} && echo 'exists' || echo 'not_exists'"
            )

            if "not_exists" in (file_exists or ""):
                logger.warning(
                    f"PCAP file not found on device at {device_pcap_path}. "
                    "PCAPdroid may not have captured any traffic."
                )
                return None

            # Pull file to local path
            self._execute_adb_command(f"pull {device_pcap_path} {output_path}")
            logger.info(f"PCAP file pulled to {output_path}")

            # Clean up file on device
            self._execute_adb_command(f"shell rm {device_pcap_path}")

            return output_path

        except Exception as e:
            logger.error(f"Failed to stop and pull traffic capture: {e}")
            self._is_capturing = False
            return None

    def is_capturing(self) -> bool:
        """Check if traffic capture is currently running.

        Returns:
            True if capture is active, False otherwise
        """
        return self._is_capturing

    def get_status(self) -> Dict[str, Any]:
        """Get current traffic capture status.

        Returns:
            Dictionary with status information:
            - capturing: bool
            - installed: bool
            - enabled: bool
        """
        return {
            "capturing": self._is_capturing,
            "installed": self.is_installed(),
            "enabled": self._config.enabled if self._config else False,
        }

    def _execute_adb_command(self, command: str) -> Optional[str]:
        """Execute an ADB command.

        Args:
            command: ADB command to execute (without 'adb' prefix)

        Returns:
            Command output, or None if command failed
        """
        if self._adb_client:
            return self._adb_client.execute(command)

        # Fallback to subprocess if no ADB client provided
        import subprocess
        try:
            result = subprocess.run(
                ["adb"] + command.split(),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.error(f"ADB command timed out: {command}")
            return None
        except FileNotFoundError:
            logger.error("ADB not found in PATH")
            return None
        except Exception as e:
            logger.error(f"ADB command failed: {e}")
            return None
