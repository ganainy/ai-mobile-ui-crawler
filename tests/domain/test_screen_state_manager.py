"""Tests for screen state manager."""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from mobile_crawler.domain.screen_state_manager import (
    ScreenStateManager, ScreenState, ScreenSnapshot
)
from mobile_crawler.infrastructure.appium_driver import AppiumDriver
from mobile_crawler.infrastructure.screenshot_capture import ScreenshotCapture


class TestScreenStateManager:
    """Test cases for ScreenStateManager."""

    @pytest.fixture
    def mock_appium_driver(self):
        """Create mock AppiumDriver."""
        driver = Mock(spec=AppiumDriver)
        mock_webdriver = Mock()
        mock_webdriver.get_window_size.return_value = {'width': 1080, 'height': 1920}
        mock_webdriver.current_activity = 'com.example.TestActivity'
        mock_webdriver.current_package = 'com.example'
        driver.get_driver.return_value = mock_webdriver
        return driver

    @pytest.fixture
    def mock_screenshot_capture(self):
        """Create mock ScreenshotCapture."""
        capture = Mock(spec=ScreenshotCapture)
        capture.capture_screenshot_to_file.return_value = '/tmp/screenshot_123.png'
        # Basic attributes needed by ScreenStateManager if it accessed them
        capture.output_dir = Path('/tmp')
        return capture

    @pytest.fixture
    def screen_state_manager(self, mock_appium_driver, mock_screenshot_capture):
        """Create ScreenStateManager with mocks."""
        return ScreenStateManager(
            appium_driver=mock_appium_driver,
            screenshot_capture=mock_screenshot_capture
        )

    def test_initialization(self, mock_appium_driver):
        """Test ScreenStateManager initialization."""
        # Use mocked ScreenshotCapture implicitly created inside if not provided, 
        # but here we want to test the constructor's default behavior or explicit injection.
        # If we rely on default behavior, we must mock ScreenshotCapture class or pass a mock.
        
        # Test explicit injection which is what the fixture does
        mock_capture = Mock(spec=ScreenshotCapture)
        manager = ScreenStateManager(mock_appium_driver, screenshot_capture=mock_capture)

        assert manager.driver == mock_appium_driver
        # The manager sets its own capture if None provided
        assert manager.screenshot_capture == mock_capture
        assert manager.current_state == ScreenState.UNKNOWN
        assert manager.previous_state == ScreenState.UNKNOWN
        assert len(manager.state_history) == 0
        assert manager.max_history_size == 10

    def test_get_current_state(self, screen_state_manager):
        """Test getting current state."""
        assert screen_state_manager.get_current_state() == ScreenState.UNKNOWN

        screen_state_manager.current_state = ScreenState.READY
        assert screen_state_manager.get_current_state() == ScreenState.READY

    def test_detect_screen_state_default(self, screen_state_manager):
        """Test screen state detection defaults to READY in Image-Only mode."""
        state = screen_state_manager.detect_screen_state()
        assert state == ScreenState.READY

    def test_take_snapshot(self, screen_state_manager):
        """Test taking screen snapshot."""
        snapshot = screen_state_manager.take_snapshot(include_screenshot=True)

        assert isinstance(snapshot, ScreenSnapshot)
        assert snapshot.screenshot_path == '/tmp/screenshot_123.png'
        # Elements removed
        assert not hasattr(snapshot, 'elements') or snapshot.elements is None or snapshot.elements == []
        assert snapshot.screen_state == ScreenState.READY
        assert snapshot.activity_name == 'com.example.TestActivity'
        assert snapshot.package_name == 'com.example'
        assert snapshot.screen_bounds == (0, 0, 1080, 1920)
        assert snapshot.metadata['image_only_mode'] is True

        # Check history
        assert len(screen_state_manager.state_history) == 1

    def test_take_snapshot_no_screenshot(self, screen_state_manager):
        """Test taking snapshot without screenshot."""
        snapshot = screen_state_manager.take_snapshot(include_screenshot=False)

        assert snapshot.screenshot_path is None
        assert len(screen_state_manager.state_history) == 1

    def test_wait_for_state_success(self, screen_state_manager):
        """Test waiting for state - success case."""
        result = screen_state_manager.wait_for_state(ScreenState.READY, timeout=1.0)
        assert result is True

    def test_wait_for_state_timeout(self, screen_state_manager):
        """Test waiting for state - timeout case (waiting for something other than READY)."""
        # Since logic defaults to READY, waiting for ERROR will timeout
        result = screen_state_manager.wait_for_state(ScreenState.ERROR, timeout=0.1)
        assert result is False

    def test_wait_for_stable_screen_success(self, screen_state_manager):
        """Test waiting for stable screen - success case."""
        # Mock calculate_screenshot_similarity to return high similarity
        screen_state_manager._calculate_screenshot_similarity = Mock(return_value=1.0)

        result = screen_state_manager.wait_for_stable_screen(stability_duration=0.1, timeout=1.0)
        assert result is True

    def test_wait_for_stable_screen_timeout(self, screen_state_manager):
        """Test waiting for stable screen - timeout case."""
        # Mock calculate_screenshot_similarity to return low similarity
        screen_state_manager._calculate_screenshot_similarity = Mock(return_value=0.0)

        result = screen_state_manager.wait_for_stable_screen(stability_duration=0.1, timeout=0.2)
        assert result is False

    def test_get_state_history(self, screen_state_manager):
        """Test getting state history."""
        # Take a snapshot
        screen_state_manager.take_snapshot()

        history = screen_state_manager.get_state_history()
        assert len(history) == 1
        assert isinstance(history[0], ScreenSnapshot)

    def test_clear_history(self, screen_state_manager):
        """Test clearing state history."""
        screen_state_manager.take_snapshot()
        assert len(screen_state_manager.state_history) == 1

        screen_state_manager.clear_history()
        assert len(screen_state_manager.state_history) == 0