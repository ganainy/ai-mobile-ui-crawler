"""Gesture handling utilities for mobile device interactions.

NOTE: In image-only mode, all gestures use coordinate-based actions only.
No webdriver element finding or XML/DOM access is used.
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass

from selenium.common.exceptions import WebDriverException

from mobile_crawler.infrastructure.appium_driver import AppiumDriver

logger = logging.getLogger(__name__)


# UIElement dataclass for backward compatibility
# NOTE: In image-only mode, UIElement is not used for main execution
# This is kept for backward compatibility with code that may use element-based methods
@dataclass
class UIElement:
    """Represents a UI element found on screen.
    
    NOTE: In image-only mode, this is not populated by the main crawler flow.
    Kept for backward compatibility with gesture_handler methods that accept UIElement.
    """
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


class GestureType(Enum):
    """Types of gestures supported."""
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    DRAG = "drag"
    PINCH = "pinch"
    ZOOM = "zoom"
    SCROLL = "scroll"


class GestureHandler:
    """Handles various gesture operations on mobile devices."""

    def __init__(self, appium_driver: AppiumDriver):
        """Initialize gesture handler.

        Args:
            appium_driver: AppiumDriver instance
        """
        self.driver = appium_driver

    def tap(self, element: UIElement, duration: float = 0.1) -> bool:
        """Tap on an element using coordinates only.

        NOTE: In image-only mode, this uses coordinate-based tapping only.
        No webdriver element finding is performed.

        Args:
            element: UIElement to tap (only center_x, center_y are used)
            duration: Duration of tap in seconds

        Returns:
            True if successful, False otherwise
        """
        return self.tap_at(element.center_x, element.center_y, duration)

    def tap_at(self, x: int, y: int, duration: float = 0.1) -> bool:
        """Tap at specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            duration: Duration of tap in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use W3C Actions API for Appium (TouchAction is deprecated)
            driver = self.driver.get_driver()
            
            from selenium.webdriver.common.actions.action_builder import ActionBuilder
            from selenium.webdriver.common.actions.pointer_input import PointerInput
            from selenium.webdriver.common.actions import interaction
            
            # Create a touch pointer
            pointer = PointerInput(interaction.POINTER_TOUCH, "finger")
            action_builder = ActionBuilder(driver, mouse=pointer, duration=100)
            
            # Build the tap sequence: move to location,  press, release
            action_builder.pointer_action.move_to_location(x, y)
            action_builder.pointer_action.pointer_down()
            action_builder.pointer_action.pause(0.05)  # Short pause for tap
            action_builder.pointer_action.pointer_up()
            
            # Perform the action
            action_builder.perform()
            
            time.sleep(duration)
            logger.info(f"Tapped at coordinates ({x}, {y})")
            return True
        except WebDriverException as e:
            logger.error(f"Failed to tap at ({x}, {y}): {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error tapping at ({x}, {y}): {e}")
            return False

    def double_tap(self, element: UIElement) -> bool:
        """Double tap on an element using coordinates only.

        NOTE: In image-only mode, this uses coordinate-based double tapping only.
        No webdriver element finding is performed.

        Args:
            element: UIElement to double tap (only center_x, center_y are used)

        Returns:
            True if successful, False otherwise
        """
        return self.double_tap_at(element.center_x, element.center_y)

    def double_tap_at(self, x: int, y: int) -> bool:
        """Double tap at specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if successful, False otherwise
        """
        try:
            actions = ActionChains(self.driver.get_driver())
            actions.move_by_offset(x, y).double_click().move_by_offset(-x, -y).perform()
            logger.info(f"Double tapped at coordinates ({x}, {y})")
            return True
        except WebDriverException as e:
            logger.error(f"Failed to double tap at ({x}, {y}): {e}")
            return False

    def long_press(self, element: UIElement, duration: float = 2.0) -> bool:
        """Long press on an element using coordinates only.

        NOTE: In image-only mode, this uses coordinate-based long press only.
        No webdriver element finding is performed.

        Args:
            element: UIElement to long press (only center_x, center_y are used)
            duration: Duration of press in seconds

        Returns:
            True if successful, False otherwise
        """
        return self.long_press_at(element.center_x, element.center_y, duration)

    def long_press_at(self, x: int, y: int, duration: float = 2.0) -> bool:
        """Long press at specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            duration: Duration of press in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use W3C Actions API for Appium
            driver = self.driver.get_driver()
            
            from selenium.webdriver.common.actions.action_builder import ActionBuilder
            from selenium.webdriver.common.actions.pointer_input import PointerInput
            from selenium.webdriver.common.actions import interaction
            
            # Create a touch pointer
            pointer = PointerInput(interaction.POINTER_TOUCH, "finger")
            action_builder = ActionBuilder(driver, mouse=pointer)
            
            # Build long press sequence: move, press, hold, release
            action_builder.pointer_action.move_to_location(x, y)
            action_builder.pointer_action.pointer_down()
            action_builder.pointer_action.pause(duration)  # Hold for specified duration
            action_builder.pointer_action.pointer_up()
            action_builder.perform()
            
            logger.info(f"Long pressed at coordinates ({x}, {y}) for {duration}s")
            return True
        except WebDriverException as e:
            logger.error(f"Failed to long press at ({x}, {y}): {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error long pressing at ({x}, {y}): {e}")
            return False

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int,
              duration: float = 0.5) -> bool:
        """Swipe from one point to another.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration: Duration of swipe in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use W3C Actions with absolute coordinates for Appium compatibility
            from selenium.webdriver.common.actions.action_builder import ActionBuilder
            from selenium.webdriver.common.actions.pointer_input import PointerInput
            from selenium.webdriver.common.actions import interaction
            
            driver = self.driver.get_driver()
            pointer = PointerInput(interaction.POINTER_TOUCH, "finger")
            actions = ActionBuilder(driver, mouse=pointer)
            
            # Move to start position (absolute coordinates required for first action)
            actions.pointer_action.move_to_location(start_x, start_y)
            actions.pointer_action.pointer_down()
            # Pause briefly before moving
            actions.pointer_action.pause(0.1)
            # Move to end position (absolute coordinates)
            actions.pointer_action.move_to_location(end_x, end_y)
            actions.pointer_action.pointer_up()
            actions.perform()

            # Add delay for swipe to complete
            time.sleep(duration)
            logger.info(f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            return True
        except WebDriverException as e:
            logger.error(f"Failed to swipe: {e}")
            return False

    def drag(self, element: UIElement, end_x: int, end_y: int, duration: float = 0.5) -> bool:
        """Drag an element to a new position using coordinates only.

        NOTE: In image-only mode, this uses coordinate-based dragging only.
        No webdriver element finding is performed.

        Args:
            element: UIElement to drag (only center_x, center_y are used)
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration: Duration of drag in seconds

        Returns:
            True if successful, False otherwise
        """
        return self.drag_from_to(element.center_x, element.center_y, end_x, end_y, duration)

    def drag_from_to(self, start_x: int, start_y: int, end_x: int, end_y: int,
                     duration: float = 0.5) -> bool:
        """Drag from one point to another.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration: Duration of drag in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use W3C Actions with absolute coordinates for Appium compatibility
            from selenium.webdriver.common.actions.action_builder import ActionBuilder
            from selenium.webdriver.common.actions.pointer_input import PointerInput
            from selenium.webdriver.common.actions import interaction
            
            driver = self.driver.get_driver()
            pointer = PointerInput(interaction.POINTER_TOUCH, "finger")
            actions = ActionBuilder(driver, mouse=pointer)
            
            # Move to start position (absolute coordinates required for first action)
            actions.pointer_action.move_to_location(start_x, start_y)
            actions.pointer_action.pointer_down()
            actions.pointer_action.pause(0.1)
            # Move to end position (absolute coordinates)
            actions.pointer_action.move_to_location(end_x, end_y)
            actions.pointer_action.pointer_up()
            actions.perform()
            
            time.sleep(duration)
            logger.info(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            return True
        except WebDriverException as e:
            logger.error(f"Failed to drag from ({start_x}, {start_y}) to ({end_x}, {end_y}): {e}")
            return False

    def scroll(self, direction: str, distance: int = 300, duration: float = 0.5) -> bool:
        """Scroll in a direction.

        Args:
            direction: Direction to scroll ('up', 'down', 'left', 'right')
            distance: Distance to scroll in pixels
            duration: Duration of scroll in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get screen dimensions
            size = self.driver.get_driver().get_window_size()
            width = size['width']
            height = size['height']

            # Calculate scroll coordinates based on direction
            if direction == 'up':
                start_x = width // 2
                start_y = height // 2
                end_x = width // 2
                end_y = height // 2 - distance
            elif direction == 'down':
                start_x = width // 2
                start_y = height // 2
                end_x = width // 2
                end_y = height // 2 + distance
            elif direction == 'left':
                start_x = width // 2
                start_y = height // 2
                end_x = width // 2 - distance
                end_y = height // 2
            elif direction == 'right':
                start_x = width // 2
                start_y = height // 2
                end_x = width // 2 + distance
                end_y = height // 2
            else:
                logger.error(f"Invalid scroll direction: {direction}")
                return False

            return self.swipe(start_x, start_y, end_x, end_y, duration)

        except (WebDriverException, KeyError, TypeError) as e:
            logger.error(f"Failed to scroll {direction}: {e}")
            return False

    def pinch(self, center_x: int, center_y: int, scale: float = 0.5) -> bool:
        """Pinch gesture (zoom out).

        Args:
            center_x: Center X coordinate
            center_y: Center Y coordinate
            scale: Scale factor (0.5 = zoom out, 2.0 = zoom in)

        Returns:
            True if successful, False otherwise
        """
        try:
            # This is a simplified pinch implementation
            # In a real implementation, you'd use multi-touch actions
            size = self.driver.get_driver().get_window_size()
            width = size['width'] if isinstance(size, dict) else 1080
            height = size['height'] if isinstance(size, dict) else 1920

            # Calculate pinch points
            pinch_distance = min(width, height) // 4

            # For zoom out (pinch), fingers start apart and come together
            if scale < 1.0:
                start_distance = int(pinch_distance * 2)
                end_distance = int(pinch_distance * scale * 2)
            else:
                # For zoom in, fingers start close and move apart
                start_distance = int(pinch_distance * 0.5)
                end_distance = int(pinch_distance * scale * 0.5)

            # Calculate finger positions
            start_finger1_x = center_x - start_distance // 2
            start_finger1_y = center_y
            start_finger2_x = center_x + start_distance // 2
            start_finger2_y = center_y

            end_finger1_x = center_x - end_distance // 2
            end_finger1_y = center_y
            end_finger2_x = center_x + end_distance // 2
            end_finger2_y = center_y

            # Perform pinch using multiple actions (simplified)
            # Note: Real pinch requires multi-touch support
            logger.warning("Pinch gesture is simplified and may not work on all devices")
            return self.drag_from_to(start_finger1_x, start_finger1_y,
                                   end_finger1_x, end_finger1_y, 0.5)

        except (WebDriverException, KeyError, TypeError) as e:
            logger.error(f"Failed to perform pinch gesture: {e}")
            return False

    # NOTE: webdriver-based methods removed in image-only mode:
    # - wait_for_element_interaction (was webdriver-based)
    # - _get_webdriver_element (was webdriver-based)
    # - _elements_match (was webdriver-based)
    # - _bounds_match (was webdriver-based)