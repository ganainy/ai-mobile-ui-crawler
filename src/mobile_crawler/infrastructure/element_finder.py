"""UI element finding and analysis utilities."""

import time
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import logging
import re

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from mobile_crawler.infrastructure.appium_driver import AppiumDriver
from mobile_crawler.infrastructure.screenshot_capture import ScreenshotCapture

logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    """Represents a UI element found on screen."""
    element_id: Optional[str]
    bounds: Tuple[int, int, int, int]  # (left, top, right, bottom)
    text: Optional[str]
    content_desc: Optional[str]
    class_name: Optional[str]
    package: Optional[str]
    clickable: bool
    visible: bool
    enabled: bool
    resource_id: Optional[str]
    xpath: Optional[str]
    center_x: int
    center_y: int

    @property
    def width(self) -> int:
        """Get element width."""
        return self.bounds[2] - self.bounds[0]

    @property
    def height(self) -> int:
        """Get element height."""
        return self.bounds[3] - self.bounds[1]

    @property
    def area(self) -> int:
        """Get element area."""
        return self.width * self.height

    def contains_point(self, x: int, y: int) -> bool:
        """Check if point (x, y) is within element bounds."""
        left, top, right, bottom = self.bounds
        return left <= x <= right and top <= y <= bottom

    def distance_to_point(self, x: int, y: int) -> float:
        """Calculate distance from element center to point."""
        dx = self.center_x - x
        dy = self.center_y - y
        return (dx ** 2 + dy ** 2) ** 0.5


class ElementFinderError(Exception):
    """Raised when element finding fails."""
    pass


class ElementNotFoundError(ElementFinderError):
    """Raised when a specific element is not found."""
    pass


