"""Device selection widget for mobile-crawler GUI."""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QMessageBox
)
from PySide6.QtCore import Signal, QObject

from mobile_crawler.infrastructure.device_detection import (
    DeviceDetection,
    AndroidDevice,
    DeviceDetectionError
)

if TYPE_CHECKING:
    from mobile_crawler.infrastructure.user_config_store import UserConfigStore


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
        saved_device_id = self._config_store.get_setting("last_device_id", default=None)
        if saved_device_id:
            self._saved_device_id = saved_device_id
        else:
            self._saved_device_id = None

    def _refresh_devices(self):
        """Refresh the list of available devices."""
        self.status_label.setText("Refreshing devices...")
        self.status_label.setStyleSheet("color: orange; font-style: italic;")

        try:
            devices = self.device_detection.get_available_devices()
            self._update_device_list(devices)
        except DeviceDetectionError as e:
            self.status_label.setText(f"Error: {e}")
            self.status_label.setStyleSheet("color: red; font-style: italic;")
            QMessageBox.critical(self.parent(), "Device Detection Error", str(e))

    def _update_device_list(self, devices: list[AndroidDevice]):
        """Update the device dropdown with new list.

        Args:
            devices: List of AndroidDevice objects
        """
        # Save current selection
        current_device_id = self.device_combo.currentData()
        if current_device_id:
            current_device_id = current_device_id.device_id

        # Clear and repopulate
        self.device_combo.clear()

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
                "1. Ensure USB debugging is enabled on your device\n"
                "2. Connect your device via USB\n"
                "3. Accept the USB debugging authorization prompt\n"
                "4. Or start an Android emulator\n\n"
                "Then click 'Refresh' to try again."
            )
            return

        # Add devices to dropdown
        for device in devices:
            display_text = device.display_name
            self.device_combo.addItem(display_text, device)

        # Try to restore saved selection first
        if hasattr(self, '_saved_device_id') and self._saved_device_id:
            for i in range(self.device_combo.count()):
                device = self.device_combo.itemData(i)
                if device and device.device_id == self._saved_device_id:
                    self.device_combo.setCurrentIndex(i)
                    self._update_status_text(device)
                    self._saved_device_id = None  # Clear after use
                    return
            # Saved device not found - show message
            self.status_label.setText(f"Previously selected device not found: {self._saved_device_id}")
            self.status_label.setStyleSheet("color: orange; font-style: italic;")
            self._saved_device_id = None

        # Restore selection if possible
        if current_device_id:
            for i in range(self.device_combo.count()):
                device = self.device_combo.itemData(i)
                if device and device.device_id == current_device_id:
                    self.device_combo.setCurrentIndex(i)
                    self._update_status_text(device)
                    return

        # If no previous selection, select first device
        if self.device_combo.count() > 0:
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
            # Clear saved device ID when no device selected
            self._config_store.delete_setting("last_device_id")
