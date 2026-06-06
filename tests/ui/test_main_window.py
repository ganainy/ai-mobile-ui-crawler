"""Focused tests for current MainWindow behavior."""

from unittest.mock import Mock, patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QWidget

from mobile_crawler.ui.main_window import MainWindow


class _Connectable:
    """Minimal signal stub for layout-only MainWindow tests."""

    def connect(self, _slot):
        pass


class _FakeControlPanel:
    def __init__(self):
        self.start_requested = _Connectable()
        self.pause_requested = _Connectable()
        self.resume_requested = _Connectable()
        self.stop_requested = _Connectable()
        self.step_by_step_toggled = _Connectable()
        self.next_step_requested = _Connectable()

    def set_step_by_step(self, _enabled):
        pass


class _FakeSignalAdapter:
    def __init__(self):
        self.state_changed = _Connectable()
        self.step_started = _Connectable()
        self.action_executed = _Connectable()
        self.step_completed = _Connectable()
        self.crawl_completed = _Connectable()
        self.screen_processed = _Connectable()
        self.step_paused = _Connectable()
        self.debug_log = _Connectable()
        self.ocr_completed = _Connectable()
        self.screenshot_timing = _Connectable()
        self.step_phase_transition = _Connectable()


class _FakeSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.model_selected = _Connectable()
        self.device_selected = _Connectable()
        self.app_selected = _Connectable()
        self.settings_saved = _Connectable()

    def set_api_key_callback(self, _callback):
        pass

    def current_package(self):
        return ""

    def _refresh_devices(self):
        pass


class _FakeRunHistory(QWidget):
    def _load_runs(self):
        pass


class TestMainWindowConfig:
    """Tests for run configuration creation without full GUI startup."""

    @patch("mobile_crawler.ui.main_window.ConfigManager")
    def test_create_config_manager_enables_tls_with_traffic_capture(self, mock_config_manager_cls):
        """GUI run config should request TLS decryption when traffic capture is enabled."""
        window = MainWindow.__new__(MainWindow)
        window._services = {"user_config_store": Mock()}
        window._ai_provider = "gemini"
        window._ai_model = "gemini-pro"
        window._selected_package = "com.example.app"
        window.signal_adapter = Mock()
        window.settings_panel = Mock()
        window.settings_panel.get_max_steps.return_value = 15
        window.settings_panel.get_max_duration.return_value = 600
        window.settings_panel.get_gemini_api_key.return_value = ""
        window.settings_panel.get_openrouter_api_key.return_value = ""
        window.settings_panel.get_test_username.return_value = ""
        window.settings_panel.get_test_password.return_value = ""
        window.settings_panel.get_top_bar_height.return_value = 0
        window.settings_panel.get_enable_traffic_capture.return_value = True
        window.settings_panel.get_enable_video_recording.return_value = False
        window.settings_panel.get_enable_mobsf_analysis.return_value = False
        window.settings_panel.get_pcapdroid_api_key.return_value = "pcap-key"
        window.settings_panel.get_mobsf_api_url.return_value = ""
        window.settings_panel.get_ui_parser_mode.return_value = "boost"
        window.settings_panel.get_omniparser_backend.return_value = "local"
        window.settings_panel.get_omniparser_local_url.return_value = "http://localhost:8000"
        window.settings_panel.get_omniparser_local_parse_timeout_seconds.return_value = 180
        window.settings_panel.get_replicate_api_key.return_value = ""
        window.settings_panel.get_exploration_objective.return_value = ""

        config_manager = Mock()
        config_manager.get.side_effect = (
            lambda key, default=None: True if key == "enable_traffic_capture" else default
        )
        mock_config_manager_cls.return_value = config_manager

        window._create_config_manager()

        config_manager.set.assert_any_call("enable_traffic_capture", True)
        config_manager.set.assert_any_call("pcapdroid_tls_decryption", True)
        config_manager.set.assert_any_call("omniparser_local_parse_timeout_seconds", 180)


