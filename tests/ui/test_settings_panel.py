"""Tests for SettingsPanel widget."""

import datetime
import json
import sqlite3

import pytest
from PySide6.QtWidgets import QLineEdit, QMessageBox, QScrollArea


@pytest.fixture
def qt_app():
    """Create QApplication instance for all UI tests.

    This fixture is created at session scope to ensure QApplication
    exists for all UI tests. PySide6 requires exactly one QApplication
    instance to exist for widgets to work properly.
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class MockConfigStore:
    """Mock config store for testing without circular import."""

    def __init__(self, connection):
        self._connection = connection

    def get_secret_plaintext(self, key: str):
        cursor = self._connection.cursor()
        cursor.execute("SELECT encrypted_value FROM secrets WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row is None:
            return None
        # For testing, just return value as-is (not encrypted)
        return row["encrypted_value"].decode() if row else None

    def set_secret_plaintext(self, key: str, plaintext: str):
        # For testing, just store value as-is (not encrypted)
        cursor = self._connection.cursor()
        updated_at = datetime.datetime.now(datetime.UTC).isoformat()
        cursor.execute(
            """
            INSERT OR REPLACE INTO secrets (key, encrypted_value, updated_at)
            VALUES (?, ?, ?)
        """,
            (key, plaintext.encode(), updated_at),
        )
        self._connection.commit()

    def delete_secret(self, key: str):
        cursor = self._connection.cursor()
        cursor.execute("DELETE FROM secrets WHERE key = ?", (key,))
        self._connection.commit()

    def get_setting(self, key: str, default=None):
        cursor = self._connection.cursor()
        cursor.execute("SELECT value, value_type FROM user_config WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row is None:
            return default
        value_str, value_type = row["value"], row["value_type"]
        return self._convert_from_string(value_str, value_type)

    def set_setting(self, key: str, value, value_type=None):
        if value_type is None:
            value_type = self._detect_type(value)
        value_str = self._convert_to_string(value, value_type)
        cursor = self._connection.cursor()
        updated_at = datetime.datetime.now(datetime.UTC).isoformat()
        cursor.execute(
            """
            INSERT OR REPLACE INTO user_config (key, value, value_type, updated_at)
            VALUES (?, ?, ?, ?)
        """,
            (key, value_str, value_type, updated_at),
        )
        self._connection.commit()

    def delete_setting(self, key: str):
        cursor = self._connection.cursor()
        cursor.execute("DELETE FROM user_config WHERE key = ?", (key,))
        self._connection.commit()

    def _detect_type(self, value):
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, (list, dict)):
            return "json"
        else:
            return "string"

    def _convert_to_string(self, value, value_type):
        if value_type == "bool":
            return "true" if value else "false"
        elif value_type == "json":
            return json.dumps(value)
        else:
            return str(value)

    def _convert_from_string(self, value_str, value_type):
        if value_type == "bool":
            return value_str.lower() == "true"
        elif value_type == "int":
            return int(value_str)
        elif value_type == "float":
            return float(value_str)
        elif value_type == "json":
            return json.loads(value_str)
        else:
            return value_str


@pytest.fixture
def mock_config_store():
    """Create a mock config store for testing.

    Yields:
        Mock config store with in-memory database
    """
    # Create in-memory database for testing without file
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Create schema
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                value_type TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS secrets (
                key TEXT PRIMARY KEY,
                encrypted_value BLOB NOT NULL,
                updated_at TEXT NOT NULL
            )
    """)
    conn.commit()

    yield MockConfigStore(conn)


def _create_settings_panel(mock_config_store):
    """Create a new SettingsPanel instance for testing.

    Args:
        mock_config_store: Mock config store instance

    Returns:
        SettingsPanel instance with mock config store
    """
    # Import SettingsPanel here to avoid circular import
    from mobile_crawler.ui.widgets.settings_panel import SettingsPanel

    return SettingsPanel(mock_config_store)


