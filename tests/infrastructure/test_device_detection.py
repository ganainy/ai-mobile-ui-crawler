"""Tests for device detection functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from subprocess import CompletedProcess

from mobile_crawler.infrastructure.device_detection import (
    DeviceDetection,
    AndroidDevice,
    DeviceDetectionError,
    ADBNotFoundError
)


class TestAndroidDevice:
    """Test AndroidDevice dataclass."""

    def test_device_properties(self):
        """Test device property methods."""
        device = AndroidDevice(
            device_id='emulator-5554',
            status='device',
            model='Pixel_4',
            manufacturer='Google',
            android_version='12',
            api_level=31
        )

        assert device.is_available is True
        assert device.display_name == 'Google Pixel_4 (emulator-5554)'

    def test_device_not_available(self):
        """Test device not available."""
        device = AndroidDevice(device_id='emulator-5554', status='offline')
        assert device.is_available is False

    def test_display_name_fallback(self):
        """Test display name fallback when manufacturer/model not available."""
        device = AndroidDevice(device_id='emulator-5554', status='device')
        assert device.display_name == 'emulator-5554'


class TestDeviceDetection:
    """Test DeviceDetection class."""

    @patch('mobile_crawler.infrastructure.device_detection.subprocess.run')
    def test_init_adb_available(self, mock_run):
        """Test initialization when ADB is available."""
        mock_run.return_value = CompletedProcess(
            args=['adb', 'version'],
            returncode=0,
            stdout='Android Debug Bridge version 1.0.41',
            stderr=''
        )

        detector = DeviceDetection()
        assert detector.adb_path == 'adb'
        mock_run.assert_called_once_with(
            ['adb', 'version'],
            capture_output=True,
            text=True,
            timeout=10
        )

    @patch('mobile_crawler.infrastructure.device_detection.subprocess.run')
    def test_init_adb_not_found(self, mock_run):
        """Test initialization when ADB is not found."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(ADBNotFoundError, match="ADB executable not found"):
            DeviceDetection()

    @patch('mobile_crawler.infrastructure.device_detection.subprocess.run')
    def test_init_adb_command_fails(self, mock_run):
        """Test initialization when ADB command fails."""
        mock_run.return_value = CompletedProcess(
            args=['adb', 'version'],
            returncode=1,
            stdout='',
            stderr='error'
        )

        with pytest.raises(ADBNotFoundError, match="ADB command failed"):
            DeviceDetection()

    @patch('mobile_crawler.infrastructure.device_detection.subprocess.run')
    def test_get_connected_devices(self, mock_run):
        """Test getting connected devices."""
        # Mock ADB commands
        version_output = CompletedProcess(
            args=['adb', 'version'],
            returncode=0,
            stdout='Android Debug Bridge version 1.0.41',
            stderr=''
        )
        devices_output = CompletedProcess(
            args=['adb', 'devices', '-l'],
            returncode=0,
            stdout="""List of devices attached
emulator-5554	device model:Pixel_4 device:flame transport_id:1
HT1A123456	offline
emulator-5556	device

""",
            stderr=''
        )
        empty_output = CompletedProcess(
            args=['adb', '-s', 'emulator-5554', 'shell', 'getprop', 'ro.product.manufacturer'],
            returncode=0,
            stdout='\n',
            stderr=''
        )
        
        mock_run.side_effect = [
            version_output,  # version check in __init__
            devices_output,  # devices command
            empty_output,    # manufacturer
            empty_output,    # model  
            empty_output,    # android version
            empty_output,    # api level
        ]

        detector = DeviceDetection()
        devices = detector.get_connected_devices()

        assert len(devices) == 3

        # Check first device
        device1 = devices[0]
        assert device1.device_id == 'emulator-5554'
        assert device1.status == 'device'
        assert device1.model == 'Pixel_4'

        # Check second device
        device2 = devices[1]
        assert device2.device_id == 'HT1A123456'
        assert device2.status == 'offline'

        # Check third device
        device3 = devices[2]
        assert device3.device_id == 'emulator-5556'
        assert device3.status == 'device'

    @patch('mobile_crawler.infrastructure.device_detection.subprocess.run')
    def test_get_connected_devices_empty(self, mock_run):
        """Test getting connected devices when none are connected."""
        devices_output = """List of devices attached

"""
        mock_run.return_value = CompletedProcess(
            args=['adb', 'devices', '-l'],
            returncode=0,
            stdout=devices_output,
            stderr=''
        )

        detector = DeviceDetection()
        devices = detector.get_connected_devices()

        assert len(devices) == 0

    @patch('mobile_crawler.infrastructure.device_detection.subprocess.run')
    def test_get_connected_devices_with_details(self, mock_run):
        """Test getting connected devices with detailed information."""
        # Mock devices command
        devices_output = """List of devices attached
emulator-5554	device model:Pixel_4 device:flame transport_id:1

"""
        mock_run.side_effect = [
            # version check in __init__
            CompletedProcess(
                args=['adb', 'version'],
                returncode=0,
                stdout='Android Debug Bridge version 1.0.41',
                stderr=''
            ),
            # devices -l command
            CompletedProcess(
                args=['adb', 'devices', '-l'],
                returncode=0,
                stdout=devices_output,
                stderr=''
            ),
            # getprop manufacturer
            CompletedProcess(
                args=['adb', '-s', 'emulator-5554', 'shell', 'getprop', 'ro.product.manufacturer'],
                returncode=0,
                stdout='Google\n',
                stderr=''
            ),
            # getprop model
            CompletedProcess(
                args=['adb', '-s', 'emulator-5554', 'shell', 'getprop', 'ro.product.model'],
                returncode=0,
                stdout='Pixel 4\n',
                stderr=''
            ),
            # getprop android version
            CompletedProcess(
                args=['adb', '-s', 'emulator-5554', 'shell', 'getprop', 'ro.build.version.release'],
                returncode=0,
                stdout='12\n',
                stderr=''
            ),
            # getprop api level
            CompletedProcess(
                args=['adb', '-s', 'emulator-5554', 'shell', 'getprop', 'ro.build.version.sdk'],
                returncode=0,
                stdout='31\n',
                stderr=''
            )
        ]

        detector = DeviceDetection()
        devices = detector.get_connected_devices()

        assert len(devices) == 1
        device = devices[0]
        assert device.device_id == 'emulator-5554'
        assert device.status == 'device'
        assert device.manufacturer == 'Google'
        assert device.model == 'Pixel 4'
        assert device.android_version == '12'
        assert device.api_level == 31

    @patch('mobile_crawler.infrastructure.device_detection.subprocess.run')
    def test_get_available_devices(self, mock_run):
        """Test getting only available devices."""
        devices_output = """List of devices attached
emulator-5554	device
HT1A123456	offline
emulator-5556	device

"""
        mock_run.return_value = CompletedProcess(
            args=['adb', 'devices', '-l'],
            returncode=0,
            stdout=devices_output,
            stderr=''
        )

        detector = DeviceDetection()
        devices = detector.get_available_devices()

        assert len(devices) == 2
        assert all(d.is_available for d in devices)
        assert devices[0].device_id == 'emulator-5554'
        assert devices[1].device_id == 'emulator-5556'

    @patch('mobile_crawler.infrastructure.device_detection.subprocess.run')
    def test_find_device_by_id(self, mock_run):
        """Test finding device by ID."""
        devices_output = """List of devices attached
emulator-5554	device
emulator-5556	device

"""
        mock_run.return_value = CompletedProcess(
            args=['adb', 'devices', '-l'],
            returncode=0,
            stdout=devices_output,
            stderr=''
        )

        detector = DeviceDetection()
        device = detector.find_device_by_id('emulator-5554')

        assert device is not None
        assert device.device_id == 'emulator-5554'
        assert device.status == 'device'

    @patch('mobile_crawler.infrastructure.device_detection.subprocess.run')
    def test_find_device_by_id_not_found(self, mock_run):
        """Test finding device by ID when not found."""
        devices_output = """List of devices attached
emulator-5554	device

"""
        mock_run.return_value = CompletedProcess(
            args=['adb', 'devices', '-l'],
            returncode=0,
            stdout=devices_output,
            stderr=''
        )

        detector = DeviceDetection()
        device = detector.find_device_by_id('nonexistent')

        assert device is None

    @patch('mobile_crawler.infrastructure.device_detection.subprocess.run')
    @patch('mobile_crawler.infrastructure.device_detection.time.sleep')
    def test_wait_for_device_specific(self, mock_sleep, mock_run):
        """Test waiting for a specific device."""
        # First call returns no devices
        # Second call returns the device
        devices_output1 = """List of devices attached

"""
        devices_output2 = """List of devices attached
emulator-5554	device

"""
        mock_run.side_effect = [
            CompletedProcess(
                    args=['adb', 'version'],
                    returncode=0,
                    stdout='Android Debug Bridge version 1.0.41',
                    stderr=''
                ),  # version check
                CompletedProcess(
                    args=['adb', 'devices', '-l'],
                    returncode=0,
                    stdout=devices_output1,
                    stderr=''
                ),  # first devices call - no devices
                CompletedProcess(
                    args=['adb', 'devices', '-l'],
                    returncode=0,
                    stdout=devices_output2,
                    stderr=''
                )   # second devices call - with device
            ]
        detector = DeviceDetection()
        device = detector.wait_for_device('emulator-5554', timeout=10)

        assert device.device_id == 'emulator-5554'
        assert device.is_available
        mock_sleep.assert_called_once_with(1)

    @patch('mobile_crawler.infrastructure.device_detection.subprocess.run')
    @patch('mobile_crawler.infrastructure.device_detection.time.sleep')
    def test_wait_for_device_timeout(self, mock_sleep, mock_run):
        """Test waiting for device times out."""
        devices_output = """List of devices attached

"""
        mock_run.return_value = CompletedProcess(
            args=['adb', 'devices', '-l'],
            returncode=0,
            stdout=devices_output,
            stderr=''
        )

        detector = DeviceDetection()

        with pytest.raises(DeviceDetectionError, match="Device emulator-5554 not found"):
            detector.wait_for_device('emulator-5554', timeout=2)

        # Should have called sleep multiple times
        assert mock_sleep.call_count > 1

    @patch('mobile_crawler.infrastructure.device_detection.subprocess.run')
    def test_adb_command_timeout(self, mock_run):
        """Test ADB command timeout."""
        from subprocess import TimeoutExpired
        
        # Mock the version check in __init__
        mock_run.side_effect = [
            CompletedProcess(args=['adb', 'version'], returncode=0, stdout='', stderr=''),  # version check
            TimeoutExpired(['adb', 'devices'], 30)  # actual command
        ]

        detector = DeviceDetection()

        with pytest.raises(DeviceDetectionError, match="ADB command timed out"):
            detector.get_connected_devices()

    @patch('mobile_crawler.infrastructure.device_detection.subprocess.run')
    def test_adb_command_error(self, mock_run):
        """Test ADB command error."""
        # Mock the version check in __init__
        mock_run.side_effect = [
            CompletedProcess(args=['adb', 'version'], returncode=0, stdout='', stderr=''),  # version check
            Exception("Network error")  # actual command
        ]

        detector = DeviceDetection()

        with pytest.raises(DeviceDetectionError, match="ADB command failed"):
            detector.get_connected_devices()