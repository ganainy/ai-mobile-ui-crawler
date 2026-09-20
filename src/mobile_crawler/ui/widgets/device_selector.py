"""Device selection widget for mobile-crawler GUI."""

from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from mobile_crawler.infrastructure.device_detection import AndroidDevice, DeviceDetection
from mobile_crawler.ui.async_utils import AsyncOperation

if TYPE_CHECKING:
    from mobile_crawler.infrastructure.user_config_store import UserConfigStore

AUTO_REFRESH_RETRIES = 3
AUTO_REFRESH_DELAY_MS = 1500


class DeviceSelector(QWidget):
    """Widget for selecting Android devices.

    Provides a dropdown with detected devices and a refresh button.
    Emits a signal when a device is selected.
    Persists last selected device across sessions.

    Args:
        device_detection: DeviceDetection instance for finding devices
        config_store: UserConfigStore instance for persisting device selection
        parent: Parent widget
    """

    # Signal emitted when a device is selected
    device_selected = Signal(object)  # type: ignore

    def __init__(self, device_detection: DeviceDetection, config_store: "UserConfigStore", parent=None):
        """Initialize device selector widget.

        Args:
            device_detection: DeviceDetection instance for finding devices
            config_store: UserConfigStore instance for persisting device selection
            parent: Parent widget
        """
        super().__init__(parent)
        self.device_detection = device_detection
        self._config_store = config_store
        self._current_device: AndroidDevice = None
        self._retries_left = 0
        self._auto_retrying = False
        self._setup_ui()
        self._load_selection()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Label
        label = QLabel("Select Device:")
        layout.addWidget(label)

        # Device dropdown row
        dropdown_layout = QHBoxLayout()

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(300)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        dropdown_layout.addWidget(self.device_combo)

        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._refresh_devices)
        dropdown_layout.addWidget(self.refresh_button)

        layout.addLayout(dropdown_layout)

        # Status label
        self.status_label = QLabel("No device selected")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def _load_selection(self):
        """Load previously saved device selection from config store."""
        self._saved_device_id = self._config_store.get_setting("last_device_id", default=None)

    def auto_refresh(self, retries: int = AUTO_REFRESH_RETRIES):
        """Refresh at startup, retrying quietly before any "no devices" error.

        The first adb query often comes back empty while the adb server is
        still starting; the warning dialog only appears once retries run out.
        """
        self._retries_left = retries
        self._auto_retrying = True
        self._refresh_devices()

    def _refresh_devices(self):
        """Refresh the list of available devices (manual: no silent retries)."""
        if not getattr(self, "_auto_retrying", False):
            self._retries_left = 0
        self._auto_retrying = False
        self.status_label.setText("Refreshing devices...")
        self.status_label.setStyleSheet("color: orange; font-style: italic;")
        self.refresh_button.setEnabled(False)

        # Create async operation
        self._detect_thread = AsyncOperation(self.device_detection.get_available_devices)
        self._detect_thread.result_ready.connect(self._on_detection_success)
        self._detect_thread.error_occurred.connect(self._on_detection_error)
        self._detect_thread.finished_signal.connect(lambda: self.refresh_button.setEnabled(True))
        self._detect_thread.start()

    def _on_detection_success(self, devices: list[AndroidDevice]):
        """Handle successful device detection.

        Args:
            devices: List of detected AndroidDevice objects
        """
        self._update_device_list(devices)

    def _on_detection_error(self, error: str):
        """Handle device detection error.

        Args:
            error: Error message
        """
        if self._retries_left > 0:
            self._schedule_retry()
            return
        self.status_label.setText(f"Error: {error}")
        self.status_label.setStyleSheet("color: red; font-style: italic;")
        QMessageBox.critical(self.parent(), "Device Detection Error", str(error))

    def _schedule_retry(self):
        """Queue another automatic refresh without showing an error."""
        self._retries_left -= 1
        self.status_label.setText("Looking for devices...")
        self.status_label.setStyleSheet("color: orange; font-style: italic;")
        QTimer.singleShot(AUTO_REFRESH_DELAY_MS, self._retry_refresh)

    def _retry_refresh(self):
        self._auto_retrying = True
        self._refresh_devices()

    def _update_device_list(self, devices: list[AndroidDevice]):
        """Update the device dropdown with new list.

        Args:
            devices: List of AndroidDevice objects
        """
        # Save current selection
        current_device_id = self.device_combo.currentData()
        if current_device_id:
            current_device_id = current_device_id.device_id

        # Read last-used before repopulating: clear()/addItem() fire
        # _on_device_changed, which would overwrite the stored value.
        saved_device_id = self._config_store.get_setting("last_device_id", default=None)

        self.device_combo.clear()

        if not devices and self._retries_left > 0:
            self._schedule_retry()
            return

        if not devices:
            self.device_combo.addItem("No devices available", None)
            self.status_label.setText("No devices available")
            self.status_label.setStyleSheet("color: red; font-style: italic;")
            self._current_device = None
            # Show error dialog for no devices found
            QMessageBox.warning(
                self.parent(),
                "No Devices Found",
                "No Android devices were detected. Please:\n\n"
                "1. Enable Developer options on your device\n\n"
                "USB:\n"
                "2. Enable USB debugging and connect via USB\n"
                "3. Accept the USB debugging authorization prompt\n\n"
                "Wireless debugging (Android 11+):\n"
                "2. Enable Wireless debugging (same Wi-Fi as this PC)\n"
                "3. Tap 'Pair device with pairing code', then run:\n"
                "     adb pair <ip>:<pairing-port>\n"
                "4. Run: adb connect <ip>:<port>\n"
                "     (the port shown on the Wireless debugging screen)\n"
                "5. Check that 'adb devices' lists it as 'device'\n\n"
                "Or start an Android emulator.\n\n"
                "Then click 'Refresh' to try again.",
            )
            return

        # Add devices to dropdown
        for device in devices:
            display_text = device.display_name
            self.device_combo.addItem(display_text, device)

        # Prefer the current selection, then the last-used device, else the first
        for wanted in (current_device_id, saved_device_id):
            if not wanted:
                continue
            for i in range(self.device_combo.count()):
                device = self.device_combo.itemData(i)
                if device and device.device_id == wanted:
                    self.device_combo.setCurrentIndex(i)
                    self._update_status_text(device)
                    return

        first_device = self.device_combo.itemData(0)
        if first_device:
            self.device_combo.setCurrentIndex(0)
            self._update_status_text(first_device)

    def _update_status_text(self, device: AndroidDevice):
        """Update status label with device information.

        Args:
            device: Selected AndroidDevice
        """
        self._current_device = device
        self.status_label.setText(f"Selected: {device.display_name}")
        self.status_label.setStyleSheet("color: green; font-style: italic;")

    def current_device(self) -> AndroidDevice:
        """Get the currently selected device.

        Returns:
            Currently selected AndroidDevice or None
        """
        return self._current_device

    def clear_selection(self):
        """Clear the current device selection."""
        self.device_combo.setCurrentIndex(0)
        self._current_device = None
        self.status_label.setText("Select a device")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")

    def set_device(self, device: AndroidDevice):
        """Set a specific device as selected.

        Args:
            device: AndroidDevice to select
        """
        for i in range(self.device_combo.count()):
            item_device = self.device_combo.itemData(i)
            if item_device and item_device.device_id == device.device_id:
                self.device_combo.setCurrentIndex(i)
                self._update_status_text(device)
                return

        # Device not found in list
        self.status_label.setText(f"Device not found: {device.device_id}")
        self.status_label.setStyleSheet("color: orange; font-style: italic;")

    def _on_device_changed(self, index: int):
        """Handle device selection change.

        Args:
            index: Index of selected item in dropdown
        """
        device = self.device_combo.itemData(index)
        if device:
            self._update_status_text(device)
            # Save device selection to config store
            self._config_store.set_setting("last_device_id", device.device_id, "string")
            self.device_selected.emit(device)
        else:
            self._current_device = None
            self.status_label.setText("Select a device")
            self.status_label.setStyleSheet("color: gray; font-style: italic;")
            # Keep last_device_id: the combo is emptied on every refresh and
            # the last-used device is needed to pick among several.
