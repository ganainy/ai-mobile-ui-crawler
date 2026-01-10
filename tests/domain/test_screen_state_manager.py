"""Tests for screen state manager."""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from mobile_crawler.domain.screen_state_manager import (
    ScreenStateManager, ScreenState, ScreenSnapshot
)
from mobile_crawler.infrastructure.appium_driver import AppiumDriver
from mobile_crawler.infrastructure.element_finder import ElementFinder, UIElement
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
    def mock_element_finder(self):
        """Create mock ElementFinder."""
        finder = Mock(spec=ElementFinder)

        # Mock elements
        elements = [
            UIElement(
                element_id='1',
                bounds=(0, 0, 100, 50),
                text='Click Me',
                content_desc='',
                class_name='android.widget.Button',
                package='com.example',
                clickable=True,
                visible=True,
                enabled=True,
                resource_id='btn_click',
                xpath='//button[@text="Click Me"]',
                center_x=50,
                center_y=25
            ),
            UIElement(
                element_id='2',
                bounds=(0, 60, 100, 110),
                text='',
                content_desc='',
                class_name='android.widget.EditText',
                package='com.example',
                clickable=True,
                visible=True,
                enabled=True,
                resource_id='edit_text',
                xpath='//editText[@id="edit_text"]',
                center_x=50,
                center_y=85
            )
        ]

        finder.get_all_elements.return_value = elements
        finder.find_elements_containing_text.return_value = []
        finder.find_elements_by_class.return_value = []
        finder.find_clickable_elements.return_value = elements[:1]
        return finder

    @pytest.fixture
    def mock_screenshot_capture(self):
        """Create mock ScreenshotCapture."""
        capture = Mock(spec=ScreenshotCapture)
        capture.capture_screenshot_to_file.return_value = '/tmp/screenshot_123.png'
        return capture

    @pytest.fixture
    def screen_state_manager(self, mock_appium_driver, mock_element_finder, mock_screenshot_capture):
        """Create ScreenStateManager with mocks."""
        return ScreenStateManager(
            appium_driver=mock_appium_driver,
            element_finder=mock_element_finder,
            screenshot_capture=mock_screenshot_capture
        )

    def test_initialization(self, mock_appium_driver):
        """Test ScreenStateManager initialization."""
        manager = ScreenStateManager(mock_appium_driver)

        assert manager.driver == mock_appium_driver
        assert manager.current_state == ScreenState.UNKNOWN
        assert manager.previous_state == ScreenState.UNKNOWN
        assert len(manager.state_history) == 0
        assert manager.max_history_size == 10

    def test_get_current_state(self, screen_state_manager):
        """Test getting current state."""
        assert screen_state_manager.get_current_state() == ScreenState.UNKNOWN

        screen_state_manager.current_state = ScreenState.READY
        assert screen_state_manager.get_current_state() == ScreenState.READY

    def test_detect_screen_state_ready(self, screen_state_manager, mock_element_finder):
        """Test screen state detection for ready state."""
        # Configure mocks for ready state
        mock_element_finder.get_all_elements.return_value = [
            UIElement('1', (0, 0, 100, 50), 'Ready', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25),
            UIElement('2', (0, 60, 100, 110), 'Text', '', 'text', 'com.example', False, True, True, 'txt', '//txt', 50, 85),
            UIElement('3', (0, 120, 100, 170), 'More', '', 'view', 'com.example', False, True, True, 'view', '//view', 50, 145)
        ]
        mock_element_finder.find_elements_containing_text.return_value = []
        mock_element_finder.find_elements_by_class.return_value = []
        mock_element_finder.find_clickable_elements.return_value = [
            UIElement('1', (0, 0, 100, 50), 'Ready', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25)
        ]

        state = screen_state_manager.detect_screen_state()
        assert state == ScreenState.READY

    def test_detect_screen_state_loading(self, screen_state_manager, mock_element_finder):
        """Test screen state detection for loading state."""
        # Configure mocks for loading state
        mock_element_finder.get_all_elements.return_value = [
            UIElement('1', (0, 0, 100, 50), 'Loading...', '', 'text', 'com.example', True, True, True, '', '//text', 50, 25)
        ]
        mock_element_finder.find_elements_containing_text.return_value = [
            UIElement('1', (0, 0, 100, 50), 'Loading...', '', 'text', 'com.example', True, True, True, '', '//text', 50, 25)
        ]
        mock_element_finder.find_elements_by_class.return_value = []
        mock_element_finder.find_clickable_elements.return_value = []

        state = screen_state_manager.detect_screen_state()
        assert state == ScreenState.LOADING

    def test_detect_screen_state_error(self, screen_state_manager):
        """Test screen state detection for error state."""
        # Create fresh mock for this test
        mock_finder = Mock(spec=ElementFinder)
        screen_state_manager.element_finder = mock_finder

        # Configure mocks for error state
        def mock_find_elements_containing_text(keywords, **kwargs):
            if any(word in ' '.join(keywords).lower() for word in ['error', 'failed', 'sorry', 'problem', 'crash']):
                return [UIElement('1', (0, 0, 100, 50), 'Error occurred', '', 'text', 'com.example', True, True, True, '', '//text', 50, 25)]
            return []

        mock_finder.get_all_elements.return_value = [
            UIElement('1', (0, 0, 100, 50), 'Error occurred', '', 'text', 'com.example', True, True, True, '', '//text', 50, 25),
            UIElement('2', (0, 60, 100, 110), 'Some text', '', 'text', 'com.example', False, True, True, 'txt', '//txt', 50, 85),
            UIElement('3', (0, 120, 100, 170), 'More text', '', 'view', 'com.example', False, True, True, 'view', '//view', 50, 145)
        ]
        mock_finder.find_elements_containing_text.side_effect = mock_find_elements_containing_text
        mock_finder.find_elements_by_class.return_value = []
        mock_finder.find_clickable_elements.return_value = []

        state = screen_state_manager.detect_screen_state()
        assert state == ScreenState.ERROR

    def test_take_snapshot(self, screen_state_manager):
        """Test taking screen snapshot."""
        # Create fresh mock for this test
        mock_finder = Mock(spec=ElementFinder)
        screen_state_manager.element_finder = mock_finder

        # Configure mocks for ready state
        def mock_find_elements_containing_text(keywords, **kwargs):
            # Return empty for loading keywords, error keywords, etc.
            return []

        mock_finder.get_all_elements.return_value = [
            UIElement('1', (0, 0, 100, 50), 'Ready', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25),
            UIElement('2', (0, 60, 100, 110), 'Text', '', 'text', 'com.example', False, True, True, 'txt', '//txt', 50, 85),
            UIElement('3', (0, 120, 100, 170), 'More', '', 'view', 'com.example', False, True, True, 'view', '//view', 50, 145)
        ]
        mock_finder.find_elements_containing_text.side_effect = mock_find_elements_containing_text
        mock_finder.find_elements_by_class.return_value = []
        mock_finder.find_clickable_elements.return_value = [
            UIElement('1', (0, 0, 100, 50), 'Ready', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25)
        ]

        snapshot = screen_state_manager.take_snapshot(include_screenshot=True)

        assert isinstance(snapshot, ScreenSnapshot)
        assert snapshot.screenshot_path == '/tmp/screenshot_123.png'
        assert len(snapshot.elements) == 3
        assert snapshot.screen_state == ScreenState.READY
        assert snapshot.activity_name == 'com.example.TestActivity'
        assert snapshot.package_name == 'com.example'
        assert snapshot.screen_bounds == (0, 0, 1080, 1920)
        assert 'element_count' in snapshot.metadata

        # Check history
        assert len(screen_state_manager.state_history) == 1

    def test_take_snapshot_no_screenshot(self, screen_state_manager):
        """Test taking snapshot without screenshot."""
        snapshot = screen_state_manager.take_snapshot(include_screenshot=False)

        assert snapshot.screenshot_path is None
        assert len(screen_state_manager.state_history) == 1

    def test_wait_for_state_success(self, screen_state_manager, mock_element_finder):
        """Test waiting for state - success case."""
        # Configure mocks to return ready state
        mock_element_finder.get_all_elements.return_value = [
            UIElement('1', (0, 0, 100, 50), 'Ready', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25),
            UIElement('2', (0, 60, 100, 110), 'Text', '', 'text', 'com.example', False, True, True, 'txt', '//txt', 50, 85),
            UIElement('3', (0, 120, 100, 170), 'More', '', 'view', 'com.example', False, True, True, 'view', '//view', 50, 145)
        ]
        mock_element_finder.find_elements_containing_text.return_value = []
        mock_element_finder.find_elements_by_class.return_value = []
        mock_element_finder.find_clickable_elements.return_value = [
            UIElement('1', (0, 0, 100, 50), 'Ready', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25)
        ]

        result = screen_state_manager.wait_for_state(ScreenState.READY, timeout=1.0)
        assert result is True

    def test_wait_for_state_timeout(self, screen_state_manager):
        """Test waiting for state - timeout case."""
        screen_state_manager.current_state = ScreenState.LOADING

        result = screen_state_manager.wait_for_state(ScreenState.READY, timeout=0.1)
        assert result is False

    def test_wait_for_stable_screen_success(self, screen_state_manager, mock_element_finder):
        """Test waiting for stable screen - success case."""
        # Mock stable elements
        stable_elements = [
            UIElement('1', (0, 0, 100, 50), 'Stable', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25)
        ]
        mock_element_finder.get_all_elements.side_effect = [stable_elements, stable_elements]

        result = screen_state_manager.wait_for_stable_screen(stability_duration=0.1, timeout=1.0)
        assert result is True

    def test_wait_for_stable_screen_timeout(self, screen_state_manager, mock_element_finder):
        """Test waiting for stable screen - timeout case."""
        # Mock changing elements
        changing_elements1 = [
            UIElement('1', (0, 0, 100, 50), 'Changing1', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25)
        ]
        changing_elements2 = [
            UIElement('1', (0, 0, 100, 50), 'Changing2', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25)
        ]
        mock_element_finder.get_all_elements.side_effect = [changing_elements1, changing_elements2]

        result = screen_state_manager.wait_for_stable_screen(stability_duration=0.1, timeout=0.2)
        assert result is False

    def test_compare_snapshots(self, screen_state_manager):
        """Test comparing snapshots."""
        snapshot1 = ScreenSnapshot(
            timestamp=1000.0,
            screenshot_path='/tmp/s1.png',
            elements=[UIElement('1', (0, 0, 100, 50), 'Test', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25)],
            screen_state=ScreenState.READY,
            activity_name='com.example.Main',
            package_name='com.example',
            screen_bounds=(0, 0, 1080, 1920),
            metadata={}
        )

        snapshot2 = ScreenSnapshot(
            timestamp=1005.0,
            screenshot_path='/tmp/s2.png',
            elements=[UIElement('1', (0, 0, 100, 50), 'Test', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25)],
            screen_state=ScreenState.READY,
            activity_name='com.example.Main',
            package_name='com.example',
            screen_bounds=(0, 0, 1080, 1920),
            metadata={}
        )

        comparison = screen_state_manager.compare_snapshots(snapshot1, snapshot2)

        assert comparison['time_diff'] == 5.0
        assert comparison['state_changed'] is False
        assert comparison['element_count_diff'] == 0
        assert comparison['activity_changed'] is False
        assert comparison['element_similarity'] == 1.0

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

    def test_get_screen_bounds(self, screen_state_manager):
        """Test getting screen bounds."""
        bounds = screen_state_manager._get_screen_bounds()
        assert bounds == (0, 0, 1080, 1920)

    def test_get_current_activity(self, screen_state_manager):
        """Test getting current activity."""
        activity = screen_state_manager._get_current_activity()
        assert activity == 'com.example.TestActivity'

    def test_get_current_package(self, screen_state_manager):
        """Test getting current package."""
        package = screen_state_manager._get_current_package()
        assert package == 'com.example'

    def test_calculate_element_similarity(self, screen_state_manager):
        """Test element similarity calculation."""
        elements1 = [
            UIElement('1', (0, 0, 100, 50), 'Test', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25)
        ]
        elements2 = [
            UIElement('1', (0, 0, 100, 50), 'Test', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25)
        ]

        similarity = screen_state_manager._calculate_element_similarity(elements1, elements2)
        assert similarity == 1.0

        # Test with different elements
        elements3 = [
            UIElement('2', (200, 200, 300, 250), 'Different', '', 'text', 'com.example', True, True, True, 'txt', '//txt', 250, 225)
        ]
        similarity = screen_state_manager._calculate_element_similarity(elements1, elements3)
        assert similarity == 0.0

    def test_elements_similar(self, screen_state_manager):
        """Test element similarity check."""
        elem1 = UIElement('1', (0, 0, 100, 50), 'Test', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25)
        elem2 = UIElement('1', (0, 0, 100, 50), 'Test', '', 'button', 'com.example', True, True, True, 'btn', '//btn', 50, 25)
        elem3 = UIElement('2', (200, 200, 300, 250), 'Different', '', 'text', 'com.example', True, True, True, 'txt', '//txt', 250, 225)

        assert screen_state_manager._elements_similar(elem1, elem2) is True
        assert screen_state_manager._elements_similar(elem1, elem3) is False

    def test_error_handling_in_state_detection(self, screen_state_manager, mock_element_finder):
        """Test error handling in state detection."""
        # Configure mocks to raise exception
        mock_element_finder.get_all_elements.side_effect = Exception("Test error")
        mock_element_finder.find_elements_containing_text.side_effect = Exception("Test error")
        mock_element_finder.find_elements_by_class.side_effect = Exception("Test error")
        mock_element_finder.find_clickable_elements.side_effect = Exception("Test error")

        state = screen_state_manager.detect_screen_state()
        assert state == ScreenState.UNKNOWN

    def test_error_handling_in_snapshot(self, screen_state_manager, mock_element_finder):
        """Test error handling in snapshot taking."""
        mock_element_finder.get_all_elements.side_effect = Exception("Test error")

        snapshot = screen_state_manager.take_snapshot()
        assert snapshot.screen_state == ScreenState.ERROR
        assert 'error' in snapshot.metadata

    def test_history_size_limit(self, screen_state_manager):
        """Test history size limiting."""
        screen_state_manager.max_history_size = 2

        # Take multiple snapshots
        for i in range(4):
            screen_state_manager.take_snapshot()

        assert len(screen_state_manager.state_history) == 2