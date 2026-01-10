"""Tests for element finder functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from mobile_crawler.infrastructure.element_finder import (
    ElementFinder,
    UIElement,
    ElementFinderError,
    ElementNotFoundError
)
from mobile_crawler.infrastructure.appium_driver import AppiumDriver


class TestUIElement:
    """Test UIElement dataclass."""

    def test_element_properties(self):
        """Test element property calculations."""
        element = UIElement(
            element_id="test_id",
            bounds=(10, 20, 110, 70),
            text="Test Button",
            content_desc="A test button",
            class_name="android.widget.Button",
            package="com.example.app",
            clickable=True,
            visible=True,
            enabled=True,
            resource_id="com.example.app:id/button",
            xpath="//button[@text='Test Button']",
            center_x=60,
            center_y=45
        )

        assert element.width == 100
        assert element.height == 50
        assert element.area == 5000
        assert element.contains_point(60, 45) is True
        assert element.contains_point(5, 5) is False
        assert element.distance_to_point(60, 45) == 0.0
        assert element.distance_to_point(70, 55) == pytest.approx(14.14, abs=0.01)

    def test_element_bounds_edge_cases(self):
        """Test element bounds edge cases."""
        element = UIElement(
            element_id=None,
            bounds=(0, 0, 100, 100),
            text=None,
            content_desc=None,
            class_name=None,
            package=None,
            clickable=False,
            visible=False,
            enabled=False,
            resource_id=None,
            xpath=None,
            center_x=50,
            center_y=50
        )

        assert element.contains_point(0, 0) is True
        assert element.contains_point(100, 100) is True
        assert element.contains_point(101, 101) is False


class TestElementFinder:
    """Test ElementFinder class."""

    @pytest.fixture
    def mock_driver(self):
        """Create a mock AppiumDriver."""
        mock_appium_driver = Mock(spec=AppiumDriver)
        mock_webdriver = Mock()
        mock_appium_driver.get_driver.return_value = mock_webdriver
        return mock_appium_driver

    @pytest.fixture
    def element_finder(self, mock_driver):
        """Create ElementFinder instance."""
        return ElementFinder(mock_driver)

    def test_init(self, mock_driver):
        """Test initialization."""
        finder = ElementFinder(mock_driver)
        assert finder.driver == mock_driver
        assert finder.screenshot_capture is not None

    @patch('mobile_crawler.infrastructure.element_finder.ScreenshotCapture')
    def test_init_with_screenshot_capture(self, mock_screenshot_capture_class, mock_driver):
        """Test initialization with custom screenshot capture."""
        mock_screenshot_capture = Mock()
        mock_screenshot_capture_class.return_value = mock_screenshot_capture

        finder = ElementFinder(mock_driver, mock_screenshot_capture)
        assert finder.screenshot_capture == mock_screenshot_capture

    def test_find_element_by_id_success(self, element_finder, mock_driver):
        """Test successful element finding by ID."""
        mock_element = Mock()
        mock_element.location = {'x': 10, 'y': 20}
        mock_element.size = {'width': 100, 'height': 50}
        mock_element.text = "Test"
        mock_element.id = "element123"  # Add id attribute
        mock_element.get_attribute.side_effect = lambda attr: {
            'content-desc': 'Description',
            'class': 'Button',
            'package': 'com.example',
            'clickable': 'true',
            'visible': 'true',
            'enabled': 'true',
            'resource-id': 'test:id'
        }.get(attr)

        mock_driver.get_driver.return_value.find_element.return_value = mock_element

        result = element_finder.find_element_by_id("test:id")

        assert result is not None
        assert result.element_id == "element123"  # Should have the id now
        assert result.bounds == (10, 20, 110, 70)
        assert result.text == "Test"
        assert result.center_x == 60
        assert result.center_y == 45

    def test_find_element_by_id_not_found(self, element_finder, mock_driver):
        """Test element not found by ID."""
        mock_driver.get_driver.return_value.find_element.side_effect = NoSuchElementException()

        result = element_finder.find_element_by_id("nonexistent:id")
        assert result is None

    def test_find_element_by_xpath_success(self, element_finder, mock_driver):
        """Test successful element finding by XPath."""
        mock_element = Mock()
        mock_element.location = {'x': 0, 'y': 0}
        mock_element.size = {'width': 50, 'height': 30}
        mock_element.get_attribute.return_value = None

        mock_driver.get_driver.return_value.find_element.return_value = mock_element

        result = element_finder.find_element_by_xpath("//button")

        assert result is not None
        assert result.bounds == (0, 0, 50, 30)

    def test_find_element_by_text_exact(self, element_finder, mock_driver):
        """Test finding element by exact text."""
        mock_element = Mock()
        mock_element.location = {'x': 10, 'y': 10}
        mock_element.size = {'width': 80, 'height': 40}
        mock_element.get_attribute.return_value = None

        mock_driver.get_driver.return_value.find_element.return_value = mock_element

        result = element_finder.find_element_by_text("Click Me")

        assert result is not None
        mock_driver.get_driver.return_value.find_element.assert_called_with(
            'xpath', "//*[@text='Click Me']"
        )

    def test_find_element_by_text_partial(self, element_finder, mock_driver):
        """Test finding element by partial text."""
        mock_element = Mock()
        mock_element.location = {'x': 10, 'y': 10}
        mock_element.size = {'width': 80, 'height': 40}
        mock_element.get_attribute.return_value = None

        mock_driver.get_driver.return_value.find_element.return_value = mock_element

        result = element_finder.find_element_by_text("Click", partial=True)

        assert result is not None
        mock_driver.get_driver.return_value.find_element.assert_called_with(
            'xpath', "//*[contains(@text, 'Click')]"
        )

    def test_find_elements_by_class(self, element_finder, mock_driver):
        """Test finding elements by class."""
        mock_element1 = Mock()
        mock_element1.location = {'x': 0, 'y': 0}
        mock_element1.size = {'width': 50, 'height': 30}
        mock_element1.get_attribute.return_value = None

        mock_element2 = Mock()
        mock_element2.location = {'x': 60, 'y': 0}
        mock_element2.size = {'width': 50, 'height': 30}
        mock_element2.get_attribute.return_value = None

        mock_driver.get_driver.return_value.find_elements.return_value = [mock_element1, mock_element2]

        result = element_finder.find_elements_by_class("android.widget.Button")

        assert len(result) == 2
        assert result[0].bounds == (0, 0, 50, 30)
        assert result[1].bounds == (60, 0, 110, 30)

    def test_find_clickable_elements(self, element_finder, mock_driver):
        """Test finding clickable elements."""
        mock_element = Mock()
        mock_element.location = {'x': 10, 'y': 10}
        mock_element.size = {'width': 80, 'height': 40}
        mock_element.get_attribute.return_value = None

        mock_driver.get_driver.return_value.find_elements.return_value = [mock_element]

        result = element_finder.find_clickable_elements()

        assert len(result) == 1
        mock_driver.get_driver.return_value.find_elements.assert_called_with(
            'xpath', "//*[@clickable='true']"
        )

    def test_get_all_elements(self, element_finder, mock_driver):
        """Test getting all elements from page source."""
        page_source = '''<?xml version='1.0' encoding='UTF-8'?>
<hierarchy>
  <android.widget.FrameLayout bounds="[0,0][1080,1920]">
    <android.widget.Button bounds="[100,200][300,300]" text="Click Me" clickable="true" visible="true" enabled="true"/>
    <android.widget.TextView bounds="[100,350][300,400]" text="Hello World" clickable="false" visible="true" enabled="true"/>
  </android.widget.FrameLayout>
</hierarchy>'''

        mock_driver.get_driver.return_value.page_source = page_source

        result = element_finder.get_all_elements()

        # Should find elements with bounds
        assert len(result) >= 2
        button = next((e for e in result if e.text == "Click Me"), None)
        assert button is not None
        assert button.bounds == (100, 200, 300, 300)
        assert button.clickable is True

    def test_find_element_at_point(self, element_finder, mock_driver):
        """Test finding element at specific point."""
        page_source = '''<?xml version='1.0' encoding='UTF-8'?>
<hierarchy>
  <android.widget.Button bounds="[100,200][300,300]" text="Click Me"/>
  <android.widget.TextView bounds="[400,200][600,300]" text="Other"/>
</hierarchy>'''

        mock_driver.get_driver.return_value.page_source = page_source

        # Point within first button
        result = element_finder.find_element_at_point(150, 250)
        assert result is not None
        assert result.text == "Click Me"

        # Point within second element
        result = element_finder.find_element_at_point(500, 250)
        assert result is not None
        assert result.text == "Other"

        # Point with no element
        result = element_finder.find_element_at_point(50, 50)
        assert result is None

    def test_find_largest_element(self, element_finder, mock_driver):
        """Test finding largest element."""
        page_source = '''<?xml version='1.0' encoding='UTF-8'?>
<hierarchy>
  <android.widget.Button bounds="[100,200][200,250]" text="Small"/>
  <android.widget.TextView bounds="[100,300][400,500]" text="Large"/>
  <android.widget.ImageView bounds="[100,600][250,650]" text="Medium"/>
</hierarchy>'''

        mock_driver.get_driver.return_value.page_source = page_source

        result = element_finder.find_largest_element()

        assert result is not None
        assert result.text == "Large"
        assert result.area == (400 - 100) * (500 - 300)  # 300 * 200 = 60000

    def test_find_elements_containing_text(self, element_finder, mock_driver):
        """Test finding elements containing text."""
        page_source = '''<?xml version='1.0' encoding='UTF-8'?>
<hierarchy>
  <android.widget.Button bounds="[100,200][300,300]" text="Click Me"/>
  <android.widget.TextView bounds="[100,350][300,400]" text="Hello World"/>
  <android.widget.TextView bounds="[100,450][300,500]" text="Click Here"/>
</hierarchy>'''

        mock_driver.get_driver.return_value.page_source = page_source

        result = element_finder.find_elements_containing_text("Click")
        assert len(result) == 2
        texts = [e.text for e in result]
        assert "Click Me" in texts
        assert "Click Here" in texts

    def test_find_elements_containing_text_case_insensitive(self, element_finder, mock_driver):
        """Test case insensitive text search."""
        page_source = '''<?xml version='1.0' encoding='UTF-8'?>
<hierarchy>
  <android.widget.Button bounds="[100,200][300,300]" text="CLICK ME"/>
</hierarchy>'''

        mock_driver.get_driver.return_value.page_source = page_source

        result = element_finder.find_elements_containing_text("click", case_sensitive=False)
        assert len(result) == 1
        assert result[0].text == "CLICK ME"

    @patch('mobile_crawler.infrastructure.element_finder.time.sleep')
    def test_wait_for_element_success(self, mock_sleep, element_finder, mock_driver):
        """Test waiting for element successfully."""
        mock_element = Mock()
        mock_element.location = {'x': 10, 'y': 10}
        mock_element.size = {'width': 80, 'height': 40}
        mock_element.get_attribute.return_value = None

        # First call fails, second succeeds
        mock_driver.get_driver.return_value.find_element.side_effect = [
            NoSuchElementException(),
            mock_element
        ]

        from selenium.webdriver.common.by import By
        result = element_finder.wait_for_element((By.ID, "test:id"))

        assert result is not None
        assert result.bounds == (10, 10, 90, 50)
        mock_sleep.assert_called_once_with(0.5)

    @patch('mobile_crawler.infrastructure.element_finder.time.sleep')
    def test_wait_for_element_timeout(self, mock_sleep, element_finder, mock_driver):
        """Test waiting for element times out."""
        mock_driver.get_driver.return_value.find_element.side_effect = NoSuchElementException()

        from selenium.webdriver.common.by import By
        with pytest.raises(ElementNotFoundError, match="Element .* not found within"):
            element_finder.wait_for_element((By.ID, "test:id"), timeout=2.0)

        # Should have tried multiple times
        assert mock_sleep.call_count > 1

    def test_bounds_match(self, element_finder):
        """Test bounds matching with tolerance."""
        # Exact match
        assert element_finder._bounds_match((10, 20, 100, 200), (10, 20, 100, 200), 0) is True

        # Within tolerance
        assert element_finder._bounds_match((10, 20, 100, 200), (12, 18, 102, 198), 5) is True

        # Outside tolerance
        assert element_finder._bounds_match((10, 20, 100, 200), (20, 30, 110, 210), 5) is False