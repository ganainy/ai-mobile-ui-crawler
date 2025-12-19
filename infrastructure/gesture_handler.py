"""
Low-level gesture handling using W3C Actions API for Appium.
"""
import logging
from typing import Dict, Optional, Any, Tuple
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

logger = logging.getLogger(__name__)

class GestureHandler:
    """
    Handles low-level gesture execution through W3C Actions API.
    
    Provides specialized methods for tap, scroll, swipe, long press, etc.
    """
    
    def __init__(self, driver):
        """
        Initialize GestureHandler with a driver instance.
        
        Args:
            driver: The Appium/WebDriver instance
        """
        self.driver = driver

    def perform_w3c_tap(self, x: float, y: float) -> None:
        """
        Perform W3C Actions API tap at coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        actions = ActionChains(self.driver)
        actions.w3c_actions = ActionBuilder(self.driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
        actions.w3c_actions.pointer_action.move_to_location(x, y)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.pause(0.1)
        actions.w3c_actions.pointer_action.pointer_up()
        actions.perform()

    def perform_w3c_long_press(self, x: float, y: float, duration_ms: int) -> None:
        """
        Perform W3C Actions API long press at coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            duration_ms: Duration in milliseconds
        """
        actions = ActionChains(self.driver)
        actions.w3c_actions = ActionBuilder(self.driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
        actions.w3c_actions.pointer_action.move_to_location(x, y)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.pause(duration_ms / 1000.0)
        actions.w3c_actions.pointer_action.pointer_up()
        actions.perform()

    def perform_w3c_swipe(self, start_x: float, start_y: float, end_x: float, end_y: float, duration_sec: float = 0.8) -> None:
        """
        Perform W3C Actions API swipe between coordinates.
        
        Args:
            start_x, start_y: Starting coordinates
            end_x, end_y: Ending coordinates
            duration_sec: Duration of the swipe in seconds
        """
        actions = ActionChains(self.driver)
        actions.w3c_actions = ActionBuilder(self.driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
        actions.w3c_actions.pointer_action.move_to_location(start_x, start_y)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.move_to_location(end_x, end_y)
        actions.w3c_actions.pointer_action.pause(duration_sec)
        actions.w3c_actions.pointer_action.pointer_up()
        actions.perform()

    def perform_w3c_double_tap(self, x: float, y: float) -> None:
        """
        Perform W3C Actions API double tap at coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        actions = ActionChains(self.driver)
        actions.w3c_actions = ActionBuilder(self.driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
        # First tap
        actions.w3c_actions.pointer_action.move_to_location(x, y)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.pause(0.05)
        actions.w3c_actions.pointer_action.pointer_up()
        # Brief pause between taps
        actions.w3c_actions.pointer_action.pause(0.05)
        # Second tap
        actions.w3c_actions.pointer_action.move_to_location(x, y)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.pause(0.05)
        actions.w3c_actions.pointer_action.pointer_up()
        actions.perform()

    @staticmethod
    def get_element_center(element) -> Tuple[float, float]:
        """
        Get element center coordinates.
        
        Args:
            element: WebElement
            
        Returns:
            Tuple of (x, y) coordinates
        """
        location = element.location
        size = element.size
        
        return (
            location['x'] + size['width'] / 2,
            location['y'] + size['height'] / 2
        )