class TestMainWindowLayout:
    """Tests for responsive MainWindow layout contracts."""

    def test_left_panel_gives_settings_panel_vertical_stretch(self, qt_app):
        """Selectors should keep natural height while SettingsPanel gets spare space."""
        window = MainWindow.__new__(MainWindow)
        window._services = {
            "device_detection": Mock(),
            "user_config_store": Mock(),
            "provider_registry": Mock(),
            "vision_detector": Mock(),
        }
        window._selected_package = None
        window._get_api_key_for_provider = Mock()
        window._on_model_selected = Mock()
        window._on_settings_saved = Mock()
        window._on_device_selected = Mock()
        window._on_app_selected = Mock()

        with (
            patch("mobile_crawler.ui.main_window.DeviceSelector", return_value=_FakeSelector()),
            patch("mobile_crawler.ui.main_window.AppSelector", return_value=_FakeSelector()),
            patch("mobile_crawler.ui.main_window.AIModelSelector", return_value=_FakeSelector()),
            patch("mobile_crawler.ui.main_window.SettingsPanel", return_value=_FakeSelector()),
        ):
            panel = MainWindow._create_left_panel(window)

        layout = panel.layout()
        assert layout.stretch(0) == 0
        assert layout.stretch(1) == 0
        assert layout.stretch(2) == 0
        assert layout.stretch(3) == 1

    def test_bottom_panel_uses_reduced_run_history_minimum(self, qt_app):
        """MainWindow should not restore the old 280px Run History minimum."""
        window = MainWindow.__new__(MainWindow)
        window._services = {
            "run_repository": Mock(),
            "report_generator": Mock(),
            "mobsf_manager": Mock(),
        }

        with patch("mobile_crawler.ui.main_window.RunHistoryView", side_effect=lambda *_args: _FakeRunHistory()):
            panel = MainWindow._create_bottom_panel(window)

        assert panel is not None
        assert window.run_history_view.minimumHeight() == 170

    def test_central_widget_uses_vertical_splitter_for_run_history(self, qt_app, monkeypatch):
        """Main workspace and Run History should be separated by a resizable splitter."""
        monkeypatch.setattr(
            MainWindow,
            "_create_services",
            lambda self: {
                "database_manager": Mock(),
                "user_config_store": Mock(get_setting=Mock(return_value=False)),
            },
        )
        monkeypatch.setattr(
            "mobile_crawler.ui.main_window.StaleRunCleaner",
            lambda _db: Mock(cleanup_stale_runs=Mock()),
        )
        monkeypatch.setattr(MainWindow, "_setup_python_logging", lambda self: None)
        monkeypatch.setattr(MainWindow, "_connect_statistics_signals", lambda self: None)
        monkeypatch.setattr(MainWindow, "_update_start_button_state", lambda self: None)

        def create_left_panel(self):
            self.device_selector = _FakeSelector()
            self.app_selector = _FakeSelector()
            self.ai_selector = _FakeSelector()
            self.settings_panel = _FakeSelector()
            return QWidget()

        def create_center_panel(self):
            self.control_panel = _FakeControlPanel()
            self.stats_dashboard = QWidget()
            return QWidget()

        def create_right_panel(self):
            self.log_viewer = QWidget()
            return QWidget()

        def create_bottom_panel(self):
            self.run_history_view = _FakeRunHistory()
            self.run_history_view.setMinimumHeight(170)
            return self.run_history_view

        monkeypatch.setattr(MainWindow, "_create_left_panel", create_left_panel)
        monkeypatch.setattr(MainWindow, "_create_center_panel", create_center_panel)
        monkeypatch.setattr(MainWindow, "_create_right_panel", create_right_panel)
        monkeypatch.setattr(MainWindow, "_create_bottom_panel", create_bottom_panel)
        monkeypatch.setattr("mobile_crawler.ui.main_window.QtSignalAdapter", _FakeSignalAdapter)

        window = MainWindow()
        workspace_splitter = window.findChild(QSplitter, "workspaceSplitter")

        assert workspace_splitter is not None
        assert workspace_splitter.orientation() == Qt.Orientation.Vertical
        assert workspace_splitter.count() == 2
        assert window.run_history_view.minimumHeight() == 170


class TestRunFunction:
    """Tests for current GUI entrypoint behavior."""

    def test_gui_icon_path_uses_root_ico(self):
        """The GUI should use the root crawler_logo.ico asset."""
        from mobile_crawler.ui.main_window import _get_gui_icon_path

        icon_path = _get_gui_icon_path()

        assert icon_path.endswith("crawler_logo.ico")
        assert "mobile-crawler" in icon_path

    @patch("mobile_crawler.ui.main_window.QApplication")
    @patch("mobile_crawler.ui.main_window.MainWindow")
    @patch("mobile_crawler.ui.main_window.QIcon")
    @patch("mobile_crawler.ui.main_window._set_windows_app_user_model_id")
    @patch("mobile_crawler.ui.main_window.sys.exit")
    def test_run_shows_window_maximized_and_exits_with_app_code(
        self,
        mock_exit,
        mock_set_app_id,
        mock_qicon,
        mock_window,
        mock_qapp,
    ):
        """The GUI launcher should show the main window maximized."""
        from mobile_crawler.ui.main_window import run

        mock_qapp_instance = Mock()
        mock_qapp_instance.exec = Mock(return_value=42)
        mock_qapp.return_value = mock_qapp_instance

        mock_window_instance = Mock()
        mock_window.return_value = mock_window_instance

        run()

        mock_set_app_id.assert_called_once()
        mock_qapp.assert_called_once()
        mock_qapp_instance.setWindowIcon.assert_called_once_with(mock_qicon.return_value)
        assert mock_qicon.call_args.args[0].endswith("crawler_logo.ico")
        mock_window.assert_called_once()
        mock_window_instance.showMaximized.assert_called_once()
        mock_exit.assert_called_once_with(42)
