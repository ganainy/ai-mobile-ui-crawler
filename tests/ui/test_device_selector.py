"""Tests for DeviceSelector widget."""

import pytest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication, QWidget

from mobile_crawler.ui.widgets.device_selector import DeviceSelector
from mobile_crawler.infrastructure.device_detection import (
    DeviceDetection,
    AndroidDevice,
    DeviceDetectionError
)


@pytest.fixture
def qapp():
    """Create QApplication instance for tests."""
    if not QApplication.instance():
        app = QApplication([])
        yield app
        app.quit()
    else:
        yield QApplication.instance()


@pytest.fixture
def mock_config_store():
    """Create mock UserConfigStore for tests."""
    mock_store = Mock()
    mock_store.get_setting.return_value = None
    mock_store.set_setting.return_value = None
    mock_store.delete_setting.return_value = None
    return mock_store


@pytest.fixture
def device_selector(qapp, mock_config_store):
    """Create DeviceSelector instance for tests."""
    mock_detection = Mock(spec=DeviceDetection)
    parent_widget = QWidget()
    selector = DeviceSelector(
        device_detection=mock_detection,
        config_store=mock_config_store,
        parent=parent_widget
    )
    yield selector
    # Cleanup
    selector.deleteLater()
    parent_widget.deleteLater()


class TestDeviceSelectorInit:
    """Tests for DeviceSelector initialization."""

    def test_initialization(self, qapp, device_selector):
        """Test that DeviceSelector initializes correctly."""
        assert device_selector.device_detection is not None
        assert device_selector.current_device() is None


class TestRefreshDevices:
    """Tests for device refresh functionality."""

    def test_refresh_updates_device_list(self, qapp, device_selector):
        """Test that refresh updates device list."""
        mock_devices = [
            AndroidDevice(
                device_id="emulator-5554",
                status="device",
                model="Pixel 5",
                manufacturer="Google",
                android_version="13",
                api_level=33
            ),
            AndroidDevice(
                device_id="emulator-5556",
                status="device",
                model="Pixel 6",
                manufacturer="Google",
                android_version="14",
                api_level=34
            )
        ]

        device_selector.device_detection.get_available_devices = Mock(return_value=mock_devices)
        device_selector._refresh_devices()

        # Check that devices were added to combo box
        assert device_selector.device_combo.count() == 2
        assert device_selector.device_combo.itemText(0) == "Google Pixel 5 (emulator-5554)"
        assert device_selector.device_combo.itemText(1) == "Google Pixel 6 (emulator-5556)"

    def test_refresh_with_no_devices(self, qapp, device_selector):
        """Test refresh with no devices available."""
        device_selector.device_detection.get_available_devices = Mock(return_value=[])

        device_selector._refresh_devices()

        assert device_selector.device_combo.count() == 1
        assert device_selector.device_combo.itemText(0) == "No devices available"
        assert "No devices available" in device_selector.status_label.text()

    def test_refresh_with_error(self, qapp, device_selector):
        """Test refresh with device detection error."""
        device_selector.device_detection.get_available_devices = Mock(
            side_effect=DeviceDetectionError("ADB not found")
        )

        device_selector._refresh_devices()

        assert "Error" in device_selector.status_label.text()
        assert "red" in device_selector.status_label.styleSheet()


class TestDeviceSelection:
    """Tests for device selection functionality."""

    def test_device_selection_emits_signal(self, qapp, device_selector):
        """Test that selecting a device emits signal."""
        mock_devices = [
            AndroidDevice(
                device_id="emulator-5554",
                status="device",
                model="Pixel 5",
                manufacturer="Google",
                android_version="13",
                api_level=33
            )
        ]

        device_selector.device_detection.get_available_devices = Mock(return_value=mock_devices)

        # Track signal emissions
        signal_emitted = []

        def capture_signal(device):
            signal_emitted.append(device)

        device_selector.device_selected.connect(capture_signal)

        device_selector._refresh_devices()

        # Select first device
        device_selector.device_combo.setCurrentIndex(0)

        # Check signal was emitted
        assert len(signal_emitted) == 1
        assert signal_emitted[0].device_id == "emulator-5554"

    def test_clear_selection(self, qapp, device_selector):
        """Test that clear_selection works."""
        mock_devices = [
            AndroidDevice(
                device_id="emulator-5554",
                status="device",
                model="Pixel 5",
                manufacturer="Google",
                android_version="13",
                api_level=33
            )
        ]

        device_selector.device_detection.get_available_devices = Mock(return_value=mock_devices)
        device_selector._refresh_devices()

        # Select first device
        device_selector.device_combo.setCurrentIndex(0)
        assert device_selector.current_device() is not None

        # Clear selection
        device_selector.clear_selection()

        # Verify selection is cleared
        assert device_selector.current_device() is None
        assert device_selector.device_combo.currentIndex() == 0

    def test_set_device(self, qapp, device_selector):
        """Test that set_device works."""
        mock_devices = [
            AndroidDevice(
                device_id="emulator-5554",
                status="device",
                model="Pixel 5",
                manufacturer="Google",
                android_version="13",
                api_level=33
            ),
            AndroidDevice(
                device_id="emulator-5556",
                status="device",
                model="Pixel 6",
                manufacturer="Google",
                android_version="14",
                api_level=34
            )
        ]

        device_selector.device_detection.get_available_devices = Mock(return_value=mock_devices)
        device_selector._refresh_devices()

        # Set second device
        target_device = mock_devices[1]
        device_selector.set_device(target_device)

        # Verify device was selected
        assert device_selector.current_device().device_id == "emulator-5556"
        assert "Google Pixel 6 (emulator-5556)" in device_selector.status_label.text()

    def test_set_device_not_found(self, qapp, device_selector):
        """Test set_device when device not in list."""
        mock_devices = [
            AndroidDevice(
                device_id="emulator-5554",
                status="device",
                model="Pixel 5",
                manufacturer="Google",
                android_version="13",
                api_level=33
            )
        ]

        device_selector.device_detection.get_available_devices = Mock(return_value=mock_devices)
        device_selector._refresh_devices()

        # Try to set non-existent device
        target_device = AndroidDevice(
                device_id="emulator-5557",
                status="device",
                model="Pixel 7",
                manufacturer="Google",
                android_version="14",
                api_level=35
        )

        device_selector.set_device(target_device)

        # Verify status shows device not found
        assert "not found" in device_selector.status_label.text().lower()
        assert "orange" in device_selector.status_label.styleSheet()


