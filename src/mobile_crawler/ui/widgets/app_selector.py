"""App selection widget for mobile-crawler GUI."""

import logging
import re
import subprocess
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from mobile_crawler.infrastructure.app_metadata_resolver import AppMetadata, AppMetadataResolver
from mobile_crawler.ui.async_utils import AsyncOperation

if TYPE_CHECKING:
    from mobile_crawler.infrastructure.user_config_store import UserConfigStore

logger = logging.getLogger(__name__)


class AppEnrichmentWorker(QThread):
    """Resolves App Metadata (name + icon) for a list of packages in the background.

    Emits one `item_resolved` per package as it's resolved, so the caller can
    update the UI incrementally instead of waiting for the whole batch.
    """

    item_resolved = Signal(str, object)  # package, AppMetadata

    def __init__(self, resolver: AppMetadataResolver, device_id: str, packages: list[str], parent=None):
        super().__init__(parent)
        self._resolver = resolver
        self._device_id = device_id
        self._packages = packages

    def run(self):
        for package in self._packages:
            try:
                metadata = self._resolver.resolve(self._device_id, package)
            except Exception as e:
                logger.debug(f"Failed to resolve app metadata for {package}: {e}")
                metadata = AppMetadata(package=package, label=package, icon_path=None, source="unresolved")
            self.item_resolved.emit(package, metadata)


