"""
Clipboard Helper - Clipboard operations for OTP transfer.

This class provides methods to copy OTP codes to the Android
clipboard and paste them into apps.
"""

import time
import base64
import subprocess
from typing import Optional

from .gmail_configs import GmailAutomationConfig


class ClipboardHelper:
    """Helper for Android clipboard operations."""
    
    def __init__(self, driver, device_id: str, config: Optional[GmailAutomationConfig] = None):
        """
        Initialize clipboard helper.
        
        Args:
            driver: Appium WebDriver instance
            device_id: Android device ID for ADB commands
            config: Gmail automation configuration
        """
        self.driver = driver
        self.device_id = device_id
        self.config = config or GmailAutomationConfig()
        self._last_set_content: Optional[str] = None
    
    def _run_adb(self, *args) -> subprocess.CompletedProcess:
        """Run an ADB command."""
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    def set_clipboard(self, text: str) -> bool:
        """
        Set the device clipboard content.
        
        Args:
            text: Text to copy to clipboard
            
        Returns:
            True if successful
        """
        try:
            # Method 1: Use Appium mobile: setClipboard
            encoded = base64.b64encode(text.encode()).decode()
            self.driver.execute_script('mobile: setClipboard', {
                'content': encoded,
                'contentType': 'plaintext'
            })
            self._last_set_content = text
            return True
            
        except Exception:
            try:
                # Method 2: Use ADB broadcast (requires Clipper app)
                result = self._run_adb(
                    'shell', 'am', 'broadcast',
                    '-a', 'clipper.set',
                    '-e', 'text', text
                )
                if result.returncode == 0:
                    self._last_set_content = text
                    return True
            except Exception:
                pass
            
            return False
    
    def get_clipboard(self) -> Optional[str]:
        """
        Get the current clipboard content.
        
        Returns:
            Clipboard text or None
        """
        try:
            # Use Appium mobile: getClipboard
            encoded = self.driver.execute_script('mobile: getClipboard')
            if encoded:
                return base64.b64decode(encoded).decode()
            return None
            
        except Exception:
            # Return last known content as fallback
            return self._last_set_content
    
    def paste_from_clipboard(self, element=None) -> bool:
        """
        Paste clipboard content into the focused element.
        
        This performs a long-press to show context menu, then taps Paste.
        
        Args:
            element: Optional element to paste into (will be focused first)
            
        Returns:
            True if paste action was performed
        """
        try:
            # If element provided, tap and long-press it
            if element:
                element.click()
                time.sleep(0.3)
            
            # Get current focused element location for long press
            # Use Appium's long press action
            try:
                from appium.webdriver.common.touch_action import TouchAction
                
                if element:
                    action = TouchAction(self.driver)
                    action.long_press(element).release().perform()
                else:
                    # Long press at center of screen
                    size = self.driver.get_window_size()
                    center_x = size['width'] // 2
                    center_y = size['height'] // 2
                    action = TouchAction(self.driver)
                    action.long_press(x=center_x, y=center_y).release().perform()
                
                time.sleep(0.5)
                
            except ImportError:
                # Fallback for newer Appium versions
                if element:
                    self.driver.execute_script('mobile: longClickGesture', {
                        'elementId': element.id,
                        'duration': 1000
                    })
                else:
                    size = self.driver.get_window_size()
                    self.driver.execute_script('mobile: longClickGesture', {
                        'x': size['width'] // 2,
                        'y': size['height'] // 2,
                        'duration': 1000
                    })
                time.sleep(0.5)
            
            # Find and tap Paste option
            from appium.webdriver.common.appiumby import AppiumBy
            
            paste_options = [
                "Paste",
                "PASTE",
                "paste",
            ]
            
            for paste_text in paste_options:
                try:
                    paste_btn = self.driver.find_element(
                        AppiumBy.XPATH,
                        f"//android.widget.TextView[contains(@text, '{paste_text}')]"
                    )
                    paste_btn.click()
                    time.sleep(0.3)
                    return True
                except Exception:
                    continue
            
            # Fallback: Try sending Ctrl+V keycode
            self._run_adb('shell', 'input', 'keyevent', '279')  # KEYCODE_PASTE
            time.sleep(0.3)
            return True
            
        except Exception:
            return False
    
    def type_text_directly(self, text: str) -> bool:
        """
        Type text directly using ADB input.
        
        This is a fallback when clipboard doesn't work.
        
        Args:
            text: Text to type
            
        Returns:
            True if successful
        """
        try:
            # Escape special characters for shell
            escaped = text.replace(' ', '%s').replace("'", "\\'")
            result = self._run_adb('shell', 'input', 'text', escaped)
            return result.returncode == 0
        except Exception:
            return False
