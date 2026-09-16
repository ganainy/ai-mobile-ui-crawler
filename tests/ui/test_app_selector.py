"""Tests for AppSelector widget."""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from mobile_crawler.infrastructure.app_metadata_resolver import AppMetadata
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
    """Create AppSelector instance for tests.

    The real AppMetadataResolver is replaced with a Mock so tests never
    shell out to adb or the network; the background enrichment thread it
    drives is also patched out (`_start_enrichment`) unless a test is
    specifically exercising enrichment.
    """
    parent_widget = QWidget()
    with patch("mobile_crawler.ui.widgets.app_selector.AppMetadataResolver"):
        selector = AppSelector(config_store=mock_config_store, parent=parent_widget)
    yield selector
    # Cleanup
    selector.deleteLater()
    parent_widget.deleteLater()


class TestAppSelectorInit:
    """Tests for AppSelector initialization."""

    def test_initialization(self, qapp, app_selector):
        """Test that AppSelector initializes correctly."""
        assert app_selector.current_package() is None
        assert "No device connected" in app_selector.status_label.text()

    def test_no_manual_entry_field(self, qapp, app_selector):
        """Manual package entry was removed - only device-installed apps can be picked."""
        assert not hasattr(app_selector, "package_input")


class TestPackageValidation:
    """Tests for package name validation."""

    def test_valid_package_format(self, qapp, app_selector):
        """Test valid package name formats."""
        valid_packages = [
            "com.example.app",
            "com.google.android.gms",
            "org.example.test",
            "io.flutter.app",
            "com.company1.app2",
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


class TestSetDeviceId:
    """Tests for set_device_id auto-triggering the app list."""

    def test_set_device_id_triggers_list_refresh(self, qapp, app_selector):
        """Selecting a device auto-fetches the app list, no manual click required."""
        with patch.object(app_selector, "_list_installed_apps") as mock_list:
            app_selector.set_device_id("emulator-5554")

        assert app_selector.device_id == "emulator-5554"
        mock_list.assert_called_once()

    def test_set_device_id_none_clears_state(self, qapp, app_selector):
        """Clearing the device clears the combo and shows the no-device status."""
        app_selector.apps_combo.addItem("com.example.app", "com.example.app")

        app_selector.set_device_id(None)

        assert app_selector.device_id is None
        assert app_selector.apps_combo.count() == 0
        assert "No device connected" in app_selector.status_label.text()


class TestListInstalledApps:
    """Tests for listing installed apps."""

    def test_list_apps_with_no_device(self, qapp, app_selector):
        """Test listing apps when no device is connected."""
        with patch("mobile_crawler.ui.widgets.app_selector.QMessageBox.warning"):
            app_selector._list_installed_apps()

        assert "No device" in app_selector.status_label.text()
        assert app_selector.apps_combo.count() == 0

    def test_on_list_success_populates_combo(self, qapp, app_selector):
        """Parsed packages populate the combo as (package-text, package-data) pairs."""
        with patch.object(app_selector, "_start_enrichment"):
            app_selector._on_list_success("package:com.example.app\npackage:com.test.app")

        assert app_selector.apps_combo.count() == 3  # placeholder + 2 apps
        assert app_selector.apps_combo.itemText(1) == "com.example.app"
        assert app_selector.apps_combo.itemData(1) == "com.example.app"
        assert app_selector.apps_combo.itemText(2) == "com.test.app"
        assert "Found 2 apps" in app_selector.status_label.text()

    def test_on_list_success_starts_enrichment(self, qapp, app_selector):
        """Listing apps kicks off background metadata enrichment for the parsed packages."""
        with patch.object(app_selector, "_start_enrichment") as mock_enrich:
            app_selector._on_list_success("package:com.example.app")

        mock_enrich.assert_called_once_with(["com.example.app"])

    def test_on_list_error(self, qapp, app_selector):
        """Test listing apps when error occurs."""
        with patch("mobile_crawler.ui.widgets.app_selector.QMessageBox.critical"):
            app_selector._on_list_error("ADB error")

        assert "Error" in app_selector.status_label.text()

    def test_on_list_success_empty_result(self, qapp, app_selector):
        """Test listing apps when no apps found."""
        with patch.object(app_selector, "_start_enrichment") as mock_enrich:
            app_selector._on_list_success("")

        assert "No apps found" in app_selector.status_label.text()
        assert app_selector.apps_combo.count() == 0
        mock_enrich.assert_not_called()

    def test_on_list_success_restores_last_used_package(self, qapp, app_selector):
        """A previously saved package is auto-selected once it reappears in the list."""
        app_selector._pending_restore_package = "com.test.app"

        with patch.object(app_selector, "_start_enrichment"):
            app_selector._on_list_success("package:com.example.app\npackage:com.test.app")

        assert app_selector.current_package() == "com.test.app"
        # Restore is one-shot: consumed after the first successful list load.
        assert app_selector._pending_restore_package is None

    def test_on_list_success_restore_not_found(self, qapp, app_selector):
        """A saved package no longer installed on this device is reported, not silently dropped."""
        app_selector._pending_restore_package = "com.gone.app"

        with patch.object(app_selector, "_start_enrichment"):
            app_selector._on_list_success("package:com.example.app")

        assert app_selector.current_package() is None
        assert "not found on this device" in app_selector.status_label.text()


class TestComboSelection:
    """Tests for combo box selection."""

    def test_selecting_item_emits_package(self, qapp, app_selector):
        """Selecting a combo entry emits the underlying package, not the display label."""
        signal_emitted = []
        app_selector.app_selected.connect(signal_emitted.append)

        app_selector.apps_combo.addItem("Select an app...", None)
        app_selector.apps_combo.addItem("com.example.app", "com.example.app")
        app_selector.apps_combo.setCurrentIndex(1)

        assert app_selector.current_package() == "com.example.app"
        assert signal_emitted == ["com.example.app"]
        app_selector._config_store.set_setting.assert_called_with("last_app_package", "com.example.app", "string")

    def test_selecting_placeholder_clears_package(self, qapp, app_selector):
        """Selecting the placeholder entry (userData=None) clears the current selection."""
        app_selector.apps_combo.addItem("Select an app...", None)
        app_selector.apps_combo.addItem("com.example.app", "com.example.app")
        app_selector.apps_combo.setCurrentIndex(1)
        app_selector.apps_combo.setCurrentIndex(0)

        assert app_selector.current_package() is None

    def test_display_text_survives_enrichment_without_losing_selection(self, qapp, app_selector):
        """Renaming a combo item's display text (enrichment) must not change the selected package."""
        app_selector.apps_combo.addItem("com.example.app", "com.example.app")
        app_selector.apps_combo.setCurrentIndex(0)
        assert app_selector.current_package() == "com.example.app"

        app_selector.apps_combo.setItemText(0, "Example App")

        assert app_selector.current_package() == "com.example.app"


class TestEnrichment:
    """Tests for background app-metadata enrichment updating combo items."""

    def test_item_resolved_updates_text_and_icon(self, qapp, app_selector):
        app_selector.apps_combo.addItem("com.example.app", "com.example.app")
        metadata = AppMetadata(package="com.example.app", label="Example App", icon_path=None, source="local")

        app_selector._enrichment_generation = 1
        app_selector._on_item_resolved(1, "com.example.app", metadata)

        assert app_selector.apps_combo.itemText(0) == "Example App"

    def test_stale_generation_is_ignored(self, qapp, app_selector):
        """A result from a superseded list refresh (device switch, manual refresh) is dropped."""
        app_selector.apps_combo.addItem("com.example.app", "com.example.app")
        metadata = AppMetadata(package="com.example.app", label="Example App", icon_path=None, source="local")

        app_selector._enrichment_generation = 2  # a newer refresh has already started
        app_selector._on_item_resolved(1, "com.example.app", metadata)

        assert app_selector.apps_combo.itemText(0) == "com.example.app"


class TestClear:
    """Tests for clear method."""

    def test_clear_resets_state(self, qapp, app_selector):
        """Test that clear resets all state."""
        app_selector.apps_combo.addItem("com.example.app", "com.example.app")
        app_selector.apps_combo.setCurrentIndex(0)

        app_selector.clear()

        assert app_selector.apps_combo.count() == 0
        assert app_selector.current_package() is None


class TestUIComponents:
    """Tests for UI components."""

    def test_apps_combo_exists(self, qapp, app_selector):
        """Test that the apps combo exists and is the sole selection control."""
        assert app_selector.apps_combo is not None

    def test_refresh_button_exists(self, qapp, app_selector):
        """Test that refresh button exists."""
        assert app_selector.refresh_button is not None
        assert app_selector.refresh_button.text() == "Refresh Apps"

    def test_status_label_exists(self, qapp, app_selector):
        """Test that status label exists."""
        assert app_selector.status_label is not None