class TestSettingsPanelInit:
    """Tests for SettingsPanel initialization."""

    def test_initialization(self, qt_app, mock_config_store):
        """Test that SettingsPanel initializes correctly."""
        panel = _create_settings_panel(mock_config_store)
        assert panel is not None
        assert hasattr(panel, "settings_saved")
        assert panel.settings_saved is not None

    def test_has_settings_saved_signal(self, qt_app, mock_config_store):
        """Test that settings_saved signal exists."""
        panel = _create_settings_panel(mock_config_store)
        assert hasattr(panel, "settings_saved")
        assert panel.settings_saved is not None

    def test_settings_tabs_are_grouped_by_workflow(self, qt_app, mock_config_store):
        """Test settings tabs use the consolidated workflow grouping."""
        panel = _create_settings_panel(mock_config_store)
        assert panel.tab_widget.count() == 4
        assert [panel.tab_widget.tabText(i) for i in range(panel.tab_widget.count())] == [
            "General",
            "AI Crawler",
            "API Keys & Parsing",
            "Integrations",
        ]

    def test_settings_tabs_are_scrollable(self, qt_app, mock_config_store):
        """Each settings tab should stay internally scrollable on short screens."""
        panel = _create_settings_panel(mock_config_store)

        for index in range(panel.tab_widget.count()):
            tab_page = panel.tab_widget.widget(index)
            assert isinstance(tab_page, QScrollArea)
            assert tab_page.widgetResizable()
            assert tab_page.widget() is not None

    def test_tab_widget_gets_vertical_stretch_over_save_button(self, qt_app, mock_config_store):
        """The tab content should receive extra vertical space before the save row."""
        panel = _create_settings_panel(mock_config_store)
        layout = panel.layout()

        assert layout.stretch(0) == 1
        assert layout.stretch(1) == 0


class TestAPIKeyInputs:
    """Tests for API key input fields."""

    def test_gemini_api_key_input_exists(self, qt_app, mock_config_store):
        """Test that Gemini API key input exists."""
        panel = _create_settings_panel(mock_config_store)
        assert hasattr(panel, "gemini_api_key_input")
        assert panel.gemini_api_key_input is not None

    def test_gemini_api_key_is_password_mode(self, qt_app, mock_config_store):
        """Test that Gemini API key input is password mode."""
        panel = _create_settings_panel(mock_config_store)
        assert panel.gemini_api_key_input.echoMode() == QLineEdit.EchoMode.Password

    def test_openrouter_api_key_input_exists(self, qt_app, mock_config_store):
        """Test that OpenRouter API key input exists."""
        panel = _create_settings_panel(mock_config_store)
        assert hasattr(panel, "openrouter_api_key_input")
        assert panel.openrouter_api_key_input is not None

    def test_openrouter_api_key_is_password_mode(self, qt_app, mock_config_store):
        """Test that OpenRouter API key input is password mode."""
        panel = _create_settings_panel(mock_config_store)
        assert panel.openrouter_api_key_input.echoMode() == QLineEdit.EchoMode.Password

    def test_mobsf_api_key_input_does_not_exist(self, qt_app, mock_config_store):
        """MobSF no longer exposes manual API key entry."""
        panel = _create_settings_panel(mock_config_store)
        assert not hasattr(panel, "mobsf_api_key_input")

    def test_get_gemini_api_key(self, qt_app, mock_config_store):
        """Test getting Gemini API key value."""
        panel = _create_settings_panel(mock_config_store)
        panel.gemini_api_key_input.setText("test-key-123")
        assert panel.get_gemini_api_key() == "test-key-123"

    def test_get_openrouter_api_key(self, qt_app, mock_config_store):
        """Test getting OpenRouter API key value."""
        panel = _create_settings_panel(mock_config_store)
        panel.openrouter_api_key_input.setText("test-key-456")
        assert panel.get_openrouter_api_key() == "test-key-456"

    def test_remote_omniparser_warmup_controls_exist(self, qt_app, mock_config_store):
        """Test that Replicate OmniParser warm-up controls exist."""
        panel = _create_settings_panel(mock_config_store)
        assert hasattr(panel, "omniparser_warmup_button")
        assert panel.omniparser_warmup_button.text() == "Warm Up Remote OmniParser"
        assert panel.omniparser_warmup_status_label.text() == "Idle"

    def test_remote_omniparser_warmup_visibility_follows_backend(self, qt_app, mock_config_store):
        """Warm-up controls are only shown for the remote Replicate backend."""
        panel = _create_settings_panel(mock_config_store)

        panel.omniparser_backend_combo.setCurrentText("local")
        assert panel.replicate_warmup_container.isHidden()

        panel.omniparser_backend_combo.setCurrentText("replicate")
        assert not panel.replicate_warmup_container.isHidden()

    def test_remote_omniparser_warmup_requires_api_key(self, qt_app, mock_config_store, monkeypatch):
        """Warm-up should not start without a Replicate API key."""
        panel = _create_settings_panel(mock_config_store)
        warnings = []

        def mock_warning(parent, title, message):
            warnings.append((title, message))

        monkeypatch.setattr(QMessageBox, "warning", mock_warning)
        panel.replicate_api_key_input.clear()

        panel._start_omniparser_warmup()

        assert warnings
        assert "Replicate API key is required" in panel.omniparser_warmup_status_label.text()
        assert panel.omniparser_warmup_button.isEnabled()

    def test_remote_omniparser_warmup_starts_background_worker(
        self, qt_app, mock_config_store, monkeypatch
    ):
        """Warm-up should disable the button and start a background worker."""
        panel = _create_settings_panel(mock_config_store)
        panel.replicate_api_key_input.setText("replicate-key")
        started = {}

        class FakeThread:
            def __init__(self, target, args, daemon):
                started["target"] = target
                started["args"] = args
                started["daemon"] = daemon

            def start(self):
                started["started"] = True

        monkeypatch.setattr("mobile_crawler.ui.widgets.settings_panel.threading.Thread", FakeThread)

        panel._start_omniparser_warmup()

        assert started["started"]
        assert started["daemon"] is True
        assert started["args"] == ("replicate-key", 0.05)
        assert not panel.omniparser_warmup_button.isEnabled()
        assert panel.omniparser_warmup_status_label.text() == "Warming up remote OmniParser..."

    def test_remote_omniparser_warmup_finished_updates_status(
        self, qt_app, mock_config_store, monkeypatch
    ):
        """Warm-up completion should re-enable the button and notify the user."""
        panel = _create_settings_panel(mock_config_store)
        panel.omniparser_warmup_button.setEnabled(False)
        messages = []

        def mock_information(parent, title, message):
            messages.append((title, message))

        monkeypatch.setattr(QMessageBox, "information", mock_information)

        panel._on_omniparser_warmup_finished(True, "Remote OmniParser warm-up complete in 1.2s.", 1.2)

        assert panel.omniparser_warmup_button.isEnabled()
        assert panel.omniparser_warmup_status_label.text() == "Remote OmniParser warm-up complete in 1.2s."
        assert messages == [("OmniParser Warm-Up Complete", "Remote OmniParser warm-up complete in 1.2s.")]