class AppSelector(QWidget):
    """Widget for selecting an installed Android app.

    Lists third-party apps installed on the connected device and lets the
    user pick one from a dropdown. Each entry is enriched in the background
    with its real app name and icon (see AppMetadataResolver); the
    underlying selected value is always the package name, never the
    display label. Persists the last selected package across sessions.

    Args:
        config_store: UserConfigStore instance for persisting app package
        parent: Parent widget
    """

    # Signal emitted when an app is selected
    app_selected = Signal(str)  # type: ignore

    def __init__(self, config_store: "UserConfigStore", parent=None):
        """Initialize app selector widget.

        Args:
            config_store: UserConfigStore instance for persisting app package
            parent: Parent widget
        """
        super().__init__(parent)
        self.device_id: str | None = None
        self._config_store = config_store
        self._current_package: str | None = None
        self._pending_restore_package: str | None = None
        self._resolver = AppMetadataResolver()
        self._enrichment_worker: AppEnrichmentWorker | None = None
        self._enrichment_generation = 0
        self._setup_ui()
        self._load_selection()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Label
        label = QLabel("App:")
        layout.addWidget(label)

        # App picker row
        input_layout = QHBoxLayout()

        # Installed apps dropdown (only way to select an app - must be installed on the device)
        self.apps_combo = QComboBox()
        self.apps_combo.setMinimumWidth(300)
        self.apps_combo.currentIndexChanged.connect(self._on_combo_index_changed)
        input_layout.addWidget(self.apps_combo)

        # Refresh button for re-listing installed apps
        self.refresh_button = QPushButton("Refresh Apps")
        self.refresh_button.clicked.connect(self._list_installed_apps)
        input_layout.addWidget(self.refresh_button)

        layout.addLayout(input_layout)

        # Status label
        self.status_label = QLabel("No device connected")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def _load_selection(self):
        """Load previously saved app package from config store.

        There's no text field to restore into anymore; the saved package is
        auto-selected in the dropdown once the app list has loaded (see
        `_on_list_success`).
        """
        self._pending_restore_package = self._config_store.get_setting("last_app_package", default=None)

    def set_device_id(self, device_id: str | None) -> None:
        """Update the active device id used for ADB calls and refresh the app list."""
        self.device_id = device_id
        if device_id:
            self._list_installed_apps()
        else:
            self.apps_combo.clear()
            self.status_label.setText("No device connected")
            self.status_label.setStyleSheet("color: gray; font-style: italic;")

    def _list_installed_apps(self):
        """List installed apps from device."""
        self.status_label.setText("Loading apps...")
        self.status_label.setStyleSheet("color: orange; font-style: italic;")

        if not self.device_id:
            # Show a more helpful message about needing a device connection
            QMessageBox.warning(
                self,
                "No Device Session",
                "No active device session.\n\n"
                "Please select a device from the Device Selector first.\n"
                "The device must be connected and authorized.",
            )
            self.status_label.setText("No device connected")
            self.status_label.setStyleSheet("color: red; font-style: italic;")
            return

        self.refresh_button.setEnabled(False)

        # Create async operation
        self._list_thread = AsyncOperation(self._fetch_packages)
        self._list_thread.result_ready.connect(self._on_list_success)
        self._list_thread.error_occurred.connect(self._on_list_error)
        self._list_thread.finished_signal.connect(lambda: self.refresh_button.setEnabled(True))
        self._list_thread.start()

    def _fetch_packages(self) -> str:
        """Fetch installed packages from device via ADB.

        Returns:
            Output of 'pm list packages -3'
        """
        if not self.device_id:
            raise RuntimeError("No device selected")

        result = subprocess.run(
            ["adb", "-s", self.device_id, "shell", "pm", "list", "packages", "-3"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            error_output = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(error_output or "ADB command failed")

        return result.stdout

    def _on_list_success(self, packages: str):
        """Handle successful package list retrieval.

        Args:
            packages: Raw string output from package manager
        """
        # Parse output
        package_list = []
        if packages:
            for line in packages.split("\n"):
                line = line.strip()
                if line.startswith("package:"):
                    package = line.replace("package:", "").strip()
                    if self._validate_package(package):
                        package_list.append(package)

        if not package_list:
            self.status_label.setText("No apps found")
            self.status_label.setStyleSheet("color: red; font-style: italic;")
            return

        # Sort packages
        package_list.sort()

        # Populate combo box with raw package names; icons/labels arrive via enrichment
        self.apps_combo.blockSignals(True)
        self.apps_combo.clear()
        self.apps_combo.addItem("Select an app...", None)
        for package in package_list:
            self.apps_combo.addItem(package, package)
        self.apps_combo.blockSignals(False)

        self.status_label.setText(f"Found {len(package_list)} apps")
        self.status_label.setStyleSheet("color: green; font-style: italic;")

        restore_package = self._pending_restore_package
        self._pending_restore_package = None
        if restore_package:
            index = self.apps_combo.findData(restore_package)
            if index >= 0:
                self.apps_combo.setCurrentIndex(index)
            else:
                self.status_label.setText("Previously selected app not found on this device")
                self.status_label.setStyleSheet("color: gray; font-style: italic;")

        self._start_enrichment(package_list)

    def _on_list_error(self, error: str):
        """Handle package list retrieval error.

        Args:
            error: Error message
        """
        error_msg = str(error).lower()
        if "adb" in error_msg or "device" in error_msg or "not found" in error_msg:
            QMessageBox.critical(
                self.parent(),
                "ADB Not Available",
                "Cannot access the device via ADB. Please:\n\n"
                "1. Ensure the device is connected and authorized\n"
                "2. Verify USB debugging is enabled\n"
                "3. Confirm 'adb' is available in your PATH\n\n"
                f"Error: {error}",
            )
        else:
            QMessageBox.critical(self.parent(), "App List Error", str(error))

        self.status_label.setText(f"Error: {error}")
        self.status_label.setStyleSheet("color: red; font-style: italic;")

    def _start_enrichment(self, packages: list[str]) -> None:
        """Resolve real app name + icon for each listed package, in the background."""
        # Bump the generation so results from a previous (now-stale) list refresh
        # or device switch are ignored if they arrive after this one starts.
        self._enrichment_generation += 1
        generation = self._enrichment_generation

        worker = AppEnrichmentWorker(self._resolver, self.device_id, packages, parent=self)
        worker.item_resolved.connect(
            lambda package, metadata, gen=generation: self._on_item_resolved(gen, package, metadata)
        )
        self._enrichment_worker = worker
        worker.start()

    def _on_item_resolved(self, generation: int, package: str, metadata: AppMetadata) -> None:
        """Update a combo item's display text/icon once its metadata resolves."""
        if generation != self._enrichment_generation:
            return

        index = self.apps_combo.findData(package)
        if index < 0:
            return

        self.apps_combo.setItemText(index, metadata.label)
        self.apps_combo.setItemData(index, package, Qt.ItemDataRole.ToolTipRole)
        if metadata.icon_path:
            icon = QIcon(str(metadata.icon_path))
            if not icon.isNull():
                self.apps_combo.setItemIcon(index, icon)

    def _on_combo_index_changed(self, index: int):
        """Handle combo box selection change.

        Args:
            index: Selected item's index
        """
        if index < 0:
            return

        package = self.apps_combo.itemData(index)
        if not package:
            self._current_package = None
            return

        self._current_package = package
        self.status_label.setText(f"Package: {package}")
        self.status_label.setStyleSheet("color: green; font-style: italic;")
        self._config_store.set_setting("last_app_package", package, "string")
        self.app_selected.emit(package)

    def _validate_package(self, package: str) -> bool:
        """Validate Android package name format.

        Args:
            package: Package name to validate

        Returns:
            True if valid, False otherwise
        """
        # Android package name regex:
        # - Must start with a letter
        # - Can contain letters, digits, and underscores
        # - Must have at least one dot
        # - Each segment must start with a lowercase letter
        pattern = r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"
        return bool(re.match(pattern, package))

    def current_package(self) -> str | None:
        """Get the currently selected package.

        Returns:
            Currently selected package or None
        """
        return self._current_package

    def clear(self):
        """Clear the current selection."""
        self.apps_combo.clear()
        self.status_label.setText("No device connected" if not self.device_id else "No apps found")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        self._current_package = None
