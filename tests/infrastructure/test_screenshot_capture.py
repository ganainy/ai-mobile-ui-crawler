"""Tests for screenshot capture functionality."""

import io
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from mobile_crawler.infrastructure.screenshot_capture import (
    ScreenshotCapture,
    ScreenshotCaptureError
)
from mobile_crawler.infrastructure.appium_driver import AppiumDriver


class TestScreenshotCapture:
    """Test ScreenshotCapture class."""

    @pytest.fixture
    def mock_driver(self):
        """Create a mock AppiumDriver."""
        mock_appium_driver = Mock(spec=AppiumDriver)
        mock_webdriver = Mock()
        mock_appium_driver.get_driver.return_value = mock_webdriver
        return mock_appium_driver

    @pytest.fixture
    def screenshot_capture(self, mock_driver):
        """Create ScreenshotCapture instance."""
        return ScreenshotCapture(mock_driver)

    def test_init(self, mock_driver):
        """Test initialization."""
        capture = ScreenshotCapture(mock_driver, max_width=1024, max_height=768)
        assert capture.driver == mock_driver
        assert capture.max_width == 1024
        assert capture.max_height == 768

    @patch('mobile_crawler.infrastructure.screenshot_capture.base64')
    @patch('mobile_crawler.infrastructure.screenshot_capture.Image')
    def test_capture_screenshot_success(self, mock_image_class, mock_base64, screenshot_capture, mock_driver):
        """Test successful screenshot capture."""
        # Mock base64 screenshot data
        mock_driver.get_driver.return_value.get_screenshot_as_base64.return_value = "base64data"

        # Mock PIL Image
        mock_image = Mock(spec=Image.Image)
        mock_image_class.open.return_value = mock_image

        # Mock base64 decode
        mock_base64.b64decode.return_value = b"imagedata"

        result = screenshot_capture.capture_screenshot()

        assert result == mock_image
        mock_driver.get_driver.return_value.get_screenshot_as_base64.assert_called_once()
        mock_base64.b64decode.assert_called_once_with("base64data")
        mock_image_class.open.assert_called_once()

    def test_capture_screenshot_failure(self, screenshot_capture, mock_driver):
        """Test screenshot capture failure."""
        mock_driver.get_driver.return_value.get_screenshot_as_base64.side_effect = Exception("Screenshot failed")

        with pytest.raises(ScreenshotCaptureError, match="Failed to capture screenshot"):
            screenshot_capture.capture_screenshot()

    @patch('mobile_crawler.infrastructure.screenshot_capture.base64')
    @patch('mobile_crawler.infrastructure.screenshot_capture.Image')
    def test_capture_and_downscale(self, mock_image_class, mock_base64, screenshot_capture, mock_driver):
        """Test capture and downscale."""
        # Create a mock image that's larger than max dimensions
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (1600, 1200)  # Larger than default 800x600
        mock_image.resize.return_value = Mock(spec=Image.Image)
        mock_image_class.open.return_value = mock_image

        # Mock base64
        mock_base64.b64decode.return_value = b"imagedata"
        mock_driver.get_driver.return_value.get_screenshot_as_base64.return_value = "base64data"

        result = screenshot_capture.capture_and_downscale()

        # Should have resized the image
        mock_image.resize.assert_called_once()
        args, kwargs = mock_image.resize.call_args
        assert args[0] == (800, 600)  # Scaled to fit within 800x600

    def test_downscale_image_no_scaling_needed(self, screenshot_capture):
        """Test downscaling when image is already small enough."""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (400, 300)  # Smaller than 800x600

        result = screenshot_capture._downscale_image(mock_image)

        assert result == mock_image
        mock_image.resize.assert_not_called()

    def test_downscale_image_scaling_needed(self, screenshot_capture):
        """Test downscaling when image needs to be scaled."""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (1600, 1200)
        mock_resized = Mock(spec=Image.Image)
        mock_image.resize.return_value = mock_resized

        result = screenshot_capture._downscale_image(mock_image)

        assert result == mock_resized
        mock_image.resize.assert_called_once_with((800, 600), Image.Resampling.LANCZOS)

    @patch('mobile_crawler.infrastructure.screenshot_capture.Path')
    @patch('mobile_crawler.infrastructure.screenshot_capture.base64')
    @patch('mobile_crawler.infrastructure.screenshot_capture.Image')
    def test_capture_to_file(self, mock_image_class, mock_base64, mock_path_class, screenshot_capture, mock_driver):
        """Test saving screenshot to file."""
        # Mock image
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (1600, 1200)  # Larger than max dimensions
        mock_resized = Mock(spec=Image.Image)
        mock_image.resize.return_value = mock_resized
        mock_image_class.open.return_value = mock_image

        # Mock base64
        mock_base64.b64decode.return_value = b"imagedata"
        mock_driver.get_driver.return_value.get_screenshot_as_base64.return_value = "base64data"

        # Mock path
        mock_path = Mock()
        mock_path.parent.mkdir = Mock()
        mock_path_class.return_value = mock_path

        screenshot_capture.capture_to_file("/path/to/screenshot.png", downscale=True)

        mock_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_resized.save.assert_called_once_with("/path/to/screenshot.png")

    @patch('mobile_crawler.infrastructure.screenshot_capture.base64')
    @patch('mobile_crawler.infrastructure.screenshot_capture.Image')
    @patch('mobile_crawler.infrastructure.screenshot_capture.np')
    def test_capture_to_numpy(self, mock_np, mock_image_class, mock_base64, screenshot_capture, mock_driver):
        """Test capturing to numpy array."""
        # Mock image
        mock_image = Mock(spec=Image.Image)
        mock_image.mode = 'RGBA'
        mock_image.convert.return_value = Mock(spec=Image.Image)
        mock_image_class.open.return_value = mock_image

        # Mock numpy array
        mock_array = np.array([[1, 2], [3, 4]])
        mock_np.array.return_value = mock_array

        # Mock base64
        mock_base64.b64decode.return_value = b"imagedata"
        mock_driver.get_driver.return_value.get_screenshot_as_base64.return_value = "base64data"

        result = screenshot_capture.capture_to_numpy(downscale=False)

        assert result is mock_array
        mock_image.convert.assert_called_once_with('RGB')
        mock_np.array.assert_called_once()

    def test_get_image_info(self, screenshot_capture):
        """Test getting image information."""
        mock_image = Mock(spec=Image.Image)
        mock_image.width = 800
        mock_image.height = 600
        mock_image.mode = 'RGB'
        mock_image.format = 'PNG'
        mock_image.tobytes.return_value = b"123456789"

        info = screenshot_capture.get_image_info(mock_image)

        expected = {
            'width': 800,
            'height': 600,
            'mode': 'RGB',
            'format': 'PNG',
            'size_bytes': 9
        }
        assert info == expected

    @patch('mobile_crawler.infrastructure.screenshot_capture.base64')
    @patch('mobile_crawler.infrastructure.screenshot_capture.Image')
    def test_get_image_info_capture_new(self, mock_image_class, mock_base64, screenshot_capture, mock_driver):
        """Test getting image info by capturing new screenshot."""
        mock_image = Mock(spec=Image.Image)
        mock_image.width = 400
        mock_image.height = 300
        mock_image.mode = 'RGB'
        mock_image.format = None
        mock_image.tobytes.return_value = b"123456789"
        mock_image_class.open.return_value = mock_image

        mock_base64.b64decode.return_value = b"imagedata"
        mock_driver.get_driver.return_value.get_screenshot_as_base64.return_value = "base64data"

        info = screenshot_capture.get_image_info()

        assert info['width'] == 400
        assert info['height'] == 300

    def test_compare_images_identical(self, screenshot_capture):
        """Test comparing identical images."""
        # Create identical mock images
        mock_image1 = Mock(spec=Image.Image)
        mock_image1.size = (100, 100)
        mock_image1.convert.return_value = Mock()

        mock_image2 = Mock(spec=Image.Image)
        mock_image2.size = (100, 100)
        mock_image2.convert.return_value = Mock()

        # Mock numpy arrays for identical images
        with patch('mobile_crawler.infrastructure.screenshot_capture.np') as mock_np:
            mock_np.abs.return_value = np.zeros((100, 100))
            mock_np.mean.return_value = 0.0

            is_similar, difference = screenshot_capture.compare_images(mock_image1, mock_image2)

            assert is_similar is True
            assert difference == 0.0

    def test_compare_images_different_sizes(self, screenshot_capture):
        """Test comparing images of different sizes."""
        mock_image1 = Mock(spec=Image.Image)
        mock_image1.size = (200, 200)

        mock_image2 = Mock(spec=Image.Image)
        mock_image2.size = (100, 100)
        mock_resized = Mock(spec=Image.Image)
        mock_image2.resize.return_value = mock_resized
        mock_resized.convert.return_value = Mock()

        mock_image1.convert.return_value = Mock()

        with patch('mobile_crawler.infrastructure.screenshot_capture.np') as mock_np:
            mock_np.abs.return_value = np.ones((200, 200)) * 128  # Medium difference
            mock_np.mean.return_value = 128.0

            is_similar, difference = screenshot_capture.compare_images(mock_image1, mock_image2)

            assert is_similar is False
            assert difference == 128.0 / 255.0
            mock_image2.resize.assert_called_once_with((200, 200), Image.Resampling.LANCZOS)

    @patch('mobile_crawler.infrastructure.screenshot_capture.time.sleep')
    @patch('mobile_crawler.infrastructure.screenshot_capture.base64')
    @patch('mobile_crawler.infrastructure.screenshot_capture.Image')
    def test_wait_for_stable_screen_success(self, mock_image_class, mock_base64, mock_sleep, screenshot_capture, mock_driver):
        """Test waiting for stable screen successfully."""
        # Mock images - second one is identical to first (stable)
        mock_image1 = Mock(spec=Image.Image)
        mock_image1.size = (100, 100)
        mock_image1.convert.return_value = Mock()

        mock_image2 = Mock(spec=Image.Image)
        mock_image2.size = (100, 100)
        mock_image2.convert.return_value = Mock()

        mock_image_class.open.side_effect = [mock_image1, mock_image2]

        mock_base64.b64decode.return_value = b"imagedata"
        mock_driver.get_driver.return_value.get_screenshot_as_base64.return_value = "base64data"

        # Mock comparison to return stable on second attempt
        with patch.object(screenshot_capture, 'compare_images') as mock_compare:
            mock_compare.return_value = (True, 0.01)  # Stable

            result = screenshot_capture.wait_for_stable_screen(max_attempts=5)

            assert result == mock_image2
            assert mock_compare.call_count == 1
            mock_sleep.assert_called_once_with(0.5)

    @patch('mobile_crawler.infrastructure.screenshot_capture.time.sleep')
    @patch('mobile_crawler.infrastructure.screenshot_capture.base64')
    @patch('mobile_crawler.infrastructure.screenshot_capture.Image')
    def test_wait_for_stable_screen_timeout(self, mock_image_class, mock_base64, mock_sleep, screenshot_capture, mock_driver):
        """Test waiting for stable screen times out."""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (100, 100)
        mock_image.convert.return_value = Mock()

        mock_image_class.open.return_value = mock_image

        mock_base64.b64decode.return_value = b"imagedata"
        mock_driver.get_driver.return_value.get_screenshot_as_base64.return_value = "base64data"

        # Mock comparison to always return unstable
        with patch.object(screenshot_capture, 'compare_images') as mock_compare:
            mock_compare.return_value = (False, 0.2)  # Unstable

            with pytest.raises(ScreenshotCaptureError, match="Screen did not stabilize"):
                screenshot_capture.wait_for_stable_screen(max_attempts=3, delay=0.1)

            assert mock_compare.call_count == 2  # Called for attempts 2 and 3
            assert mock_sleep.call_count == 2