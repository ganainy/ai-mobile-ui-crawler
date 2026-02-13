"""Tests for action executor."""

from unittest.mock import MagicMock, Mock

import pytest

from mobile_crawler.domain.action_executor import ActionExecutor
from mobile_crawler.domain.models import ActionResult


class TestActionExecutor:
    """Test ActionExecutor."""

    @pytest.fixture
    def mock_driver(self):
        """Mock AppiumDriver."""
        driver = Mock()
        window_size = {'width': 1080, 'height': 1920}
        driver.get_window_size.return_value = window_size
        driver.back = Mock()
        driver.find_element_by_xpath = Mock()
        driver.press_keycode = Mock()

        appium_driver = Mock()
        appium_driver.get_driver.return_value = driver
        return appium_driver

    @pytest.fixture
    def mock_gesture_handler(self):
        """Mock GestureHandler."""
        handler = Mock()
        return handler

    @pytest.fixture
    def executor(self, mock_driver, mock_gesture_handler):
        """Create ActionExecutor with mocks."""
        return ActionExecutor(mock_driver, mock_gesture_handler)

    def test_click_success(self, executor, mock_gesture_handler):
        """Test successful click action."""
        bounds = (100, 200, 300, 400)
        mock_gesture_handler.tap = Mock()

        result = executor.click(bounds)

        assert isinstance(result, ActionResult)
        assert result.success is True
        assert result.action_type == "click"
        assert result.target == "(200, 300)"  # center
        assert result.duration_ms >= 0
        assert result.error_message is None
        assert result.navigated_away is False

        mock_gesture_handler.tap.assert_called_once_with(200, 300)

    def test_click_failure(self, executor, mock_gesture_handler):
        """Test failed click action."""
        bounds = (100, 200, 300, 400)
        mock_gesture_handler.tap = Mock(side_effect=Exception("Tap failed"))

        result = executor.click(bounds)

        assert result.success is False
        assert result.error_message == "Tap failed"

    def test_input_success(self, executor, mock_driver, mock_gesture_handler):
        """Test successful input action."""
        bounds = (100, 200, 300, 400)
        text = "test input"
        mock_gesture_handler.tap = Mock()

        result = executor.input(bounds, text)

        assert result.success is True
        assert result.action_type == "input"
        assert result.target == "(200, 300)"

        mock_gesture_handler.tap.assert_called_once_with(200, 300)
        mock_driver.get_driver().press_keycode.assert_called_once_with(66)
        mock_driver.get_driver().find_element_by_xpath.assert_called_once_with("//*")
        # Note: send_keys would be called on the element, but we mocked find_element_by_xpath

    def test_long_press_success(self, executor, mock_gesture_handler):
        """Test successful long press action."""
        bounds = (100, 200, 300, 400)
        mock_gesture_handler.long_press = Mock()

        result = executor.long_press(bounds)

        assert result.success is True
        assert result.action_type == "long_press"
        assert result.target == "(200, 300)"

        mock_gesture_handler.long_press.assert_called_once_with(200, 300)

    def test_scroll_up_success(self, executor, mock_driver, mock_gesture_handler):
        """Test successful scroll up action."""
        mock_gesture_handler.scroll = Mock()

        result = executor.scroll_up()

        assert result.success is True
        assert result.action_type == "scroll_up"
        assert result.target == "(540, 960)"  # screen center

        mock_gesture_handler.scroll.assert_called_once_with(540, 960, "up")

    def test_scroll_down_success(self, executor, mock_gesture_handler):
        """Test successful scroll down action."""
        mock_gesture_handler.scroll = Mock()

        result = executor.scroll_down()

        assert result.success is True
        assert result.action_type == "scroll_down"
        assert result.target == "(540, 960)"

        mock_gesture_handler.scroll.assert_called_once_with(540, 960, "down")

    def test_swipe_left_success(self, executor, mock_gesture_handler):
        """Test successful swipe left action."""
        mock_gesture_handler.swipe = Mock()

        result = executor.swipe_left()

        assert result.success is True
        assert result.action_type == "swipe_left"
        assert result.target == "(540, 960)"

        mock_gesture_handler.swipe.assert_called_once_with(540, 960, "left")

    def test_swipe_right_success(self, executor, mock_gesture_handler):
        """Test successful swipe right action."""
        mock_gesture_handler.swipe = Mock()

        result = executor.swipe_right()

        assert result.success is True
        assert result.action_type == "swipe_right"
        assert result.target == "(540, 960)"

        mock_gesture_handler.swipe.assert_called_once_with(540, 960, "right")

    def test_back_success(self, executor, mock_driver):
        """Test successful back action."""
        result = executor.back()

        assert result.success is True
        assert result.action_type == "back"
        assert result.target == "back_button"

        mock_driver.get_driver().back.assert_called_once()

    def test_action_delay(self, executor, mock_gesture_handler):
        """Test that actions have minimum delay between them."""
        import time
        start_time = time.time()

        # First action
        executor.click((0, 0, 100, 100))

        # Second action should be delayed
        executor.click((0, 0, 100, 100))

        elapsed = time.time() - start_time
        # Should be at least 0.5 seconds due to delay
        assert elapsed >= 0.5

    def test_calculate_center(self, executor):
        """Test center calculation from bounds."""
        bounds = (10, 20, 30, 40)
        center = executor._calculate_center(bounds)
        assert center == (20, 30)  # ((10+30)/2, (20+40)/2)

    def test_get_screen_center(self, executor, mock_driver):
        """Test screen center calculation."""
        center = executor._get_screen_center()
        assert center == (540, 960)  # 1080/2, 1920/2