class TestCrawlLimitInputs:
    """Tests for crawl limit input fields."""

    def test_max_steps_input_exists(self, qt_app, mock_config_store):
        """Test that max steps input exists."""
        panel = _create_settings_panel(mock_config_store)
        assert hasattr(panel, "max_steps_input")
        assert panel.max_steps_input is not None

    def test_max_steps_default_value(self, qt_app, mock_config_store):
        """Test that max steps has default value of 100."""
        panel = _create_settings_panel(mock_config_store)
        assert panel.max_steps_input.value() == 100

    def test_get_max_steps(self, qt_app, mock_config_store):
        """Test getting max steps value."""
        panel = _create_settings_panel(mock_config_store)
        panel.max_steps_input.setValue(250)
        assert panel.get_max_steps() == 250

    def test_max_duration_input_exists(self, qt_app, mock_config_store):
        """Test that max duration input exists."""
        panel = _create_settings_panel(mock_config_store)
        assert hasattr(panel, "max_duration_input")
        assert panel.max_duration_input is not None

    def test_max_duration_default_value(self, qt_app, mock_config_store):
        """Test that max duration has default value of 300."""
        panel = _create_settings_panel(mock_config_store)
        assert panel.max_duration_input.value() == 300

    def test_get_max_duration(self, qt_app, mock_config_store):
        """Test getting max duration value."""
        panel = _create_settings_panel(mock_config_store)
        panel.max_duration_input.setValue(600)
        assert panel.get_max_duration() == 600


class TestCredentialInputs:
    """Tests for test credential input fields."""

    def test_test_username_input_exists(self, qt_app, mock_config_store):
        """Test that test username input exists."""
        panel = _create_settings_panel(mock_config_store)
        assert hasattr(panel, "test_username_input")
        assert panel.test_username_input is not None

    def test_get_test_username(self, qt_app, mock_config_store):
        """Test getting test username value."""
        panel = _create_settings_panel(mock_config_store)
        panel.test_username_input.setText("testuser")
        assert panel.get_test_username() == "testuser"

    def test_test_password_input_exists(self, qt_app, mock_config_store):
        """Test that test password input exists."""
        panel = _create_settings_panel(mock_config_store)
        assert hasattr(panel, "test_password_input")
        assert panel.test_password_input is not None

    def test_test_password_is_password_mode(self, qt_app, mock_config_store):
        """Test that test password input is password mode."""
        panel = _create_settings_panel(mock_config_store)
        assert panel.test_password_input.echoMode() == QLineEdit.EchoMode.Password


