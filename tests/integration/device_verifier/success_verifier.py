"""Success verification utility for Appium action verification tests.

Provides multiple verification strategies:
1. Accessibility ID detection (preferred)  
2. Text-based XPath search (fallback)
"""

import logging
import time
from typing import Optional, TYPE_CHECKING

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

if TYPE_CHECKING:
    from appium.webdriver import Remote

logger = logging.getLogger(__name__)


class SuccessVerifier:
    """Verifies action success using accessibility ID or text detection."""
    
    # Accessibility ID used by the Flutter test app when action succeeds
    SUCCESS_INDICATOR_ID = "success_indicator"
    
    # Accessibility ID used while waiting for action
    WAITING_INDICATOR_ID = "status_indicator"
    
    # Text to search for as fallback
    SUCCESS_TEXT = "Success"
    
    def __init__(self, driver: "Remote"):
        """
        Initialize the success verifier.
        
        Args:
            driver: Appium WebDriver instance
        """
        self.driver = driver
    
    def wait_for_success(self, timeout: int = 10) -> bool:
        """
        Wait for success indicator using multiple strategies.
        
        Strategy order:
        1. Accessibility ID 'success_indicator'
        2. Text containing 'Success' (case-insensitive via XPath)
        
        Args:
            timeout: Maximum seconds to wait for success indicator
            
        Returns:
            True if success indicator found, False if timeout
        """
        logger.info(f"Waiting for success indicator (timeout: {timeout}s)")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Strategy 1: Accessibility ID
            if self._check_accessibility_id():
                logger.info("Success found via accessibility ID")
                return True
            
            # Strategy 2: Text search
            if self._check_text_contains():
                logger.info("Success found via text search")
                return True
            
            time.sleep(0.5)
        
        logger.warning(f"Timeout waiting for success indicator after {timeout}s")
        return False
    
    def _check_accessibility_id(self) -> bool:
        """Check for success_indicator in accessibility ID (content-desc)."""
        try:
            # Use XPath contains() since Flutter may include additional text in content-desc
            xpath = f"//*[contains(@content-desc, '{self.SUCCESS_INDICATOR_ID}')]"
            elements = self.driver.find_elements(AppiumBy.XPATH, xpath)
            return len(elements) > 0
        except Exception:
            return False
    
    def _check_text_contains(self) -> bool:
        """Check for 'Success' text anywhere on screen."""
        try:
            # XPath to find element containing 'Success' in text or content-desc
            xpath = f"//*[contains(@text, '{self.SUCCESS_TEXT}') or contains(@content-desc, '{self.SUCCESS_TEXT}')]"
            elements = self.driver.find_elements(AppiumBy.XPATH, xpath)
            
            # Filter out elements that contain unwanted text like "Hub Loaded"
            for el in elements:
                try:
                    text = el.text or el.get_attribute("content-desc") or ""
                    # Exclude hub-related success messages
                    if "Hub" not in text and self.SUCCESS_TEXT in text:
                        return True
                except Exception:
                    continue
            
            return False
        except Exception as e:
            logger.debug(f"Text search failed: {e}")
            return False
    
    def is_success_visible(self) -> bool:
        """
        Check if success indicator is currently visible (non-blocking).
        
        Returns:
            True if success indicator is present, False otherwise
        """
        return self._check_accessibility_id() or self._check_text_contains()
    
    def get_status_text(self) -> Optional[str]:
        """
        Get the current status indicator text.
        
        Returns:
            Status text or None if not found
        """
        try:
            # Try accessibility ID first
            for aid in [self.SUCCESS_INDICATOR_ID, self.WAITING_INDICATOR_ID]:
                elements = self.driver.find_elements(AppiumBy.ACCESSIBILITY_ID, aid)
                if elements:
                    return elements[0].text or elements[0].get_attribute("content-desc")
            
            # Try text search
            xpath = f"//*[contains(@text, '{self.SUCCESS_TEXT}') or contains(@content-desc, '{self.SUCCESS_TEXT}')]"
            elements = self.driver.find_elements(AppiumBy.XPATH, xpath)
            if elements:
                return elements[0].text or elements[0].get_attribute("content-desc")
            
            return None
        except Exception as e:
            logger.error(f"Error getting status text: {e}")
            return None
