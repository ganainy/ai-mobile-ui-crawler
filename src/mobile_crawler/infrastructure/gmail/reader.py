"""
Gmail Reader module.
Responsible for parsing email content, extracting OTPs and links.
"""

import re
import time
import subprocess
from typing import Optional, List
from appium.webdriver.common.appiumby import AppiumBy

from dataclasses import dataclass

from .config import (
    GmailAutomationConfig,
    GMAIL_SELECTORS,
)


@dataclass
class OTPResult:
    """Result of an OTP extraction operation."""
    code: str
    timestamp: float
    sender: str
    pattern_matched: str = None
    context: str = None
    confidence: float = 1.0


@dataclass
class LinkResult:
    """Result of a verification link extraction operation."""
    url: str
    clicked: bool
    link_text: Optional[str] = None
    link_type: str = "URL_ONLY"
    is_deep_link: bool = False



# Error Classes
class GmailReadError(Exception):
    """Base error for Gmail reading failures."""
    pass


class NoEmailOpenError(GmailReadError):
    """No email is currently open to read."""
    pass


class OTPNotFoundError(GmailReadError):
    """OTP code not found in email content."""
    pass


class LinkNotFoundError(GmailReadError):
    """Verification link not found in email."""
    pass


class GmailReader:
    """Extract OTP codes and verification links from open emails."""
    
    def __init__(self, driver, device_id: str = None, config: Optional[GmailAutomationConfig] = None):
        """
        Initialize Gmail content reader.
        
        Args:
            driver: Appium WebDriver instance
            device_id: Android device ID for ADB commands
            config: Gmail automation configuration
        """
        self.driver = driver
        self.device_id = device_id
        self.config = config or GmailAutomationConfig()
    
    def _run_adb(self, *args) -> subprocess.CompletedProcess:
        """Run an ADB command."""
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    def _save_screenshot(self, name: str):
        """Save screenshot for debugging."""
        if self.config.capture_screenshots:
            try:
                filename = f"{self.config.screenshot_dir}/{name}_{int(time.time())}.png"
                self.driver.save_screenshot(filename)
            except Exception:
                pass
    
    def get_email_content(self) -> str:
        """
        Extract text content from currently open email.
        
        Returns:
            Plain text content of the email body
            
        Raises:
            NoEmailOpenError: If no email is currently open
        """
        all_text = []
        
        try:
            # Method 1: Try to get text from WebView (HTML emails)
            webviews = self.driver.find_elements(AppiumBy.ID, GMAIL_SELECTORS["webview"])
            if webviews:
                # Try getting text attribute
                text = webviews[0].get_attribute("text")
                if text:
                    all_text.append(text)
            
            # Method 2: Collect all TextView elements
            text_views = self.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.TextView")
            for tv in text_views:
                try:
                    text = tv.get_attribute("text") or tv.text
                    if text and len(text) > 2:
                        all_text.append(text)
                except Exception:
                    continue
            
            # Method 3: Try scrolling and collecting more text
            if not all_text:
                self._scroll_email()
                text_views = self.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.TextView")
                for tv in text_views:
                    try:
                        text = tv.get_attribute("text") or tv.text
                        if text and len(text) > 2:
                            all_text.append(text)
                    except Exception:
                        continue
            
            if not all_text:
                raise NoEmailOpenError("Could not extract any text from email")
            
            return "\n".join(all_text)
            
        except NoEmailOpenError:
            raise
        except Exception as e:
            self._save_screenshot("get_email_content_failed")
            raise GmailReadError(f"Failed to get email content: {e}")
    
    def _scroll_email(self):
        """Scroll down in the email to reveal more content."""
        try:
            screen_size = self.driver.get_window_size()
            start_x = screen_size['width'] // 2
            start_y = screen_size['height'] * 3 // 4
            end_y = screen_size['height'] // 4
            
            # Use W3C Actions or script if driver supports it, keeping simple swipe for now assuming Appium helper
            # or standard W3C actions are available. If not, this might need update.
            # Using ADB swipe for reliability as 'swipe' method is sometimes deprecated
            if self.device_id:
                self._run_adb('shell', 'input', 'swipe', str(start_x), str(start_y), str(start_x), str(end_y), '500')
            else:
                 # Fallback to driver swipe if available (deprecated in generic WD but present in AppiumDriver)
                if hasattr(self.driver, 'swipe'):
                    self.driver.swipe(start_x, start_y, start_x, end_y, 500)
                else: 
                    # W3C action fallback? For now let's hope ADB works or 'swipe' exists.
                    pass
            
            time.sleep(0.5)
        except Exception:
            pass
    
    def extract_otp(self, custom_patterns: List[str] = None) -> Optional[OTPResult]:
        """
        Extract OTP code from currently open email.
        
        Args:
            custom_patterns: Additional regex patterns to try
            
        Returns:
            OTPResult if found, None otherwise
        """
        try:
            content = self.get_email_content()
            
            # Combine default and custom patterns
            patterns = (custom_patterns or []) + self.config.otp_patterns
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    code = match.group(1)
                    
                    # Calculate confidence based on pattern type
                    confidence = 0.9 if "code" in pattern.lower() or "otp" in pattern.lower() else 0.7
                    
                    # Get context (surrounding text)
                    start = max(0, match.start() - 30)
                    end = min(len(content), match.end() + 30)
                    context = content[start:end]
                    
                    return OTPResult(
                        code=code,
                        timestamp=time.time(),
                        sender="unknown", # We'll need to extract sender separately if needed
                        # Removed extra fields matching original file but kept dataclass compat
                    )
            
            return None
            
        except NoEmailOpenError:
            raise
        except Exception as e:
            self._save_screenshot("extract_otp_failed")
            raise GmailReadError(f"Failed to extract OTP: {e}")
    
    def extract_verification_link(self, custom_patterns: List[str] = None) -> Optional[LinkResult]:
        """
        Extract verification link from currently open email.
        
        Args:
            custom_patterns: Additional regex patterns for URLs
            
        Returns:
            LinkResult if found, None otherwise
        """
        try:
            content = self.get_email_content()
            
            # Combine default and custom patterns
            patterns = (custom_patterns or []) + self.config.link_patterns
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    url = match.group(1)
                    
                    # Determine if it's a deep link
                    is_deep_link = not url.startswith("http")
                    
                    return LinkResult(
                        url=url,
                        clicked=False
                    )
            
            return None
            
        except NoEmailOpenError:
            raise
        except Exception as e:
            self._save_screenshot("extract_link_failed")
            raise GmailReadError(f"Failed to extract verification link: {e}")
    
    def find_verification_button(self) -> Optional[object]:
        """
        Find a verification button in the email.
        
        Returns:
            WebElement if found, None otherwise
        """
        for button_text in GMAIL_SELECTORS["verify_button_texts"]:
            try:
                # Try finding by text
                xpath = f"//android.widget.Button[contains(@text, '{button_text}')]"
                buttons = self.driver.find_elements(AppiumBy.XPATH, xpath)
                if buttons:
                    return buttons[0]
                
                # Try finding TextView that looks like a link
                xpath = f"//android.widget.TextView[contains(@text, '{button_text}')]"
                links = self.driver.find_elements(AppiumBy.XPATH, xpath)
                if links:
                    return links[0]
                    
            except Exception:
                continue
        
        return None
    
    def click_verification_link(self) -> bool:
        """
        Find and click the verification link/button in the email.
        
        Returns:
            True if link found and clicked, False otherwise
        """
        try:
            # First try to find and click a verification button
            button = self.find_verification_button()
            if button:
                button.click()
                time.sleep(2)
                return True
            
            # Fallback: Extract link and trigger via ADB
            link = self.extract_verification_link()
            if link:
                return self.extract_and_trigger_link(link.url)
            
            return False
            
        except Exception as e:
            self._save_screenshot("click_link_failed")
            raise GmailReadError(f"Failed to click verification link: {e}")
    
    def extract_and_trigger_link(self, url: str) -> bool:
        """
        Trigger a URL via ADB VIEW intent.
        
        Args:
            url: The URL to open
            
        Returns:
            True if successful
        """
        try:
            result = self._run_adb(
                'shell', 'am', 'start',
                '-a', 'android.intent.action.VIEW',
                '-d', url
            )
            time.sleep(2)
            return result.returncode == 0
        except Exception:
            return False
    
    def copy_otp_to_clipboard(self) -> bool:
        """
        Extract OTP and copy it to device clipboard.
        
        Returns:
            True if OTP found and copied, False otherwise
        """
        try:
            otp_result = self.extract_otp()
            if not otp_result:
                raise OTPNotFoundError("No OTP found in email")
            
            # Use Appium to set clipboard
            import base64
            encoded = base64.b64encode(otp_result.code.encode()).decode()
            self.driver.execute_script('mobile: setClipboard', {
                'content': encoded,
                'contentType': 'plaintext'
            })
            
            return True
            
        except OTPNotFoundError:
            raise
        except Exception as e:
            self._save_screenshot("copy_otp_failed")
            raise GmailReadError(f"Failed to copy OTP to clipboard: {e}")
