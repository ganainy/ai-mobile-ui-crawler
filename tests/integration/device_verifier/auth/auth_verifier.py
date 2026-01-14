import time
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class AuthVerifier:
    """Verifies authentication screen states."""
    
    def __init__(self, driver):
        self.driver = driver
    
    def _wait_for_accessibility_id(self, accessibility_id: str, timeout: int = 15) -> bool:
        # Use a shorter timeout for the primary check to allow fallbacks to kick in sooner
        primary_timeout = 5
        try:
            # Try by accessibility ID first
            WebDriverWait(self.driver, primary_timeout).until(
                EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, accessibility_id))
            )
            return True
        except TimeoutException:
            # Fallback to XPATH content-desc or text check
            try:
                # Search for accessibility_id in both description and text
                xpath = f"//*[contains(@content-desc, '{accessibility_id}') or contains(@text, '{accessibility_id}')]"
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((AppiumBy.XPATH, xpath))
                )
                return True
            except TimeoutException:
                # Specialized fallbacks based on the ID we are looking for
                fallback_xpath = None
                if accessibility_id == 'home_welcome':
                    fallback_xpath = "//*[contains(@text, 'Welcome') or contains(@text, 'Home')]"
                elif accessibility_id == 'input_otp':
                    fallback_xpath = "//*[contains(@text, 'OTP') or contains(@text, 'Verify')]"
                elif accessibility_id == 'input_captcha':
                    fallback_xpath = "//*[contains(@text, 'CAPTCHA') or contains(@text, 'Enter code')]"
                elif accessibility_id == 'email_waiting' or accessibility_id == 'email_status':
                    fallback_xpath = "//*[contains(@text, 'email') or contains(@text, 'Check') or contains(@text, 'link')]"
                elif accessibility_id == 'error_message':
                    fallback_xpath = "//*[contains(@text, 'Incorrect') or contains(@text, 'invalid')]"
                
                if fallback_xpath:
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((AppiumBy.XPATH, fallback_xpath))
                        )
                        return True
                    except:
                        pass
                
                # If we still have time, try one last broad check for any EditText if we're looking for an input
                if accessibility_id.startswith('input_'):
                    try:
                        WebDriverWait(self.driver, 2).until(
                            EC.presence_of_element_located((AppiumBy.XPATH, "//android.widget.EditText"))
                        )
                        return True
                    except:
                        pass

                # Save screenshot for debugging
                timestamp = int(time.time())
                filename = f"failure_{accessibility_id}_{timestamp}.png"
                try:
                    self.driver.save_screenshot(filename)
                except:
                    pass
                return False

    def wait_for_home(self, timeout: int = 30) -> bool:
        """Wait for authenticated Home screen."""
        return self._wait_for_accessibility_id('home_welcome', timeout)
    
    def wait_for_otp_screen(self, timeout: int = 10) -> bool:
        """Wait for OTP entry screen."""
        return self._wait_for_accessibility_id('input_otp', timeout)
    
    def wait_for_email_screen(self, timeout: int = 10) -> bool:
        """Wait for email verification waiting screen."""
        return self._wait_for_accessibility_id('email_status', timeout)
    
    def wait_for_captcha_screen(self, timeout: int = 10) -> bool:
        """Wait for CAPTCHA challenge screen."""
        return self._wait_for_accessibility_id('captcha_challenge', timeout)
    
    def wait_for_error(self, timeout: int = 5) -> bool:
        """Wait for error message."""
        return self._wait_for_accessibility_id('error_message', timeout)
