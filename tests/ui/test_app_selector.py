"""Tests for AppSelector widget."""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from mobile_crawler.ui.widgets.app_selector import AppSelector


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
def app_selector(qapp, mock_config_store):
    """Create AppSelector instance for tests."""
    parent_widget = QWidget()
    selector = AppSelector(
        config_store=mock_config_store,
        parent=parent_widget
    )
    yield selector
    # Cleanup
    selector.deleteLater()
    parent_widget.deleteLater()


class TestAppSelectorInit:
    """Tests for AppSelector initialization."""

    def test_initialization(self, qapp, app_selector):
        """Test that AppSelector initializes correctly."""
        assert app_selector.current_package() is None


class TestPackageValidation:
    """Tests for package name validation."""

    def test_valid_package_format(self, qapp, app_selector):
        """Test valid package name formats."""
        valid_packages = [
            "com.example.app",
            "com.google.android.gms",
            "org.example.test",
            "io.flutter.app",
            "com.company1.app2"
        ]

        for package in valid_packages:
            assert app_selector._validate_package(package) is True

    def test_invalid_package_format(self, qapp, app_selector):
        """Test invalid package name formats."""
        invalid_packages = [
            "com.example.",  # Ends with dot
            ".com.example",  # Starts with dot
            "Com.example.app",  # Uppercase letter
            "1com.example.app",  # Starts with digit
            "com..example.app",  # Double dot
            "com.example.app.",  # Ends with dot
            "",  # Empty string
            "com.example-app",  # Invalid character
            "com.example app",  # Space
        ]

        for package in invalid_packages:
            assert app_selector._validate_package(package) is False

    def test_package_with_underscore(self, qapp, app_selector):
        """Test package name with underscores."""
        assert app_selector._validate_package("com.example_test.app") is True
        assert app_selector._validate_package("com.example.app_test") is True


class TestPackageInput:
    """Tests for package input functionality."""

    def test_empty_input(self, qapp, app_selector):
        """Test empty input shows default status."""
        app_selector.package_input.setText("")
        assert app_selector.current_package() is None
        assert "Enter package name" in app_selector.status_label.text()

    def test_valid_package_input(self, qapp, app_selector):
        """Test valid package input updates status."""
        app_selector.package_input.setText("com.example.app")

        assert app_selector.current_package() == "com.example.app"
        assert "Package: com.example.app" in app_selector.status_label.text()
        assert "green" in app_selector.status_label.styleSheet()

    def test_invalid_package_input(self, qapp, app_selector):
        """Test invalid package input shows error."""
        app_selector.package_input.setText("Invalid.Package")

        assert app_selector.current_package() is None
        assert "Invalid package format" in app_selector.status_label.text()
        assert "red" in app_selector.status_label.styleSheet()


class TestAppSelectedSignal:
    """Tests for app_selected signal."""

    def test_signal_emitted_on_valid_package(self, qapp, app_selector):
        """Test that signal is emitted when valid package is entered."""
        signal_emitted = []

        def capture_signal(package):
            signal_emitted.append(package)

        app_selector.app_selected.connect(capture_signal)
        app_selector.package_input.setText("com.example.app")

        assert len(signal_emitted) == 1
        assert signal_emitted[0] == "com.example.app"

    def test_signal_not_emitted_on_invalid_package(self, qapp, app_selector):
        """Test that signal is not emitted for invalid package."""
        signal_emitted = []

        def capture_signal(package):
            signal_emitted.append(package)

        app_selector.app_selected.connect(capture_signal)
        app_selector.package_input.setText("invalid")

        assert len(signal_emitted) == 0


class TestListInstalledApps:
    """Tests for listing installed apps."""

    def test_list_apps_with_connected_device(self, qapp, app_selector):
        """Test listing apps with connected device."""
        app_selector.device_id = "emulator-5554"
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="package:com.example.app\npackage:com.test.app"
            )
            app_selector._list_installed_apps()

        # Verify combo box is shown and populated
        assert app_selector.apps_combo.isVisible() is True
        assert app_selector.apps_combo.count() == 3  # 2 apps + placeholder
        assert app_selector.apps_combo.itemText(1) == "com.example.app"
        assert app_selector.apps_combo.itemText(2) == "com.test.app"

    def test_list_apps_with_no_device(self, qapp, app_selector):
        """Test listing apps when no device is connected."""
        app_selector._list_installed_apps()

        assert "No device" in app_selector.status_label.text()
        assert app_selector.apps_combo.isVisible() is False

    def test_list_apps_with_error(self, qapp, app_selector):
        """Test listing apps when error occurs."""
        app_selector.device_id = "emulator-5554"
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = RuntimeError("ADB error")
            app_selector._list_installed_apps()

        assert "Error" in app_selector.status_label.text()
        assert app_selector.apps_combo.isVisible() is False

    def test_list_apps_empty_result(self, qapp, app_selector):
        """Test listing apps when no apps found."""
        app_selector.device_id = "emulator-5554"
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")
            app_selector._list_installed_apps()

        assert "No apps found" in app_selector.status_label.text()
        assert app_selector.apps_combo.isVisible() is False


class TestComboSelection:
    """Tests for combo box selection."""

    def test_combo_selection_updates_input(self, qapp, app_selector):
        """Test that selecting from combo box updates input."""
        app_selector.device_id = "emulator-5554"
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="package:com.example.app"
            )
            app_selector._list_installed_apps()

        # Select first app
        app_selector.apps_combo.setCurrentIndex(1)

        assert app_selector.package_input.text() == "com.example.app"
        assert app_selector.current_package() == "com.example.app"


class TestSetPackage:
    """Tests for set_package method."""

    def test_set_valid_package(self, qapp, app_selector):
        """Test setting a valid package."""
        app_selector.set_package("com.example.app")

        assert app_selector.package_input.text() == "com.example.app"
        assert app_selector.current_package() == "com.example.app"

    def test_set_invalid_package(self, qapp, app_selector):
        """Test setting an invalid package."""
        app_selector.set_package("invalid")

        assert "Invalid package" in app_selector.status_label.text()
        assert app_selector.current_package() is None


class TestClear:
    """Tests for clear method."""

    def test_clear_resets_state(self, qapp, app_selector):
        """Test that clear resets all state."""
        # First set a package
        app_selector.package_input.setText("com.example.app")

        # Then clear
        app_selector.clear()

        assert app_selector.package_input.text() == ""
        assert app_selector.current_package() is None
        assert "Enter package name" in app_selector.status_label.text()
        assert app_selector.apps_combo.isVisible() is False


class TestUIComponents:
    """Tests for UI components."""

    def test_package_input_exists(self, qapp, app_selector):
        """Test that package input exists."""
        assert app_selector.package_input is not None
        assert app_selector.package_input.placeholderText() == "e.g., com.example.app"

    def test_refresh_button_exists(self, qapp, app_selector):
        """Test that refresh button exists."""
        assert app_selector.refresh_button is not None
        assert app_selector.refresh_button.text() == "List Apps"

    def test_status_label_exists(self, qapp, app_selector):
        """Test that status label exists."""
        assert app_selector.status_label is not None

    def test_apps_combo_hidden_by_default(self, qapp, app_selector):
        """Test that apps combo box is hidden by default."""
        assert app_selector.apps_combo.isVisible() is False
