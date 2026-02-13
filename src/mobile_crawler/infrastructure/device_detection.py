"""Device detection utilities for Android devices using ADB."""

import subprocess
import re
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AndroidDevice:
    """Represents an Android device detected via ADB."""
    device_id: str
    status: str  # 'device', 'offline', 'unauthorized', etc.
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    android_version: Optional[str] = None
    api_level: Optional[int] = None

    @property
    def is_available(self) -> bool:
        """Check if device is available for testing."""
        return self.status == 'device'

    @property
    def display_name(self) -> str:
        """Get a human-readable display name for the device."""
        parts = []
        if self.manufacturer:
            parts.append(self.manufacturer)
        if self.model:
            parts.append(self.model)
        if parts:
            return f"{' '.join(parts)} ({self.device_id})"
        else:
            return self.device_id


class DeviceDetectionError(Exception):
    """Raised when device detection fails."""
    pass


class ADBNotFoundError(DeviceDetectionError):
    """Raised when ADB is not found."""
    pass


class DeviceDetection:
    """Handles detection and information retrieval for Android devices via ADB."""

    def __init__(self, adb_path: Optional[str] = None):
        """Initialize device detection.

        Args:
            adb_path: Path to ADB executable. If None, uses 'adb' from PATH.
        """
        self.adb_path = adb_path or 'adb'
        self._check_adb_available()

    def _check_adb_available(self) -> None:
        """Check if ADB is available and working."""
        try:
            result = subprocess.run(
                [self.adb_path, 'version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise ADBNotFoundError(f"ADB command failed: {result.stderr}")
        except FileNotFoundError:
            raise ADBNotFoundError("ADB executable not found in PATH")

    def _run_adb_command(self, args: List[str], timeout: int = 30) -> Tuple[str, str]:
        """Run an ADB command and return stdout, stderr.

        Args:
            args: ADB command arguments
            timeout: Command timeout in seconds

        Returns:
            Tuple of (stdout, stderr)

        Raises:
            DeviceDetectionError: If command fails
        """
        try:
            result = subprocess.run(
                [self.adb_path] + args,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            raise DeviceDetectionError(f"ADB command timed out: {' '.join(args)}")
        except Exception as e:
            raise DeviceDetectionError(f"ADB command failed: {e}") from e

    def get_connected_devices(self) -> List[AndroidDevice]:
        """Get list of connected Android devices.

        Returns:
            List of AndroidDevice objects

        Raises:
            DeviceDetectionError: If device detection fails
        """
        stdout, stderr = self._run_adb_command(['devices', '-l'])

        devices = []
        lines = stdout.strip().split('\n')

        # Skip the first line ("List of devices attached")
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            # Parse device line: "device_id status [properties...]"
            # Split by whitespace, device_id is first, status is second
            parts = line.split()
            if len(parts) < 2:
                continue

            device_id = parts[0]
            status = parts[1]

            device = AndroidDevice(device_id=device_id, status=status)

            # Parse additional properties if available (everything after status)
            if len(parts) > 2:
                properties = ' '.join(parts[2:])
                device = self._parse_device_properties(device, properties)

            # Get detailed device info if device is available
            if device.is_available:
                try:
                    device = self._get_device_details(device)
                except Exception as e:
                    logger.warning(f"Failed to get details for device {device_id}: {e}")

            devices.append(device)

        return devices

    def _parse_device_properties(self, device: AndroidDevice, properties: str) -> AndroidDevice:
        """Parse device properties from ADB devices -l output.

        Args:
            device: Device object to update
            properties: Properties string from ADB

        Returns:
            Updated device object
        """
        # Properties are in format: "key:value key:value ..."
        prop_pattern = re.compile(r'(\w+):([^\s]+)')
        matches = prop_pattern.findall(properties)

        for key, value in matches:
            if key == 'model':
                device.model = value
            elif key == 'device':
                # 'device' here refers to the product name, not device_id
                pass
            elif key == 'transport_id':
                pass  # Not needed for our purposes

        return device

    def _get_device_details(self, device: AndroidDevice) -> AndroidDevice:
        """Get detailed information about a device.

        Args:
            device: Device object to update

        Returns:
            Updated device object with detailed info
        """
        # Get manufacturer and model from getprop
        manufacturer = self._get_device_prop(device.device_id, 'ro.product.manufacturer')
        if manufacturer:
            device.manufacturer = manufacturer.capitalize()

        model = self._get_device_prop(device.device_id, 'ro.product.model')
        if model:
            device.model = model

        # Get Android version
        android_version = self._get_device_prop(device.device_id, 'ro.build.version.release')
        if android_version:
            device.android_version = android_version

        # Get API level
        api_level_str = self._get_device_prop(device.device_id, 'ro.build.version.sdk')
        if api_level_str:
            try:
                device.api_level = int(api_level_str)
            except ValueError:
                pass

        return device

    def _get_device_prop(self, device_id: str, prop: str) -> Optional[str]:
        """Get a device property using ADB shell getprop.

        Args:
            device_id: Device ID
            prop: Property name

        Returns:
            Property value or None if not found
        """
        try:
            stdout, stderr = self._run_adb_command(['-s', device_id, 'shell', 'getprop', prop])
            value = stdout.strip()
            return value if value else None
        except Exception:
            return None

    def get_available_devices(self) -> List[AndroidDevice]:
        """Get list of available (online) Android devices.

        Returns:
            List of available AndroidDevice objects
        """
        devices = self.get_connected_devices()
        return [d for d in devices if d.is_available]

    def find_device_by_id(self, device_id: str) -> Optional[AndroidDevice]:
        """Find a device by its ID.

        Args:
            device_id: Device ID to search for

        Returns:
            AndroidDevice object or None if not found
        """
        devices = self.get_connected_devices()
        for device in devices:
            if device.device_id == device_id:
                return device
        return None

    def wait_for_device(self, device_id: Optional[str] = None, timeout: int = 60) -> AndroidDevice:
        """Wait for a device to become available.

        Args:
            device_id: Specific device ID to wait for, or None for any device
            timeout: Maximum time to wait in seconds

        Returns:
            Available AndroidDevice

        Raises:
            DeviceDetectionError: If timeout expires or device not found
        """
        import time

        start_time = time.time()
        while time.time() - start_time < timeout:
            if device_id:
                device = self.find_device_by_id(device_id)
                if device and device.is_available:
                    return device
            else:
                devices = self.get_available_devices()
                if devices:
                    return devices[0]

            time.sleep(1)

        if device_id:
            raise DeviceDetectionError(f"Device {device_id} not found or not available within {timeout} seconds")
        else:
            raise DeviceDetectionError(f"No available devices found within {timeout} seconds")