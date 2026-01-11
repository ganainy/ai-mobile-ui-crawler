"""Tests for MainWindow module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication, QWidget, QSplitter, QPushButton, QMenu
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMessageBox

from mobile_crawler.ui.main_window import MainWindow


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
def mock_services():
    """Create mocked services for MainWindow testing."""
    services = {
        'device_detection': Mock(),
        'appium_driver': Mock(),
        'provider_registry': Mock(),
        'vision_detector': Mock(),
        'crawl_controller': Mock(),
        'user_config_store': Mock(),
        'run_repository': Mock(),
        'report_generator': Mock(),
        'mobsf_manager': Mock(),
        'database_manager': Mock(),
    }
    
    # Configure mocks with proper return values
    services['device_detection'].get_available_devices.return_value = []
    services['user_config_store'].create_schema.return_value = None
    services['user_config_store'].get_secret_plaintext.side_effect = lambda key: {
        "gemini_api_key": "test_gemini_key",
        "openrouter_api_key": "test_openrouter_key"
    }.get(key, "")  # Return test keys for known providers, empty for others
    services['user_config_store'].get_setting.side_effect = lambda key, default=None: {
        "system_prompt": "",
        "max_steps": 100,
        "max_duration": 3600,
        "screenshot_interval": 5,
        "auto_save": True,
        "theme": "light"
    }.get(key, default)
    services['database_manager'].create_schema.return_value = None
    services['run_repository'].create_run.return_value = 1
    services['run_repository'].get_all_runs.return_value = []
    from mobile_crawler.core.crawl_state_machine import CrawlState
    services['crawl_controller'].get_state.return_value = CrawlState.UNINITIALIZED
    
    return services


@pytest.fixture
def main_window(qapp, mock_services):
    """Create MainWindow instance with mocked services."""
    with patch('mobile_crawler.ui.main_window.MainWindow._create_services', return_value=mock_services):
        window = MainWindow()
        yield window
        window.close()


@pytest.fixture
def main_window_with_real_services(qapp):
    """Create MainWindow instance for tests that need real initialization."""
    window = MainWindow()
    yield window
    window.close()


class TestMainWindowInit:
    """Tests for MainWindow initialization."""

    def test_window_title(self, main_window):
        """Test that window has correct title."""
        assert main_window.windowTitle() == "Mobile Crawler"

    def test_minimum_size(self, main_window):
        """Test that window has minimum size."""
        size = main_window.minimumSize()
        assert size.width() >= 1024
        assert size.height() >= 768

    def test_default_size(self, main_window):
        """Test that window has default size."""
        size = main_window.size()
        assert size.width() == 1280
        assert size.height() == 960

    def test_menu_bar_exists(self, main_window):
        """Test that menu bar is created."""
        menubar = main_window.menuBar()
        assert menubar is not None

    def test_central_widget_exists(self, main_window):
        """Test that central widget is created."""
        central_widget = main_window.centralWidget()
        assert central_widget is not None


class TestMenu:
    """Tests for menu bar functionality."""

    def test_file_menu_exists(self, main_window):
        """Test that File menu exists."""
        menubar = main_window.menuBar()
        actions = menubar.actions()
        
        file_menu = None
        for action in actions:
            if action.menu() and "&File" in action.menu().title():
                file_menu = action.menu()
                break
        
        assert file_menu is not None

    def test_help_menu_exists(self, main_window):
        """Test that Help menu exists."""
        menubar = main_window.menuBar()
        actions = menubar.actions()
        
        help_menu = None
        for action in actions:
            if action.menu() and "&Help" in action.menu().title():
                help_menu = action.menu()
                break
        
        assert help_menu is not None

    def test_exit_action_exists(self, main_window):
        """Test that Exit action exists in File menu."""
        menubar = main_window.menuBar()
        actions = menubar.actions()
        
        exit_action = None
        for action in actions:
            menu = action.menu()
            if menu and "&File" in menu.title():
                for menu_action in menu.actions():
                    if "E&xit" in menu_action.text():
                        exit_action = menu_action
                        break
                break
        
        assert exit_action is not None

    def test_about_action_exists(self, main_window):
        """Test that About action exists in Help menu."""
        menubar = main_window.menuBar()
        actions = menubar.actions()
        
        about_action = None
        for action in actions:
            menu = action.menu()
            if menu and "&Help" in menu.title():
                for menu_action in menu.actions():
                    if "&About" in menu_action.text():
                        about_action = menu_action
                        break
                break
        
        assert about_action is not None


class TestCloseEvent:
    """Tests for window close event."""

    def test_close_event_accepts(self, main_window, qapp):
        """Test that close event is accepted."""
        event = QCloseEvent()
        main_window.closeEvent(event)
        
        assert event.isAccepted()

    def test_close_with_menu_exit(self, main_window, qapp):
        """Test that Exit menu action closes window."""
        menubar = main_window.menuBar()
        actions = menubar.actions()
        
        exit_action = None
        for action in actions:
            menu = action.menu()
            if menu and "&File" in menu.title():
                for menu_action in menu.actions():
                    if "E&xit" in menu_action.text():
                        exit_action = menu_action
                        break
                break
        
        if exit_action:
            exit_action.trigger()
            assert main_window.isHidden() or not main_window.isVisible()


class TestAboutDialog:
    """Tests for About dialog."""

    def test_show_about_does_not_raise(self, main_window):
        """Test that About dialog is shown without errors."""
        # Just verify that method can be called without raising an exception
        # The actual QMessageBox.about is a static method that shows a dialog
        main_window._show_about()
        
        # If we get here, the method executed successfully
        assert True


class TestRunFunction:
    """Tests for run() entry point."""

    @patch('mobile_crawler.ui.main_window.QApplication')
    @patch('mobile_crawler.ui.main_window.MainWindow')
    @patch('mobile_crawler.ui.main_window.sys.exit')
    def test_run_creates_application(self, mock_exit, mock_window, mock_qapp):
        """Test that run() creates QApplication."""
        from mobile_crawler.ui.main_window import run
        
        mock_qapp_instance = Mock()
        mock_qapp_instance.exec = Mock(return_value=0)
        mock_qapp.return_value = mock_qapp_instance
        
        mock_window_instance = Mock()
        mock_window_instance.show = Mock()
        mock_window.return_value = mock_window_instance
        
        run()
        
        mock_qapp.assert_called_once()
        mock_window.assert_called_once()
        mock_window_instance.show.assert_called_once()
        mock_qapp_instance.exec.assert_called_once()

    @patch('mobile_crawler.ui.main_window.QApplication')
    @patch('mobile_crawler.ui.main_window.MainWindow')
    @patch('mobile_crawler.ui.main_window.sys.exit')
    def test_run_exits_with_app_code(self, mock_exit, mock_window, mock_qapp):
        """Test that run() exits with QApplication return code."""
        from mobile_crawler.ui.main_window import run
        
        mock_qapp_instance = Mock()
        mock_qapp_instance.exec = Mock(return_value=42)
        mock_qapp.return_value = mock_qapp_instance
        
        run()
        
        mock_exit.assert_called_once_with(42)


class TestMainWindowWidgets:
    """Tests for MainWindow widget visibility and functionality."""

    def test_main_window_widgets_visible(self, main_window, qtbot):
        """Test all main widgets are visible when window is shown."""
        qtbot.addWidget(main_window)
        main_window.show()
        
        # Check that all main widgets exist and are visible
        device_selector = main_window.findChild(QWidget, "deviceSelector")
        assert device_selector is not None
        assert device_selector.isVisible()
        
        app_selector = main_window.findChild(QWidget, "appSelector")
        assert app_selector is not None
        assert app_selector.isVisible()
        
        ai_model_selector = main_window.findChild(QWidget, "aiModelSelector")
        assert ai_model_selector is not None
        assert ai_model_selector.isVisible()
        
        crawl_control = main_window.findChild(QWidget, "crawlControlPanel")
        assert crawl_control is not None
        assert crawl_control.isVisible()
        
        log_viewer = main_window.findChild(QWidget, "logViewer")
        assert log_viewer is not None
        assert log_viewer.isVisible()
        
        stats_dashboard = main_window.findChild(QWidget, "statsDashboard")
        assert stats_dashboard is not None
        assert stats_dashboard.isVisible()

    def test_start_button_disabled_when_not_configured(self, main_window, qtbot):
        """Test Start button is disabled when device/app/AI not configured."""
        qtbot.addWidget(main_window)
        main_window.show()
        
        # Find the crawl control panel and start button
        crawl_control = main_window.findChild(QWidget, "crawlControlPanel")
        assert crawl_control is not None
        
        start_button = crawl_control.findChild(QPushButton, "startButton")
        assert start_button is not None
        
        # Initially should be disabled (no device/app/AI selected)
        assert not start_button.isEnabled()

    def test_start_button_enabled_when_configured(self, main_window, qtbot):
        """Test Start button is enabled when device, app, and AI are configured."""
        qtbot.addWidget(main_window)
        main_window.show()
        
        # Set internal state directly
        main_window._selected_device = "emulator-5554"
        main_window._selected_package = "com.example.app"
        main_window._ai_provider = "gemini"
        main_window._ai_model = "gemini-1.5-flash"
        
        # Set API key in settings panel
        main_window.settings_panel.gemini_api_key_input.setText("test_gemini_key")
        
        # Call the update method
        main_window._update_start_button_state()
        
        # Find the start button
        crawl_control = main_window.findChild(QWidget, "crawlControlPanel")
        start_button = crawl_control.findChild(QPushButton, "startButton")
        
        # Should now be enabled
        assert start_button.isEnabled()

    def test_signal_connections_device_to_app(self, main_window, qtbot):
        """Test that device selection signal can be emitted without errors."""
        qtbot.addWidget(main_window)
        main_window.show()
        
        device_selector = main_window.findChild(QWidget, "deviceSelector")
        app_selector = main_window.findChild(QWidget, "appSelector")
        
        # Emit device selected signal - should not raise any exceptions
        device_selector.device_selected.emit("emulator-5554")
        
        # App selector should still be functional
        assert app_selector is not None
        assert app_selector.isVisible()

    def test_button_states_on_crawl_start_pause_stop(self, main_window, qtbot):
        """Test button state changes during crawl lifecycle."""
        qtbot.addWidget(main_window)
        main_window.show()
        
        # Set up initial state
        main_window._selected_device = "emulator-5554"
        main_window._selected_package = "com.example.app"
        main_window._ai_provider = "gemini"
        main_window._ai_model = "gemini-1.5-flash"
        
        # Set API key in settings panel
        main_window.settings_panel.gemini_api_key_input.setText("test_gemini_key")
        
        main_window._update_start_button_state()
        
        crawl_control = main_window.findChild(QWidget, "crawlControlPanel")
        start_button = crawl_control.findChild(QPushButton, "startButton")
        pause_button = crawl_control.findChild(QPushButton, "pauseButton")
        stop_button = crawl_control.findChild(QPushButton, "stopButton")
        
        # Initially: start enabled, pause/stop disabled
        assert start_button.isEnabled()
        assert not pause_button.isEnabled()
        assert not stop_button.isEnabled()
        
        # Simulate crawl started by updating control panel state
        from mobile_crawler.core.crawl_state_machine import CrawlState
        main_window.control_panel.update_state(CrawlState.RUNNING)
        
        # After start: start disabled, pause/stop enabled
        assert not start_button.isEnabled()
        assert pause_button.isEnabled()
        assert stop_button.isEnabled()
        
        # Simulate crawl paused
        main_window.control_panel.update_state(CrawlState.PAUSED_MANUAL)
        
        # After pause: resume enabled, pause disabled, stop enabled
        assert not start_button.isEnabled()
        assert not pause_button.isEnabled()
        assert stop_button.isEnabled()
        resume_button = crawl_control.findChild(QPushButton, "resumeButton")
        assert resume_button.isEnabled()
        
        # Simulate crawl stopped
        main_window.control_panel.update_state(CrawlState.STOPPED)
        
        # After stop: back to initial state
        assert start_button.isEnabled()
        assert not pause_button.isEnabled()
        assert not stop_button.isEnabled()
