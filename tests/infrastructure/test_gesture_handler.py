"""Tests for gesture handler functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from selenium.common.exceptions import WebDriverException

from mobile_crawler.infrastructure.gesture_handler import (
    GestureHandler,
    GestureType
)
from mobile_crawler.infrastructure.appium_driver import AppiumDriver
from mobile_crawler.infrastructure.element_finder import UIElement


class TestGestureHandler:
    """Test GestureHandler class."""

    @pytest.fixture
    def mock_driver(self):
        """Create a mock AppiumDriver."""
        mock_appium_driver = Mock(spec=AppiumDriver)
        mock_webdriver = Mock()
        mock_appium_driver.get_driver.return_value = mock_webdriver
        return mock_appium_driver

    @pytest.fixture
    def gesture_handler(self, mock_driver):
        """Create GestureHandler instance."""
        return GestureHandler(mock_driver)

    @pytest.fixture
    def sample_element(self):
        """Create a sample UIElement."""
        return UIElement(
            element_id="test_id",
            bounds=(100, 200, 200, 250),
            text="Test Button",
            content_desc=None,
            class_name="android.widget.Button",
            package="com.example.app",
            clickable=True,
            visible=True,
            enabled=True,
            resource_id="com.example.app:id/button",
            xpath="//button[@text='Test Button']",
            center_x=150,
            center_y=225
        )

    def test_init(self, mock_driver):
        """Test initialization."""
        handler = GestureHandler(mock_driver)
        assert handler.driver == mock_driver

    @patch('mobile_crawler.infrastructure.gesture_handler.time.sleep')
    def test_tap_element_success(self, mock_sleep, gesture_handler, mock_driver, sample_element):
        """Test successful tap on element."""
        mock_webdriver_element = Mock()
        mock_webdriver_element.click = Mock()

        with patch.object(gesture_handler, '_get_webdriver_element', return_value=mock_webdriver_element):
            result = gesture_handler.tap(sample_element)

            assert result is True
            mock_webdriver_element.click.assert_called_once()
            mock_sleep.assert_called_once_with(0.1)

    @patch('mobile_crawler.infrastructure.gesture_handler.time.sleep')
    def test_tap_element_fallback(self, mock_sleep, gesture_handler, mock_driver, sample_element):
        """Test tap fallback to coordinates when element not found."""
        with patch.object(gesture_handler, '_get_webdriver_element', return_value=None):
            with patch.object(gesture_handler, 'tap_at', return_value=True) as mock_tap_at:
                result = gesture_handler.tap(sample_element)

                assert result is True
                mock_tap_at.assert_called_once_with(150, 225, 0.1)

    @patch('mobile_crawler.infrastructure.gesture_handler.time.sleep')
    def test_tap_at_success(self, mock_sleep, gesture_handler, mock_driver):
        """Test successful tap at coordinates."""
        # Mock the entire ActionChains to avoid complex mocking
        with patch('selenium.webdriver.common.action_chains.ActionChains') as mock_action_class:
            mock_instance = Mock()
            mock_action_class.return_value = mock_instance
            mock_instance.__enter__ = Mock(return_value=mock_instance)
            mock_instance.__exit__ = Mock(return_value=None)

            result = gesture_handler.tap_at(100, 200)

            assert result is True
            mock_sleep.assert_called_once_with(0.1)

    @patch('mobile_crawler.infrastructure.gesture_handler.time.sleep')
    def test_tap_at_failure(self, mock_sleep, gesture_handler, mock_driver):
        """Test tap at coordinates failure."""
        mock_driver.get_driver.return_value = Mock()
        mock_driver.get_driver.side_effect = WebDriverException("Test error")

        result = gesture_handler.tap_at(100, 200)
        assert result is False

    def test_double_tap_element_success(self, gesture_handler, mock_driver, sample_element):
        """Test successful double tap on element."""
        mock_webdriver_element = Mock()

        with patch.object(gesture_handler, '_get_webdriver_element', return_value=mock_webdriver_element):
            with patch('mobile_crawler.infrastructure.gesture_handler.ActionChains') as mock_action_class:
                mock_action_instance = Mock()
                mock_action_instance.double_click.return_value = mock_action_instance
                mock_action_class.return_value = mock_action_instance

                result = gesture_handler.double_tap(sample_element)

                assert result is True
                mock_action_class.assert_called_once()
                mock_action_instance.double_click.assert_called_once_with(mock_webdriver_element)
                mock_action_instance.perform.assert_called_once()

    def test_double_tap_element_fallback(self, gesture_handler, mock_driver, sample_element):
        """Test double tap fallback to coordinates."""
        with patch.object(gesture_handler, '_get_webdriver_element', return_value=None):
            with patch.object(gesture_handler, 'double_tap_at', return_value=True) as mock_double_tap_at:
                result = gesture_handler.double_tap(sample_element)

                assert result is True
                mock_double_tap_at.assert_called_once_with(150, 225)

    def test_double_tap_at_success(self, gesture_handler, mock_driver):
        """Test successful double tap at coordinates."""
        with patch('mobile_crawler.infrastructure.gesture_handler.ActionChains') as mock_action_class:
            mock_action_instance = Mock()
            mock_action_instance.move_by_offset.return_value = mock_action_instance
            mock_action_instance.double_click.return_value = mock_action_instance
            mock_action_class.return_value = mock_action_instance

            result = gesture_handler.double_tap_at(100, 200)

            assert result is True
            assert mock_action_instance.move_by_offset.call_count >= 1
            mock_action_instance.double_click.assert_called_once()
            mock_action_instance.perform.assert_called_once()

    @patch('mobile_crawler.infrastructure.gesture_handler.time.sleep')
    def test_long_press_element_success(self, mock_sleep, gesture_handler, mock_driver, sample_element):
        """Test successful long press on element."""
        mock_webdriver_element = Mock()

        with patch.object(gesture_handler, '_get_webdriver_element', return_value=mock_webdriver_element):
            with patch('mobile_crawler.infrastructure.gesture_handler.ActionChains') as mock_action_class:
                mock_action_instance = Mock()
                mock_action_instance.click_and_hold.return_value = mock_action_instance
                mock_action_instance.pause.return_value = mock_action_instance
                mock_action_instance.release.return_value = mock_action_instance
                mock_action_class.return_value = mock_action_instance

                result = gesture_handler.long_press(sample_element, 2.0)

                assert result is True
                mock_action_instance.click_and_hold.assert_called_once_with(mock_webdriver_element)
                mock_action_instance.pause.assert_called_once_with(2.0)
                mock_action_instance.release.assert_called_once()
                mock_action_instance.perform.assert_called_once()

    @patch('mobile_crawler.infrastructure.gesture_handler.time.sleep')
    def test_long_press_at_success(self, mock_sleep, gesture_handler, mock_driver):
        """Test successful long press at coordinates."""
        with patch('mobile_crawler.infrastructure.gesture_handler.ActionChains') as mock_action_class:
            mock_action_instance = Mock()
            mock_action_instance.move_by_offset.return_value = mock_action_instance
            mock_action_instance.click_and_hold.return_value = mock_action_instance
            mock_action_instance.pause.return_value = mock_action_instance
            mock_action_instance.release.return_value = mock_action_instance
            mock_action_class.return_value = mock_action_instance

            result = gesture_handler.long_press_at(100, 200, 1.5)

            assert result is True
            assert mock_action_instance.move_by_offset.call_count >= 1
            mock_action_instance.click_and_hold.assert_called_once()
            mock_action_instance.pause.assert_called_once_with(1.5)
            mock_action_instance.release.assert_called_once()
            mock_action_instance.perform.assert_called_once()

    @patch('mobile_crawler.infrastructure.gesture_handler.time.sleep')
    def test_swipe_success(self, mock_sleep, gesture_handler, mock_driver):
        """Test successful swipe."""
        with patch('mobile_crawler.infrastructure.gesture_handler.ActionChains') as mock_action_class:
            mock_action_instance = Mock()
            mock_action_instance.move_by_offset.return_value = mock_action_instance
            mock_action_instance.click_and_hold.return_value = mock_action_instance
            mock_action_instance.pause.return_value = mock_action_instance
            mock_action_instance.release.return_value = mock_action_instance
            mock_action_class.return_value = mock_action_instance

            result = gesture_handler.swipe(100, 200, 300, 400, 0.5)

            assert result is True
            # Verify the action chain calls
            assert mock_action_instance.move_by_offset.call_count >= 1
            mock_action_instance.click_and_hold.assert_called_once()
            mock_action_instance.pause.assert_called_once_with(0.1)
            mock_action_instance.release.assert_called_once()
            mock_action_instance.perform.assert_called_once()
            mock_sleep.assert_called_once_with(0.5)

    @patch('mobile_crawler.infrastructure.gesture_handler.time.sleep')
    def test_drag_element_success(self, mock_sleep, gesture_handler, mock_driver, sample_element):
        """Test successful drag of element."""
        mock_webdriver_element = Mock()

        with patch.object(gesture_handler, '_get_webdriver_element', return_value=mock_webdriver_element):
            with patch('mobile_crawler.infrastructure.gesture_handler.ActionChains') as mock_action_class:
                mock_action_instance = Mock()
                mock_action_instance.drag_and_drop_by_offset.return_value = mock_action_instance
                mock_action_class.return_value = mock_action_instance

                result = gesture_handler.drag(sample_element, 300, 400)

                assert result is True
                mock_action_instance.drag_and_drop_by_offset.assert_called_once_with(
                    mock_webdriver_element, 150, 175  # 300-150, 400-225
                )
                mock_action_instance.perform.assert_called_once()
                mock_sleep.assert_called_once_with(0.5)

    @patch('mobile_crawler.infrastructure.gesture_handler.time.sleep')
    def test_drag_from_to_success(self, mock_sleep, gesture_handler, mock_driver):
        """Test successful drag from coordinates to coordinates."""
        with patch('mobile_crawler.infrastructure.gesture_handler.ActionChains') as mock_action_class:
            mock_action_instance = Mock()
            mock_action_instance.move_by_offset.return_value = mock_action_instance
            mock_action_instance.click_and_hold.return_value = mock_action_instance
            mock_action_instance.pause.return_value = mock_action_instance
            mock_action_instance.release.return_value = mock_action_instance
            mock_action_class.return_value = mock_action_instance

            result = gesture_handler.drag_from_to(100, 200, 300, 400)

            assert result is True
            assert mock_action_instance.move_by_offset.call_count >= 1
            mock_action_instance.click_and_hold.assert_called_once()
            mock_action_instance.pause.assert_called_once_with(0.1)
            mock_action_instance.release.assert_called_once()
            mock_action_instance.perform.assert_called_once()
            mock_sleep.assert_called_once_with(0.5)

    def test_scroll_up(self, gesture_handler, mock_driver):
        """Test scroll up."""
        mock_driver.get_driver.return_value.get_window_size.return_value = {'width': 1080, 'height': 1920}

        with patch.object(gesture_handler, 'swipe', return_value=True) as mock_swipe:
            result = gesture_handler.scroll('up', 300)

            assert result is True
            # Should swipe from center down to center up
            mock_swipe.assert_called_once_with(540, 960, 540, 660, 0.5)

    def test_scroll_down(self, gesture_handler, mock_driver):
        """Test scroll down."""
        mock_driver.get_driver.return_value.get_window_size.return_value = {'width': 1080, 'height': 1920}

        with patch.object(gesture_handler, 'swipe', return_value=True) as mock_swipe:
            result = gesture_handler.scroll('down', 300)

            assert result is True
            mock_swipe.assert_called_once_with(540, 960, 540, 1260, 0.5)

    def test_scroll_left(self, gesture_handler, mock_driver):
        """Test scroll left."""
        mock_driver.get_driver.return_value.get_window_size.return_value = {'width': 1080, 'height': 1920}

        with patch.object(gesture_handler, 'swipe', return_value=True) as mock_swipe:
            result = gesture_handler.scroll('left', 300)

            assert result is True
            mock_swipe.assert_called_once_with(540, 960, 240, 960, 0.5)

    def test_scroll_right(self, gesture_handler, mock_driver):
        """Test scroll right."""
        mock_driver.get_driver.return_value.get_window_size.return_value = {'width': 1080, 'height': 1920}

        with patch.object(gesture_handler, 'swipe', return_value=True) as mock_swipe:
            result = gesture_handler.scroll('right', 300)

            assert result is True
            mock_swipe.assert_called_once_with(540, 960, 840, 960, 0.5)

    def test_scroll_invalid_direction(self, gesture_handler, mock_driver):
        """Test scroll with invalid direction."""
        result = gesture_handler.scroll('invalid')
        assert result is False

    def test_pinch_zoom_out(self, gesture_handler, mock_driver):
        """Test pinch zoom out."""
        mock_driver.get_driver.return_value.get_window_size.return_value = {'width': 1080, 'height': 1920}

        with patch.object(gesture_handler, 'drag_from_to', return_value=True) as mock_drag:
            result = gesture_handler.pinch(500, 500, 0.5)

            assert result is True
            mock_drag.assert_called_once()

    @patch('mobile_crawler.infrastructure.gesture_handler.time.sleep')
    def test_wait_for_element_interaction_success(self, mock_sleep, gesture_handler, mock_driver, sample_element):
        """Test waiting for element interaction when element is ready."""
        mock_webdriver_element = Mock()
        mock_webdriver_element.is_displayed.return_value = True
        mock_webdriver_element.is_enabled.return_value = True

        with patch.object(gesture_handler, '_get_webdriver_element', return_value=mock_webdriver_element):
            result = gesture_handler.wait_for_element_interaction(sample_element, 1.0)

            assert result is True

    @patch('mobile_crawler.infrastructure.gesture_handler.time.sleep')
    def test_wait_for_element_interaction_timeout(self, mock_sleep, gesture_handler, mock_driver, sample_element):
        """Test waiting for element interaction times out."""
        with patch.object(gesture_handler, '_get_webdriver_element', return_value=None):
            result = gesture_handler.wait_for_element_interaction(sample_element, 0.5)

            assert result is False
            # Should have slept multiple times
            assert mock_sleep.call_count > 1

    def test_get_webdriver_element_by_resource_id(self, gesture_handler, mock_driver, sample_element):
        """Test getting webdriver element by resource ID."""
        mock_found_element = Mock()
        mock_driver.get_driver.return_value.find_element.return_value = mock_found_element

        with patch.object(gesture_handler, '_elements_match', return_value=True):
            result = gesture_handler._get_webdriver_element(sample_element)

            assert result == mock_found_element
            mock_driver.get_driver.return_value.find_element.assert_called_with(
                'id', 'com.example.app:id/button'
            )

    def test_get_webdriver_element_not_found(self, gesture_handler, mock_driver, sample_element):
        """Test webdriver element not found."""
        from selenium.common.exceptions import NoSuchElementException
        mock_driver.get_driver.return_value.find_element.side_effect = NoSuchElementException()

        result = gesture_handler._get_webdriver_element(sample_element)

        assert result is None

    def test_elements_match(self, gesture_handler, sample_element):
        """Test element matching."""
        mock_webdriver_element = Mock()
        mock_webdriver_element.location = {'x': 100, 'y': 200}
        mock_webdriver_element.size = {'width': 100, 'height': 50}

        result = gesture_handler._elements_match(sample_element, mock_webdriver_element)

        assert result is True

    def test_elements_match_outside_tolerance(self, gesture_handler, sample_element):
        """Test element matching outside tolerance."""
        mock_webdriver_element = Mock()
        mock_webdriver_element.location = {'x': 150, 'y': 250}  # Way off
        mock_webdriver_element.size = {'width': 100, 'height': 50}

        result = gesture_handler._elements_match(sample_element, mock_webdriver_element)

        assert result is False

    def test_bounds_match(self, gesture_handler):
        """Test bounds matching."""
        bounds1 = (100, 200, 200, 250)
        bounds2 = (105, 205, 205, 255)  # Within tolerance of 10

        result = gesture_handler._bounds_match(bounds1, bounds2, 10)
        assert result is True

        bounds3 = (150, 250, 250, 300)  # Outside tolerance
        result = gesture_handler._bounds_match(bounds1, bounds3, 10)
        assert result is False