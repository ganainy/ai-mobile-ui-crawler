"""Tests for app context manager."""

from unittest.mock import Mock, patch

import pytest

from mobile_crawler.domain.app_context_manager import AppContextManager


class TestAppContextManager:
    """Test AppContextManager."""

    @pytest.fixture
    def mock_driver(self):
        """Mock AppiumDriver."""
        driver = Mock()
        driver.capabilities = {'currentPackage': 'com.example.app'}
        driver.page_source = '<?xml version="1.0"?><hierarchy package="com.example.app"></hierarchy>'
        driver.back = Mock()
        driver.launch_app = Mock()

        appium_driver = Mock()
        appium_driver.get_driver.return_value = driver
        return appium_driver

    @pytest.fixture
    def context_manager(self, mock_driver):
        """Create AppContextManager with mocks."""
        return AppContextManager(
            appium_driver=mock_driver,
            target_package='com.example.target',
            allowed_packages=['com.android.browser']
        )

    def test_initialization(self, context_manager):
        """Test initialization sets up allowed packages."""
        assert context_manager.target_package == 'com.example.target'
        assert 'com.example.target' in context_manager.allowed_packages
        assert 'com.android.browser' in context_manager.allowed_packages
        assert context_manager.current_package is None
        assert context_manager.context_loss_count == 0
        assert context_manager.context_recovery_count == 0

    def test_update_context_from_capabilities(self, context_manager, mock_driver):
        """Test updating context from driver capabilities."""
        package = context_manager.update_context()
        assert package == 'com.example.app'
        assert context_manager.current_package == 'com.example.app'

    def test_update_context_from_page_source(self, context_manager, mock_driver):
        """Test updating context from page source when capabilities fail."""
        mock_driver.get_driver.return_value.capabilities = {}
        # Mock the _get_current_package to return the expected value
        context_manager._get_current_package = lambda: 'com.example.app'

        package = context_manager.update_context()
        assert package == 'com.example.app'
        assert context_manager.current_package == 'com.example.app'

    def test_check_context_loss_no_loss(self, context_manager):
        """Test context loss check when in allowed package."""
        context_manager.current_package = 'com.example.target'
        assert not context_manager.check_context_loss()

    def test_check_context_loss_with_loss(self, context_manager):
        """Test context loss check when in disallowed package."""
        context_manager.current_package = 'com.other.app'
        assert context_manager.check_context_loss()

    def test_check_context_loss_none_current(self, context_manager):
        """Test context loss check when current package is None."""
        context_manager.current_package = None
        assert context_manager.check_context_loss()

    @patch('time.sleep')
    def test_handle_context_loss_back_recovery(self, mock_sleep, context_manager, mock_driver):
        """Test context loss recovery via back presses."""
        context_manager.current_package = 'com.other.app'

        # Mock back press success - after first back, we're back in app
        def mock_update():
            if mock_driver.get_driver.return_value.back.call_count == 1:
                context_manager.current_package = 'com.example.target'
            return context_manager.current_package

        context_manager.update_context = mock_update

        result = context_manager.handle_context_loss()

        assert result is True
        assert context_manager.context_loss_count == 1
        assert context_manager.context_recovery_count == 1
        assert mock_driver.get_driver.return_value.back.call_count == 1

    @patch('time.sleep')
    def test_handle_context_loss_relaunch_recovery(self, mock_sleep, context_manager, mock_driver):
        """Test context loss recovery via app relaunch."""
        context_manager.current_package = 'com.other.app'

        # Mock relaunch success
        def mock_update():
            if mock_driver.get_driver.return_value.launch_app.called:
                context_manager.current_package = 'com.example.target'
            return context_manager.current_package

        context_manager.update_context = mock_update

        result = context_manager.handle_context_loss()

        assert result is True
        assert context_manager.context_loss_count == 1
        assert context_manager.context_recovery_count == 1
        assert mock_driver.get_driver.return_value.back.call_count == 3  # All back presses tried
        assert mock_driver.get_driver.return_value.launch_app.called

    @patch('time.sleep')
    def test_handle_context_loss_failure(self, mock_sleep, context_manager, mock_driver):
        """Test context loss recovery failure."""
        context_manager.current_package = 'com.other.app'

        # Mock all recovery attempts failing
        context_manager.update_context = lambda: 'com.other.app'

        result = context_manager.handle_context_loss()

        assert result is False
        assert context_manager.context_loss_count == 1
        assert context_manager.context_recovery_count == 0
        assert mock_driver.get_driver.return_value.back.call_count == 3
        assert mock_driver.get_driver.return_value.launch_app.called

    def test_handle_context_loss_no_loss(self, context_manager):
        """Test handle context loss when no loss occurred."""
        context_manager.current_package = 'com.example.target'

        result = context_manager.handle_context_loss()

        assert result is True
        assert context_manager.context_loss_count == 0
        assert context_manager.context_recovery_count == 0

    def test_get_stats(self, context_manager):
        """Test getting statistics."""
        context_manager.context_loss_count = 5
        context_manager.context_recovery_count = 3
        context_manager.current_package = 'com.example.current'

        stats = context_manager.get_stats()

        expected = {
            'context_loss_count': 5,
            'context_recovery_count': 3,
            'current_package': 'com.example.current',
            'target_package': 'com.example.target',
            'allowed_packages': ['com.android.browser', 'com.example.target']
        }
        assert stats == expected