class ElementFinder:
    """Handles finding and analyzing UI elements on Android screens."""

    def __init__(self, driver: AppiumDriver, screenshot_capture: ScreenshotCapture):
        """Initialize element finder.

        Args:
            driver: Appium driver instance
            screenshot_capture: Screenshot capture instance (required)
        """
        self.driver = driver
        self.screenshot_capture = screenshot_capture

    def find_element_by_id(self, element_id: str, timeout: float = 5.0) -> Optional[UIElement]:
        """Find element by resource ID.

        Args:
            element_id: Resource ID to search for
            timeout: Timeout in seconds

        Returns:
            UIElement if found, None otherwise
        """
        try:
            element = self.driver.get_driver().find_element(By.ID, element_id)
            return self._create_ui_element(element)
        except (NoSuchElementException, TimeoutException):
            return None

    def find_element_by_xpath(self, xpath: str, timeout: float = 5.0) -> Optional[UIElement]:
        """Find element by XPath.

        Args:
            xpath: XPath expression
            timeout: Timeout in seconds

        Returns:
            UIElement if found, None otherwise
        """
        try:
            element = self.driver.get_driver().find_element(By.XPATH, xpath)
            return self._create_ui_element(element)
        except (NoSuchElementException, TimeoutException):
            return None

    def find_element_by_text(self, text: str, partial: bool = False, timeout: float = 5.0) -> Optional[UIElement]:
        """Find element by text content.

        Args:
            text: Text to search for
            partial: Whether to match partial text
            timeout: Timeout in seconds

        Returns:
            UIElement if found, None otherwise
        """
        xpath = f"//*[@text='{text}']" if not partial else f"//*[contains(@text, '{text}')]"
        return self.find_element_by_xpath(xpath, timeout)

    def find_elements_by_class(self, class_name: str, timeout: float = 5.0) -> List[UIElement]:
        """Find all elements by class name.

        Args:
            class_name: Class name to search for
            timeout: Timeout in seconds

        Returns:
            List of UIElement objects
        """
        try:
            elements = self.driver.get_driver().find_elements(By.CLASS_NAME, class_name)
            return [self._create_ui_element(el) for el in elements]
        except (NoSuchElementException, TimeoutException):
            return []

    def find_clickable_elements(self, timeout: float = 5.0) -> List[UIElement]:
        """Find all clickable elements on screen.

        Args:
            timeout: Timeout in seconds

        Returns:
            List of clickable UIElement objects
        """
        try:
            elements = self.driver.get_driver().find_elements(By.XPATH, "//*[@clickable='true']")
            return [self._create_ui_element(el) for el in elements]
        except (NoSuchElementException, TimeoutException):
            return []

    def find_elements_by_bounds(self, bounds: Tuple[int, int, int, int], tolerance: int = 10) -> List[UIElement]:
        """Find elements within specified bounds.

        Args:
            bounds: (left, top, right, bottom) bounds
            tolerance: Pixel tolerance for bounds matching

        Returns:
            List of UIElement objects within bounds
        """
        # Get page source and parse elements
        page_source = self.driver.get_driver().page_source
        elements = self._parse_elements_from_source(page_source)

        result = []
        for element in elements:
            if self._bounds_match(element.bounds, bounds, tolerance):
                result.append(element)

        return result

    def get_all_elements(self, timeout: float = 5.0) -> List[UIElement]:
        """Get all UI elements on screen.

        Args:
            timeout: Timeout in seconds

        Returns:
            List of all UIElement objects
        """
        try:
            # Get page source and parse all elements
            page_source = self.driver.get_driver().page_source
            return self._parse_elements_from_source(page_source)
        except Exception as e:
            logger.warning(f"Failed to get all elements: {e}")
            return []

    def find_element_at_point(self, x: int, y: int) -> Optional[UIElement]:
        """Find the element at a specific screen coordinate.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            UIElement at the point, or None if no element found
        """
        elements = self.get_all_elements()
        for element in elements:
            if element.contains_point(x, y):
                return element
        return None

    def find_largest_element(self, elements: Optional[List[UIElement]] = None) -> Optional[UIElement]:
        """Find the largest element by area.

        Args:
            elements: List of elements to search, or None to get all elements

        Returns:
            Largest UIElement by area, or None if no elements
        """
        if elements is None:
            elements = self.get_all_elements()

        if not elements:
            return None

        return max(elements, key=lambda e: e.area)

    def find_elements_containing_text(self, text: str, case_sensitive: bool = False) -> List[UIElement]:
        """Find elements containing specific text.

        Args:
            text: Text to search for
            case_sensitive: Whether search is case sensitive

        Returns:
            List of UIElement objects containing the text
        """
        elements = self.get_all_elements()
        result = []

        for element in elements:
            element_text = element.text or ""
            search_text = text if case_sensitive else text.lower()
            element_text_search = element_text if case_sensitive else element_text.lower()

            if search_text in element_text_search:
                result.append(element)

        return result

    def wait_for_element(self, locator: Tuple[str, str], timeout: float = 10.0) -> UIElement:
        """Wait for an element to appear.

        Args:
            locator: (by, value) tuple for element location
            timeout: Maximum time to wait in seconds

        Returns:
            UIElement when found

        Raises:
            ElementNotFoundError: If element not found within timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                by, value = locator
                if by == By.ID:
                    element = self.find_element_by_id(value, timeout=1.0)
                elif by == By.XPATH:
                    element = self.find_element_by_xpath(value, timeout=1.0)
                else:
                    # For other locator types, try XPath
                    element = self.find_element_by_xpath(f"//*[@{by}='{value}']", timeout=1.0)

                if element:
                    return element
            except Exception:
                pass

            time.sleep(0.5)

        raise ElementNotFoundError(f"Element {locator} not found within {timeout} seconds")

    def _create_ui_element(self, appium_element) -> UIElement:
        """Create UIElement from Appium WebElement.

        Args:
            appium_element: Appium WebElement object

        Returns:
            UIElement object
        """
        # Get element bounds
        location = appium_element.location
        size = appium_element.size
        bounds = (
            int(location['x']),
            int(location['y']),
            int(location['x'] + size['width']),
            int(location['y'] + size['height'])
        )

        center_x = int(location['x'] + size['width'] / 2)
        center_y = int(location['y'] + size['height'] / 2)

        return UIElement(
            element_id=getattr(appium_element, 'id', None),
            bounds=bounds,
            text=appium_element.text if hasattr(appium_element, 'text') else None,
            content_desc=getattr(appium_element, 'get_attribute', lambda x: None)('content-desc'),
            class_name=getattr(appium_element, 'get_attribute', lambda x: None)('class'),
            package=getattr(appium_element, 'get_attribute', lambda x: None)('package'),
            clickable=appium_element.get_attribute('clickable') == 'true',
            visible=appium_element.get_attribute('visible') == 'true',
            enabled=appium_element.get_attribute('enabled') == 'true',
            resource_id=getattr(appium_element, 'get_attribute', lambda x: None)('resource-id'),
            xpath=None,  # Would need additional logic to generate
            center_x=center_x,
            center_y=center_y
        )

    def _parse_elements_from_source(self, page_source: str) -> List[UIElement]:
        """Parse UI elements from page source XML.

        Args:
            page_source: XML page source

        Returns:
            List of UIElement objects
        """
        # This is a simplified parser - in practice, you'd use proper XML parsing
        # and handle the complex Android UI hierarchy
        elements = []

        # Simple regex-based parsing for demonstration
        # In a real implementation, use xml.etree.ElementTree or similar
        element_pattern = re.compile(
            r'<(\w+(?:\.\w+)*)[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*>'
        )

        for match in element_pattern.finditer(page_source):
            try:
                bounds = (
                    int(match.group(2)),  # left
                    int(match.group(3)),  # top
                    int(match.group(4)),  # right
                    int(match.group(5))   # bottom
                )

                center_x = (bounds[0] + bounds[2]) // 2
                center_y = (bounds[1] + bounds[3]) // 2

                # Extract attributes from the element tag
                element_tag = match.group(0)
                
                # Extract individual attributes
                text = self._extract_attribute(element_tag, 'text')
                content_desc = self._extract_attribute(element_tag, 'content-desc')
                class_name = self._extract_attribute(element_tag, 'class')
                package = self._extract_attribute(element_tag, 'package')
                clickable = self._extract_attribute(element_tag, 'clickable') == 'true'
                visible = self._extract_attribute(element_tag, 'visible') == 'true'
                enabled = self._extract_attribute(element_tag, 'enabled') == 'true'
                resource_id = self._extract_attribute(element_tag, 'resource-id')

                element = UIElement(
                    element_id=None,
                    bounds=bounds,
                    text=text,
                    content_desc=content_desc,
                    class_name=class_name,
                    package=package,
                    clickable=clickable,
                    visible=visible,
                    enabled=enabled,
                    resource_id=resource_id,
                    xpath=None,
                    center_x=center_x,
                    center_y=center_y
                )
                elements.append(element)
            except (ValueError, IndexError):
                continue

        return elements

    def _extract_attribute(self, element_tag: str, attribute_name: str) -> Optional[str]:
        """Extract attribute value from XML element tag.
        
        Args:
            element_tag: The full element tag string
            attribute_name: Name of the attribute to extract
            
        Returns:
            Attribute value or None if not found
        """
        pattern = f'{attribute_name}="([^"]*)"'
        match = re.search(pattern, element_tag)
        return match.group(1) if match else None

    def _bounds_match(self, element_bounds: Tuple[int, int, int, int],
                     target_bounds: Tuple[int, int, int, int], tolerance: int) -> bool:
        """Check if element bounds match target bounds within tolerance.

        Args:
            element_bounds: Element bounds (left, top, right, bottom)
            target_bounds: Target bounds
            tolerance: Pixel tolerance

        Returns:
            True if bounds match within tolerance
        """
        e_left, e_top, e_right, e_bottom = element_bounds
        t_left, t_top, t_right, t_bottom = target_bounds

        return (abs(e_left - t_left) <= tolerance and
                abs(e_top - t_top) <= tolerance and
                abs(e_right - t_right) <= tolerance and
                abs(e_bottom - t_bottom) <= tolerance)