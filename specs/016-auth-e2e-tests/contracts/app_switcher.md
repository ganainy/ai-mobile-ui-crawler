# App Context Switcher Contract

**Module**: `tests/integration/device_verifier/gmail/app_switcher.py`
**Purpose**: Switch between apps reliably during email verification workflows

## Interface

```python
from typing import Optional
from dataclasses import dataclass

@dataclass
class AppState:
    """Current state of an app."""
    package: str
    activity: Optional[str]
    is_foreground: bool

class AppSwitcher:
    """Switch between test app and Gmail reliably."""
    
    def __init__(self, driver, device_id: str, test_app_package: str):
        """
        Initialize app switcher.
        
        Args:
            driver: Appium WebDriver instance
            device_id: Android device ID for ADB
            test_app_package: Package name of app under test
        """
        self.driver = driver
        self.device_id = device_id
        self.test_app_package = test_app_package
        self.gmail_package = "com.google.android.gm"
    
    def switch_to_gmail(self, wait_for_ready: bool = True) -> bool:
        """
        Switch to Gmail app.
        
        Args:
            wait_for_ready: Wait for Gmail to be fully loaded
            
        Returns:
            True if switch successful and Gmail visible
            
        Side Effects:
            - Pauses test app (may lose state in some cases)
        """
        pass
    
    def switch_to_test_app(self, wait_for_ready: bool = True) -> bool:
        """
        Switch back to the test app.
        
        Args:
            wait_for_ready: Wait for app to be fully loaded
            
        Returns:
            True if switch successful
            
        Note:
            App may be resumed or re-launched depending on state
        """
        pass
    
    def get_current_app(self) -> AppState:
        """
        Get information about the currently foreground app.
        
        Returns:
            AppState with current package and activity
        """
        pass
    
    def is_gmail_foreground(self) -> bool:
        """Check if Gmail is the current foreground app."""
        pass
    
    def is_test_app_foreground(self) -> bool:
        """Check if test app is the current foreground app."""
        pass
    
    def ensure_gmail(self) -> bool:
        """
        Ensure Gmail is in foreground, switching if needed.
        
        Returns:
            True if Gmail is now in foreground
        """
        pass
    
    def ensure_test_app(self) -> bool:
        """
        Ensure test app is in foreground, switching if needed.
        
        Returns:
            True if test app is now in foreground
        """
        pass
    
    def press_back_until(self, package: str, max_attempts: int = 5) -> bool:
        """
        Press back button repeatedly until target app is foreground.
        
        Args:
            package: Target package to reach
            max_attempts: Maximum back presses to try
            
        Returns:
            True if target reached
            
        Note:
            Useful when deep link opens in wrong app
        """
        pass
```

## Implementation Notes

### App Launching

```python
# Method 1: ADB am start (more reliable for cold start)
subprocess.run([
    'adb', '-s', device_id, 'shell', 'am', 'start',
    '-n', f'{package}/.{activity}'
])

# Method 2: Appium activate_app (works if app in recents)
driver.activate_app(package)
```

### Getting Current App

```python
# Method 1: Use driver.current_package
current = driver.current_package

# Method 2: ADB dumpsys (more reliable)
result = subprocess.run([
    'adb', '-s', device_id, 'shell', 
    'dumpsys', 'activity', 'activities',
    '|', 'grep', 'mResumedActivity'
])
```

## Usage Example

```python
switcher = AppSwitcher(driver, device_id, "com.example.auth_test_app")

# Start in test app, trigger email send
# ...

# Switch to Gmail to read email
assert switcher.switch_to_gmail()
# Read email with GmailReader...

# Return to test app to enter OTP
assert switcher.switch_to_test_app()
# Paste OTP...
```