class TestCurrentDevice:
    """Tests for current_device method."""

    def test_current_device_returns_none_initially(self, qapp, device_selector):
        """Test that current_device returns None initially."""
        assert device_selector.current_device() is None

    def test_current_device_returns_selected_device(self, qapp, device_selector):
        """Test that current_device returns selected device."""
        mock_devices = [
            AndroidDevice(
                device_id="emulator-5554",
                status="device",
                model="Pixel 5",
                manufacturer="Google",
                android_version="13",
                api_level=33
            )
        ]

        device_selector.device_detection.get_available_devices = Mock(return_value=mock_devices)
        device_selector._refresh_devices()

        # Select first device
        device_selector.device_combo.setCurrentIndex(0)

        # Verify current_device returns selected device
        current = device_selector.current_device()
        assert current is not None
        assert current.device_id == "emulator-5554"


class TestUIComponents:
    """Tests for UI components."""

    def test_refresh_button_exists(self, qapp, device_selector):
        """Test that refresh button exists."""
        assert device_selector.refresh_button is not None
        assert device_selector.refresh_button.text() == "Refresh"

    def test_device_combo_exists(self, qapp, device_selector):
        """Test that device combo box exists."""
        assert device_selector.device_combo is not None

    def test_status_label_exists(self, qapp, device_selector):
        """Test that status label exists."""
        assert device_selector.status_label is not None

    def test_status_label_updates_on_refresh(self, qapp, device_selector):
        """Test that status label updates during refresh."""
        mock_devices = [
            AndroidDevice(
                device_id="emulator-5554",
                status="device",
                model="Pixel 5",
                manufacturer="Google",
                android_version="13",
                api_level=33
            )
        ]

        device_selector.device_detection.get_available_devices = Mock(return_value=mock_devices)
        device_selector._refresh_devices()

        # After refresh, status should show selected device
        assert "Selected:" in device_selector.status_label.text()
        assert "green" in device_selector.status_label.styleSheet()

    def test_refresh_button_connected(self, qapp, device_selector):
        """Test that refresh button is connected to refresh method."""
        mock_devices = [
            AndroidDevice(
                device_id="emulator-5554",
                status="device",
                model="Pixel 5",
                manufacturer="Google",
                android_version="13",
                api_level=33
            )
        ]

        device_selector.device_detection.get_available_devices = Mock(return_value=mock_devices)

        # Mock the refresh method to track calls
        original_refresh = device_selector._refresh_devices
        call_count = [0]

        def mock_refresh():
            call_count[0] += 1
            return original_refresh()

        device_selector._refresh_devices = mock_refresh
        device_selector.refresh_button.click()

        # Verify refresh was called
        assert call_count[0] == 1


class TestDeviceDisplay:
    """Tests for device display functionality."""

    def test_device_display_name(self, qapp, device_selector):
        """Test that device display name is formatted correctly."""
        mock_devices = [
            AndroidDevice(
                device_id="emulator-5554",
                status="device",
                model="Pixel 5",
                manufacturer="Google",
                android_version="13",
                api_level=33
            )
        ]

        device_selector.device_detection.get_available_devices = Mock(return_value=mock_devices)
        device_selector._refresh_devices()

        # Check display name in combo box
        display_text = device_selector.device_combo.itemText(0)
        assert "Google" in display_text
        assert "Pixel 5" in display_text
        assert "emulator-5554" in display_text

    def test_device_display_name_with_no_manufacturer(self, qapp, device_selector):
        """Test device display name when manufacturer is None."""
        mock_devices = [
            AndroidDevice(
                device_id="emulator-5554",
                status="device",
                model=None,
                manufacturer=None,
                android_version=None,
                api_level=None
            )
        ]

        device_selector.device_detection.get_available_devices = Mock(return_value=mock_devices)
        device_selector._refresh_devices()

        # Check display name falls back to device_id
        display_text = device_selector.device_combo.itemText(0)
        assert "emulator-5554" in display_text
