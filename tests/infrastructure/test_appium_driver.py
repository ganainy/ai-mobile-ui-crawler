"""Tests for AppiumDriver."""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from appium.webdriver.webdriver import WebDriver

from mobile_crawler.infrastructure.appium_driver import AppiumDriver, AppiumDriverError, SessionLostError


class TestAppiumDriver:
    """Test suite for AppiumDriver."""

    @patch('mobile_crawler.infrastructure.appium_driver.webdriver')
    @patch('mobile_crawler.config.get_config')
    def test_connect_success(self, mock_get_config, mock_webdriver):
        """Test successful connection to Appium."""
        # Mock configuration
        mock_config = {
            'appium_url': 'http://localhost:4723',
            'appium_connection_timeout': 30,
            'appium_implicit_wait': 10
        }
        mock_get_config.return_value.get.side_effect = lambda key, default: mock_config.get(key, default)

        # Mock WebDriver
        mock_driver = Mock(spec=WebDriver)
        mock_webdriver.Remote.return_value = mock_driver

        # Test connection
        driver = AppiumDriver('emulator-5554', 'com.example.app')
        result = driver.connect()

        assert result == mock_driver
        assert driver._driver == mock_driver
        assert driver._session_start_time is not None

        # Verify WebDriver was created with correct parameters
        mock_webdriver.Remote.assert_called_once()
        call_args = mock_webdriver.Remote.call_args
        assert call_args[1]['command_executor'] == 'http://localhost:4723'

        # Verify options were set
        options = call_args[1]['options']
        assert options.platform_name == 'Android'
        assert options.device_name == 'emulator-5554'
        assert options.automation_name == 'UIAutomator2'
        assert options.app_package == 'com.example.app'
        assert options.no_reset is True
        assert options.full_reset is False

        # Verify implicit wait was set
        mock_driver.implicitly_wait.assert_called_once_with(10)

    @patch('mobile_crawler.infrastructure.appium_driver.webdriver')
    @patch('mobile_crawler.config.get_config')
    def test_connect_failure(self, mock_get_config, mock_webdriver):
        """Test connection failure."""
        mock_get_config.return_value.get.side_effect = lambda key, default: default
        mock_webdriver.Remote.side_effect = Exception("Connection refused")

        driver = AppiumDriver('emulator-5554')

        with pytest.raises(AppiumDriverError, match="Failed to connect to Appium"):
            driver.connect()

    def test_disconnect(self):
        """Test disconnecting from Appium."""
        driver = AppiumDriver('emulator-5554')
        mock_webdriver = Mock(spec=WebDriver)
        driver._driver = mock_webdriver
        driver._session_start_time = 1234567890.0

        driver.disconnect()

        mock_webdriver.quit.assert_called_once()
        assert driver._driver is None
        assert driver._session_start_time is None

    def test_disconnect_no_driver(self):
        """Test disconnecting when no driver exists."""
        driver = AppiumDriver('emulator-5554')
        driver.disconnect()  # Should not raise

    def test_get_driver_success(self):
        """Test getting driver when connected."""
        driver = AppiumDriver('emulator-5554')
        mock_webdriver = Mock(spec=WebDriver)
        driver._driver = mock_webdriver

        result = driver.get_driver()
        assert result == mock_webdriver

    def test_get_driver_no_session(self):
        """Test getting driver when not connected."""
        driver = AppiumDriver('emulator-5554')

        with pytest.raises(SessionLostError, match="No active Appium session"):
            driver.get_driver()

    def test_is_connected_true(self):
        """Test connection check when connected."""
        driver = AppiumDriver('emulator-5554')
        mock_webdriver = Mock(spec=WebDriver)
        mock_webdriver.current_activity = "com.example.MainActivity"
        driver._driver = mock_webdriver

        assert driver.is_connected() is True

    def test_is_connected_false_no_driver(self):
        """Test connection check when no driver."""
        driver = AppiumDriver('emulator-5554')
        assert driver.is_connected() is False

    def test_is_connected_false_session_dead(self):
        """Test connection check when session is dead."""
        driver = AppiumDriver('emulator-5554')
        mock_webdriver = Mock(spec=WebDriver)
        # Mock current_activity property to raise exception
        type(mock_webdriver).current_activity = PropertyMock(side_effect=Exception("Session expired"))
        driver._driver = mock_webdriver

        assert driver.is_connected() is False
        assert driver._driver is None  # Should be cleaned up

    @patch('mobile_crawler.infrastructure.appium_driver.webdriver')
    @patch('mobile_crawler.config.get_config')
    def test_reconnect(self, mock_get_config, mock_webdriver):
        """Test reconnection."""
        mock_get_config.return_value.get.side_effect = lambda key, default: default
        mock_driver = Mock(spec=WebDriver)
        mock_webdriver.Remote.return_value = mock_driver

        driver = AppiumDriver('emulator-5554')
        # Simulate existing dead driver
        old_driver = Mock()
        driver._driver = old_driver

        result = driver.reconnect()

        assert result == mock_driver
        # Should have quit old driver
        old_driver.quit.assert_called_once()

    @patch('mobile_crawler.infrastructure.appium_driver.webdriver')
    @patch('mobile_crawler.config.get_config')
    def test_ensure_connected_reconnect_needed(self, mock_get_config, mock_webdriver):
        """Test ensure_connected when reconnection is needed."""
        mock_get_config.return_value.get.side_effect = lambda key, default: default
        mock_driver = Mock(spec=WebDriver)
        mock_webdriver.Remote.return_value = mock_driver

        driver = AppiumDriver('emulator-5554')
        # No initial driver

        result = driver.ensure_connected()

        assert result == mock_driver
        mock_webdriver.Remote.assert_called_once()

    def test_ensure_connected_already_connected(self):
        """Test ensure_connected when already connected."""
        driver = AppiumDriver('emulator-5554')
        mock_webdriver = Mock(spec=WebDriver)
        mock_webdriver.current_activity = "com.example.MainActivity"
        driver._driver = mock_webdriver

        result = driver.ensure_connected()

        assert result == mock_webdriver

    def test_get_session_info_connected(self):
        """Test getting session info when connected."""
        import time
        start_time = time.time()

        driver = AppiumDriver('emulator-5554', 'com.example.app')
        mock_webdriver = Mock(spec=WebDriver)
        mock_webdriver.current_activity = "com.example.MainActivity"
        mock_webdriver.current_package = "com.example.app"
        mock_webdriver.device_time = "2024-01-10T12:00:00Z"
        driver._driver = mock_webdriver
        driver._session_start_time = start_time

        info = driver.get_session_info()

        expected_keys = {
            'device_id', 'app_package', 'connected', 'session_duration',
            'current_activity', 'current_package', 'device_time'
        }
        assert set(info.keys()) == expected_keys
        assert info['device_id'] == 'emulator-5554'
        assert info['app_package'] == 'com.example.app'
        assert info['connected'] is True
        assert info['session_duration'] >= 0
        assert info['current_activity'] == 'com.example.MainActivity'
        assert info['current_package'] == 'com.example.app'

    def test_get_session_info_not_connected(self):
        """Test getting session info when not connected."""
        driver = AppiumDriver('emulator-5554')

        info = driver.get_session_info()

        assert info['connected'] is False
        assert info['session_duration'] is None
        assert 'current_activity' not in info

    def test_context_manager(self):
        """Test context manager usage."""
        with patch('mobile_crawler.infrastructure.appium_driver.webdriver') as mock_webdriver, \
             patch('mobile_crawler.config.get_config') as mock_get_config:

            mock_get_config.return_value.get.side_effect = lambda key, default: default
            mock_driver = Mock(spec=WebDriver)
            mock_webdriver.Remote.return_value = mock_driver

            driver = AppiumDriver('emulator-5554')

            with driver as d:
                assert d == mock_driver

            # Should have quit on exit
            mock_driver.quit.assert_called_once()

    def test_get_launch_activity(self):
        """Test launch activity determination."""
        driver = AppiumDriver('emulator-5554', 'com.example.app')
        activity = driver._get_launch_activity()
        assert activity == 'com.example.app.MainActivity'