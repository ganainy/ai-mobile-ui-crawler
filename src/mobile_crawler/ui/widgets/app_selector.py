"""App selection widget for mobile-crawler GUI."""

import re
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QComboBox
)
from PySide6.QtCore import Signal, QObject

from mobile_crawler.infrastructure.appium_driver import AppiumDriver


class AppSelector(QObject):
    """Widget for selecting Android app package.

    Provides a text input for package name with validation.
    Optionally lists installed apps from device.
    Emits a signal when an app is selected.
    """

    # Signal emitted when an app is selected
    app_selected = Signal(str)  # type: ignore

    def __init__(self, appium_driver: AppiumDriver, parent=None):
        """Initialize app selector widget.

        Args:
            appium_driver: AppiumDriver instance for listing installed apps
            parent: Parent widget
        """
        super().__init__(parent)
        self.appium_driver = appium_driver
        self._current_package: str = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()

        # Label
        label = QLabel("App Package:")
        layout.addWidget(label)

        # App input row
        input_layout = QHBoxLayout()

        # Package text input
        self.package_input = QLineEdit()
        self.package_input.setPlaceholderText("e.g., com.example.app")
        self.package_input.setMinimumWidth(300)
        self.package_input.textChanged.connect(self._on_text_changed)
        input_layout.addWidget(self.package_input)

        # Refresh button for listing installed apps
        self.refresh_button = QPushButton("List Apps")
        self.refresh_button.clicked.connect(self._list_installed_apps)
        input_layout.addWidget(self.refresh_button)

        layout.addLayout(input_layout)

        # Installed apps dropdown (hidden by default)
        self.apps_combo = QComboBox()
        self.apps_combo.setVisible(False)
        self.apps_combo.currentTextChanged.connect(self._on_combo_changed)
        layout.addWidget(self.apps_combo)

        # Status label
        self.status_label = QLabel("Enter package name")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def _on_text_changed(self, text: str):
        """Handle text input change.

        Args:
            text: New text value
        """
        if not text:
            self.status_label.setText("Enter package name")
            self.status_label.setStyleSheet("color: gray; font-style: italic;")
            self._current_package = None
            return

        if self._validate_package(text):
            self.status_label.setText(f"Package: {text}")
            self.status_label.setStyleSheet("color: green; font-style: italic;")
            self._current_package = text
            self.app_selected.emit(text)
        else:
            self.status_label.setText("Invalid package format")
            self.status_label.setStyleSheet("color: red; font-style: italic;")
            self._current_package = None

    def _on_combo_changed(self, text: str):
        """Handle combo box selection change.

        Args:
            text: Selected package name
        """
        if text and self._validate_package(text):
            self.package_input.setText(text)
            self._current_package = text
            self.app_selected.emit(text)

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
        pattern = r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$'
        return bool(re.match(pattern, package))

    def _list_installed_apps(self):
        """List installed apps from device."""
        self.status_label.setText("Loading apps...")
        self.status_label.setStyleSheet("color: orange; font-style: italic;")

        try:
            if not self.appium_driver.session:
                self.status_label.setText("No device connected")
                self.status_label.setStyleSheet("color: red; font-style: italic;")
                return

            # Get list of installed packages
            packages = self.appium_driver.driver.execute_script(
                "mobile: shell",
                {"command": "pm", "args": ["list", "packages", "-3"]}
            )

            # Parse output
            package_list = []
            if packages:
                for line in packages.split('\n'):
                    line = line.strip()
                    if line.startswith('package:'):
                        package = line.replace('package:', '').strip()
                        package_list.append(package)

            if package_list:
                # Sort packages
                package_list.sort()

                # Populate combo box
                self.apps_combo.clear()
                self.apps_combo.addItem("Select an app...", None)
                for package in package_list:
                    self.apps_combo.addItem(package, package)

                # Show combo box
                self.apps_combo.setVisible(True)

                self.status_label.setText(f"Found {len(package_list)} apps")
                self.status_label.setStyleSheet("color: green; font-style: italic;")
            else:
                self.status_label.setText("No apps found")
                self.status_label.setStyleSheet("color: red; font-style: italic;")
                self.apps_combo.setVisible(False)

        except Exception as e:
            self.status_label.setText(f"Error: {e}")
            self.status_label.setStyleSheet("color: red; font-style: italic;")
            QMessageBox.critical(self.parent(), "App List Error", str(e))

    def current_package(self) -> str:
        """Get the currently selected package.

        Returns:
            Currently selected package or None
        """
        return self._current_package

    def set_package(self, package: str):
        """Set a specific package.

        Args:
            package: Package name to set
        """
        if self._validate_package(package):
            self.package_input.setText(package)
        else:
            self.status_label.setText(f"Invalid package: {package}")
            self.status_label.setStyleSheet("color: red; font-style: italic;")

    def clear(self):
        """Clear the current selection."""
        self.package_input.clear()
        self.apps_combo.setVisible(False)
        self.status_label.setText("Enter package name")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        self._current_package = None

    def get_widget(self) -> QWidget:
        """Get the underlying QWidget for embedding.

        Returns:
            The QWidget containing the app selector UI
        """
        return self.parent() if hasattr(self, 'parent') and isinstance(self.parent(), QWidget) else None
