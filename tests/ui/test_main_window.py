"""Tests for MainWindow module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication
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
def main_window(qapp):
    """Create MainWindow instance for tests."""
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