class TestReset:
    """Tests for reset functionality."""

    def test_reset_clears_api_keys(self, qt_app, mock_config_store):
        """Test that reset clears API key inputs."""
        panel = _create_settings_panel(mock_config_store)
        panel.gemini_api_key_input.setText("test-key")
        panel.openrouter_api_key_input.setText("test-key-2")
        panel.reset()
        assert panel.gemini_api_key_input.text() == ""
        assert panel.openrouter_api_key_input.text() == ""

    def test_reset_clears_crawl_limits(self, qt_app, mock_config_store):
        """Test that reset clears crawl limit inputs."""
        panel = _create_settings_panel(mock_config_store)
        panel.max_steps_input.setValue(500)
        panel.max_duration_input.setValue(900)
        panel.reset()
        assert panel.max_steps_input.value() == 100
        assert panel.max_duration_input.value() == 300

    def test_reset_clears_credentials(self, qt_app, mock_config_store):
        """Test that reset clears credential inputs."""
        panel = _create_settings_panel(mock_config_store)
        panel.test_username_input.setText("testuser_custom")
        panel.test_password_input.setText("testpass_custom")
        panel.test_address_input.setText("Some Other Address")
        panel.test_email_input.setText("other_email@example.com")
        panel.test_phone_input.setText("+123456789")
        panel.reset()
        assert panel.test_username_input.text() == "testuser"
        assert panel.test_password_input.text() == "Password123"
        assert panel.test_address_input.text() == "Kaiserstraße 12, 60311 Frankfurt am Main, Germany"
        assert panel.test_email_input.text() == "testuser@example.com"
        assert panel.test_phone_input.text() == ""

    def test_reset_exploration_objective_via_button(self, qt_app, mock_config_store):
        """Test that clicking the Reset to Default button resets the objective prompt."""
        from mobile_crawler.ui.widgets.settings_panel import DEFAULT_EXPLORATION_OBJECTIVE
        panel = _create_settings_panel(mock_config_store)
        panel.exploration_objective_input.setPlainText("Custom Objective")
        assert panel.exploration_objective_input.toPlainText() == "Custom Objective"
        panel.reset_objective_button.click()
        assert panel.exploration_objective_input.toPlainText() == DEFAULT_EXPLORATION_OBJECTIVE


class TestSettingsSavedSignal:
    """Tests for settings_saved signal."""

    def test_save_emits_signal(self, qt_app, mock_config_store, monkeypatch):
        """Test that save button emits settings_saved signal."""
        panel = _create_settings_panel(mock_config_store)
        signal_emitted = False

        def on_settings_saved():
            nonlocal signal_emitted
            signal_emitted = True

        panel.settings_saved.connect(on_settings_saved)

        # Mock QMessageBox to avoid showing dialog
        def mock_information(parent, title, message):
            pass

        monkeypatch.setattr(QMessageBox, "information", mock_information)

        # Trigger save
        panel._on_save_clicked()
        assert signal_emitted


