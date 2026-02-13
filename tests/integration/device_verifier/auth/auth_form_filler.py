import time
import subprocess
from typing import Tuple
from appium.webdriver.common.appiumby import AppiumBy
from .auth_configs import TestCredentials

class AuthFormFiller:
    """Fills authentication forms using Appium and ADB."""
    
    def __init__(self, gesture_handler, screen_dims: Tuple[int, int]):
        self.gestures = gesture_handler
        self.width, self.height = screen_dims
        self._driver = gesture_handler.driver.get_driver()

    def _get_device_id(self) -> str:
        """Helper to get device ID for ADB commands."""
        caps = self._driver.capabilities
        return caps.get('deviceName', '')

    def _find_and_tap(self, accessibility_id: str, timeout: int = 5):
        """Find element by accessibility ID and tap it."""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        try:
            el = WebDriverWait(self._driver, timeout).until(
                EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, accessibility_id))
            )
            # Get element location for a real tap gesture
            loc = el.location
            size = el.size
            # Tap center
            tap_x = loc['x'] + size['width'] // 2
            tap_y = loc['y'] + size['height'] // 2
            self.gestures.tap_at(tap_x, tap_y)
        except Exception as e:
            # Save screenshot for debugging
            timestamp = int(time.time())
            filename = f"failure_filler_{accessibility_id}_{timestamp}.png"
            self._driver.save_screenshot(filename)
            print(f"[DEBUG] Screenshot saved to {filename}")
            raise e

    def clear_text(self):
        """Clear text in the currently focused field."""
        device_id = self._get_device_id()
        # Select all and delete is a common way to clear via ADB
        # Ctrl+A (29 + 57), then Backspace (67)
        cmd_base = ['adb']
        if device_id:
            cmd_base.extend(['-s', device_id])
            
        subprocess.run(cmd_base + ['shell', 'input', 'keyevent', '29', '--meta', '113'], timeout=5) # Ctrl+A
        subprocess.run(cmd_base + ['shell', 'input', 'keyevent', '67'], timeout=5) # Delete
        
        # Alternative for some Android versions: long press and delete or just backspaces
        # For simplicity in this mock app, we'll just send a bunch of backspaces
        subprocess.run(cmd_base + ['shell', 'input', 'keyevent', 'KEYCODE_MOVE_END'], timeout=2)
        for _ in range(30):
            subprocess.run(cmd_base + ['shell', 'input', 'keyevent', '67'], timeout=1)

    def type_text(self, text: str, clear: bool = True):
        """Type text using ADB for reliability."""
        if clear:
            self.clear_text()
            
        device_id = self._get_device_id()
        cmd = ['adb']
        if device_id:
            cmd.extend(['-s', device_id])
        
        # ADB 'input text' doesn't handle spaces well unless quoted/escaped.
        # Replacing spaces with %s is the standard way for 'input text'.
        escaped_text = text.replace(" ", "%s")
        cmd.extend(['shell', 'input', 'text', escaped_text])
        
        try:
            subprocess.run(cmd, timeout=10)
        except Exception:
            # Fallback to Appium if ADB fails
            try:
                # Appium's 'mobile: type' usually handles spaces fine
                self._driver.execute_script('mobile: type', {'text': text})
            except Exception:
                pass


    def press_tab(self):
        """Press TAB key using ADB."""
        device_id = self._get_device_id()
        cmd = ['adb']
        if device_id:
            cmd.extend(['-s', device_id])
        cmd.extend(['shell', 'input', 'keyevent', '61']) # 61 is TAB
        subprocess.run(cmd, timeout=5)

    def fill_signup_form(self, creds: TestCredentials) -> bool:
        """Fill signup form with credentials."""
        # 1. Tap name field (Index 1)
        self._find_and_tap_by_xpath("(//android.widget.EditText)[1]")
        time.sleep(0.5)
        self.type_text(creds.name)
        
        # 2. Tap email field (Index 2)
        self._find_and_tap_by_xpath("(//android.widget.EditText)[2]")
        time.sleep(0.5)
        self.type_text(creds.email)
        
        # 3. Tap password field (Index 3)
        self._find_and_tap_by_xpath("(//android.widget.EditText)[3]")
        time.sleep(0.5)
        self.type_text(creds.password)
        
        # 4. Tap terms checkbox
        self._find_and_tap('checkbox_terms')
        time.sleep(0.3)
        
        try:
            self._driver.hide_keyboard()
        except:
            pass
        
        return True
    
    def fill_signin_form(self, creds: TestCredentials) -> bool:
        """Fill sign-in form with credentials."""
        # 1. Tap email field (Index 1)
        self._find_and_tap_by_xpath("(//android.widget.EditText)[1]")
        time.sleep(0.5)
        self.type_text(creds.email)
        
        # 2. Tap password field (Index 2)
        self._find_and_tap_by_xpath("(//android.widget.EditText)[2]")
        time.sleep(0.5)
        self.type_text(creds.password)
        
        try:
            self._driver.hide_keyboard()
        except:
            pass
        
        return True
    
    def enter_otp(self, otp: str = "123456") -> bool:
        """Enter OTP on OTP screen by typing."""
        self._find_and_tap_by_xpath("(//android.widget.EditText)[1]")
        time.sleep(0.5)
        self.type_text(otp)
        return True
    
    def paste_otp(self) -> bool:
        """Paste OTP from clipboard into the OTP field."""
        try:
            # 1. Tap and long-press the OTP field
            xpath = "(//android.widget.EditText)[1]"
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            el = WebDriverWait(self._driver, 5).until(
                EC.presence_of_element_located((AppiumBy.XPATH, xpath))
            )
            
            loc = el.location
            size = el.size
            tap_x = loc['x'] + size['width'] // 2
            tap_y = loc['y'] + size['height'] // 2
            
            # Long press via Appium gesture
            self._driver.execute_script('mobile: longClickGesture', {
                'x': tap_x,
                'y': tap_y,
                'duration': 1000
            })
            time.sleep(0.5)
            
            # 2. Look for "Paste" or "Einfügen" (since user has German UI)
            paste_options = ["Paste", "PASTE", "paste", "Einfügen", "EINFÜGEN"]
            for opt in paste_options:
                try:
                    paste_btn = self._driver.find_element(
                        AppiumBy.XPATH, 
                        f"//android.widget.TextView[contains(@text, '{opt}')]"
                    )
                    paste_btn.click()
                    return True
                except:
                    continue
            
            # Fallback: ADB keyevent for paste (279)
            device_id = self._get_device_id()
            cmd = ['adb']
            if device_id:
                cmd.extend(['-s', device_id])
            cmd.extend(['shell', 'input', 'keyevent', '279'])
            subprocess.run(cmd, timeout=5)
            
            return True
        except Exception as e:
            print(f"[DEBUG] Paste OTP failed: {e}")
            return False

    def enter_captcha(self, solution: str = "TESTCAPTCHA") -> bool:
        """Enter CAPTCHA on Captcha screen."""
        self._find_and_tap_by_xpath("(//android.widget.EditText)[1]")
        time.sleep(0.5)
        self.type_text(solution)
        return True

    def _find_and_tap_by_xpath(self, xpath: str, timeout: int = 5):
        """Find element by XPATH and tap it."""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        try:
            el = WebDriverWait(self._driver, timeout).until(
                EC.presence_of_element_located((AppiumBy.XPATH, xpath))
            )
            loc = el.location
            size = el.size
            tap_x = loc['x'] + size['width'] // 2
            tap_y = loc['y'] + size['height'] // 2
            self.gestures.tap_at(tap_x, tap_y)
        except Exception as e:
            timestamp = int(time.time())
            filename = f"failure_xpath_{timestamp}.png"
            self._driver.save_screenshot(filename)
            raise e
    
    def submit(self) -> bool:
        """Submit the current form by tapping the submit/verify button."""
        self._find_and_tap('btn_submit')
        return True
