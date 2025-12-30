"""
Element discovery and locator logic for Appium.
"""
import logging
import time
from typing import List, Optional, Tuple, Literal, Any, Callable

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
)

from infrastructure.appium_error_handler import (
    ElementNotFoundError,
)

logger = logging.getLogger(__name__)

LocatorStrategy = Literal[
    'id', 'xpath', 'accessibility id', 'class name', 'css selector',
    'tag name', 'link text', 'partial link text', 'name',
    'android uiautomator'
]

class ElementFinder:
    """
    Handles element discovery with robust fallback strategies and retries.
    """
    
    def __init__(self, driver, target_package: Optional[str] = None):
        """
        Initialize ElementFinder.
        
        Args:
            driver: The Appium/WebDriver instance
            target_package: The target Android package for ID prefixing
        """
        self.driver = driver
        self.target_package = target_package
        self._current_implicit_wait = None

    def get_locator(self, selector: str, strategy: LocatorStrategy) -> Tuple[str, str]:
        """
        Get Selenium/Appium locator tuple from strategy and selector.
        """
        strategy_map = {
            'id': (AppiumBy.ID, selector),
            'xpath': (AppiumBy.XPATH, selector),
            'accessibility id': (AppiumBy.ACCESSIBILITY_ID, selector),
            'class name': (AppiumBy.CLASS_NAME, selector),
            'css selector': (AppiumBy.CSS_SELECTOR, selector),
            'tag name': (AppiumBy.TAG_NAME, selector),
            'link text': (AppiumBy.LINK_TEXT, selector),
            'partial link text': (AppiumBy.PARTIAL_LINK_TEXT, selector),
            'name': (AppiumBy.NAME, selector),
            'android uiautomator': (AppiumBy.ANDROID_UIAUTOMATOR, selector),
        }
        
        return strategy_map.get(strategy, (AppiumBy.ID, selector))

    def find_element(
        self,
        selector: str,
        strategy: LocatorStrategy = 'id',
        timeout_ms: int = 10000,
        implicit_wait_ms: int = 5000,
        platform: str = 'android'
    ) -> WebElement:
        """
        Find element with specified strategy and robust fallbacks for Android.
        """
        start_time = time.time()
        last_error: Optional[Exception] = None
        
        try:
            # Temporarily reduce implicit wait for faster attempts
            original_timeout = self._current_implicit_wait or (implicit_wait_ms / 1000.0)
            reduced_implicit_wait = 1.0  # Lower implicit wait for faster failure detection
            
            if abs(original_timeout - reduced_implicit_wait) > 0.1:
                self.driver.implicitly_wait(reduced_implicit_wait)
                self._current_implicit_wait = reduced_implicit_wait
            
            try:
                # For Android with 'id' strategy, prioritize UIAutomator (proven to be ~100x faster)
                if strategy == 'id' and platform == 'android':
                    # Primary strategy: Android UIAutomator (fastest for Android resource IDs)
                    strategy_start = time.time()
                    try:
                        uiautomator_selector = f'new UiSelector().resourceId("{selector}")'
                        element = self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, uiautomator_selector)
                        if element.is_displayed():
                            strategy_duration = (time.time() - strategy_start) * 1000
                            total_duration = (time.time() - start_time) * 1000
                            return element
                    except (NoSuchElementException, TimeoutException) as e:
                        strategy_duration = (time.time() - strategy_start) * 1000
                        last_error = e
                    
                    # Fallback 1: Standard ID with explicit wait
                    by, value = self.get_locator(selector, strategy)
                    explicit_timeout = min(timeout_ms / 1000.0, 3.0)
                    fallback_start = time.time()
                    try:
                        wait = WebDriverWait(self.driver, explicit_timeout)
                        element = wait.until(EC.visibility_of_element_located((by, value)))
                        fallback_duration = (time.time() - fallback_start) * 1000
                        return element
                    except (NoSuchElementException, TimeoutException) as e:
                        fallback_duration = (time.time() - fallback_start) * 1000
                    
                    # Fallback 2: Accessibility ID
                    fallback_start = time.time()
                    try:
                        element = self.driver.find_element(AppiumBy.ACCESSIBILITY_ID, selector)
                        if element.is_displayed():
                            fallback_duration = (time.time() - fallback_start) * 1000
                            return element
                    except (NoSuchElementException, TimeoutException) as e:
                        fallback_duration = (time.time() - fallback_start) * 1000
                    
                    # Fallback 3: Package-prefixed ID
                    if ':' not in selector and self.target_package:
                        package_prefixed = f'{self.target_package}:id/{selector}'
                        fallback_start = time.time()
                        try:
                            element = self.driver.find_element(by, package_prefixed)
                            if element.is_displayed():
                                fallback_duration = (time.time() - fallback_start) * 1000
                                return element
                        except (NoSuchElementException, TimeoutException) as e:
                            fallback_duration = (time.time() - fallback_start) * 1000
                    
                    # Fallback 4: XPath by resource-id
                    fallback_start = time.time()
                    try:
                        xpath_exact = f'//*[@resource-id="{selector}"]'
                        element = self.driver.find_element(AppiumBy.XPATH, xpath_exact)
                        if element.is_displayed():
                            fallback_duration = (time.time() - fallback_start) * 1000
                            return element
                    except (NoSuchElementException, TimeoutException) as e:
                        fallback_duration = (time.time() - fallback_start) * 1000
                    
                    # If all strategies failed, raise the last error
                    if last_error:
                        raise last_error
                    raise ElementNotFoundError(f'Element not found with any strategy: {selector}')
                else:
                    # For non-Android or non-ID strategies, use standard approach
                    by, value = self.get_locator(selector, strategy)
                    explicit_timeout = min(timeout_ms / 1000.0, 5.0)
                    
                    strategy_start = time.time()
                    wait = WebDriverWait(self.driver, explicit_timeout)
                    element = wait.until(EC.visibility_of_element_located((by, value)))
                    
                    strategy_duration = (time.time() - strategy_start) * 1000
                    return element
            finally:
                # Restore original timeout
                if abs(self._current_implicit_wait - original_timeout) > 0.1:
                    self.driver.implicitly_wait(original_timeout)
                    self._current_implicit_wait = original_timeout
                    
        except (NoSuchElementException, TimeoutException, ElementNotFoundError) as error:
            duration = (time.time() - start_time) * 1000
            error_msg = f'Element not found with {strategy}: {selector}'
            logger.error(f'{error_msg}, duration={duration:.0f}ms')
            raise ElementNotFoundError(error_msg) from error

    def find_elements(
        self,
        selector: str,
        strategy: LocatorStrategy = 'id'
    ) -> List[WebElement]:
        """
        Find multiple elements with specified strategy.
        """
        start_time = time.time()
        try:
            by, value = self.get_locator(selector, strategy)
            elements = self.driver.find_elements(by, value)
            
            duration = (time.time() - start_time) * 1000
            return elements
        except Exception as error:
            duration = (time.time() - start_time) * 1000
            logger.error(f'Error finding elements with {strategy}: {selector}, duration={duration:.0f}ms')
            return []