class TestSettingsPersistence:
    """Tests for settings persistence across sessions."""

    def test_save_and_load_settings(self, qt_app, mock_config_store, monkeypatch):
        """Test that settings are saved and can be loaded."""
        panel = _create_settings_panel(mock_config_store)

        # Set values (use longer API keys to pass validation - min 20 chars)
        panel.gemini_api_key_input.setText("AIzaTestKey123456789")
        panel.openrouter_api_key_input.setText("sk-or-test-key-1234567890")
        panel.max_steps_input.setValue(250)
        panel.max_duration_input.setValue(600)
        panel.test_username_input.setText("testuser")
        panel.test_password_input.setText("testpass")
        panel.omniparser_backend_combo.setCurrentText("local")
        panel.omniparser_local_parse_timeout_input.setValue(180)

        # Mock QMessageBox to avoid showing dialog
        def mock_information(parent, title, message):
            pass

        monkeypatch.setattr(QMessageBox, "information", mock_information)

        # Save settings
        panel._on_save_clicked()

        # Create new panel instance (simulating app restart)
        panel2 = _create_settings_panel(mock_config_store)

        # Verify all settings were loaded
        assert panel2.gemini_api_key_input.text() == "AIzaTestKey123456789"
        assert panel2.openrouter_api_key_input.text() == "sk-or-test-key-1234567890"
        assert panel2.max_steps_input.value() == 250
        assert panel2.max_duration_input.value() == 600
        assert panel2.test_username_input.text() == "testuser"
        assert panel2.test_password_input.text() == "testpass"
        assert panel2.omniparser_local_parse_timeout_input.value() == 180

    def test_omniparser_local_parse_timeout_persists(self, qt_app, mock_config_store, monkeypatch):
        """Test that local OmniParser parse timeout persists across sessions."""
        panel = _create_settings_panel(mock_config_store)
        panel.omniparser_backend_combo.setCurrentText("local")
        panel.omniparser_local_parse_timeout_input.setValue(240)

        def mock_information(parent, title, message):
            pass

        monkeypatch.setattr(QMessageBox, "information", mock_information)

        panel._on_save_clicked()

        assert mock_config_store.get_setting("omniparser_local_parse_timeout_seconds") == 240
        assert panel.get_omniparser_local_parse_timeout_seconds() == 240

    def test_load_settings_with_defaults(self, qt_app, mock_config_store):
        """Test that settings load defaults when nothing is saved."""
        panel = _create_settings_panel(mock_config_store)

        # Verify defaults are loaded
        assert panel.gemini_api_key_input.text() == ""
        assert panel.openrouter_api_key_input.text() == ""
        assert panel.max_steps_input.value() == 100
        assert panel.max_duration_input.value() == 300
        assert panel.test_username_input.text() == "testuser"
        assert panel.test_password_input.text() == "Password123"

    def test_gemini_api_key_persists(self, qt_app, mock_config_store, monkeypatch):
        """Test that Gemini API key persists across sessions."""
        panel = _create_settings_panel(mock_config_store)
        panel.gemini_api_key_input.setText("AIzaTestKey123456789")

        # Mock QMessageBox
        def mock_information(parent, title, message):
            pass

        monkeypatch.setattr(QMessageBox, "information", mock_information)

        panel._on_save_clicked()

        # Verify in database
        saved_key = mock_config_store.get_secret_plaintext("gemini_api_key")
        assert saved_key == "AIzaTestKey123456789"

    def test_openrouter_api_key_persists(self, qt_app, mock_config_store, monkeypatch):
        """Test that OpenRouter API key persists across sessions."""
        panel = _create_settings_panel(mock_config_store)
        panel.openrouter_api_key_input.setText("sk-or-test-key-1234567890")

        # Mock QMessageBox
        def mock_information(parent, title, message):
            pass

        monkeypatch.setattr(QMessageBox, "information", mock_information)

        panel._on_save_clicked()

        # Verify in database
        saved_key = mock_config_store.get_secret_plaintext("openrouter_api_key")
        assert saved_key == "sk-or-test-key-1234567890"

    def test_crawl_limits_persist(self, qt_app, mock_config_store, monkeypatch):
        """Test that crawl limits persist across sessions."""
        panel = _create_settings_panel(mock_config_store)
        panel.max_steps_input.setValue(500)
        panel.max_duration_input.setValue(900)

        # Mock QMessageBox
        def mock_information(parent, title, message):
            pass

        monkeypatch.setattr(QMessageBox, "information", mock_information)

        panel._on_save_clicked()

        # Verify in database
        saved_max_steps = mock_config_store.get_setting("max_steps", default=100)
        saved_max_duration = mock_config_store.get_setting("max_duration_seconds", default=300)
        assert saved_max_steps == 500
        assert saved_max_duration == 900

    def test_test_credentials_persist(self, qt_app, mock_config_store, monkeypatch):
        """Test that test credentials persist across sessions."""
        panel = _create_settings_panel(mock_config_store)
        panel.test_username_input.setText("testuser123")
        panel.test_password_input.setText("testpass456")

        # Mock QMessageBox
        def mock_information(parent, title, message):
            pass

        monkeypatch.setattr(QMessageBox, "information", mock_information)

        panel._on_save_clicked()

        # Verify in database
        saved_username = mock_config_store.get_setting("test_username", default="")
        saved_password = mock_config_store.get_secret_plaintext("test_password")
        assert saved_username == "testuser123"
        assert saved_password == "testpass456"

    def test_saving_settings_does_not_write_mobsf_api_key(self, qt_app, mock_config_store, monkeypatch):
        """Saving SettingsPanel must not persist or delete manual MobSF secrets."""
        mock_config_store.set_secret_plaintext("mobsf_api_key", "legacy-key")
        panel = _create_settings_panel(mock_config_store)
        panel.enable_mobsf_analysis_checkbox.setChecked(True)
        panel.mobsf_api_url_input.setText("http://localhost:8000")

        def mock_information(parent, title, message):
            pass

        monkeypatch.setattr(QMessageBox, "information", mock_information)

        panel._on_save_clicked()

        assert mock_config_store.get_secret_plaintext("mobsf_api_key") == "legacy-key"
