"""Focused tests for current MainWindow behavior."""

from unittest.mock import Mock, patch

from mobile_crawler.ui.main_window import MainWindow


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


class TestRunFunction:
    """Tests for current GUI entrypoint behavior."""

    @patch("mobile_crawler.ui.main_window.QApplication")
    @patch("mobile_crawler.ui.main_window.MainWindow")
    @patch("mobile_crawler.ui.main_window.QIcon")
    @patch("mobile_crawler.ui.main_window.sys.exit")
    def test_run_shows_window_maximized_and_exits_with_app_code(
        self,
        mock_exit,
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

        mock_qapp.assert_called_once()
        mock_window.assert_called_once()
        mock_window_instance.showMaximized.assert_called_once()
        mock_exit.assert_called_once_with(42)
