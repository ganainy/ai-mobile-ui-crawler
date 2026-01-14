"""
App Switcher - Switch between test app and Gmail reliably.
"""

import time
import subprocess
from typing import Optional
from dataclasses import dataclass

from .config import GMAIL_PACKAGE, GMAIL_ACTIVITY, GmailAutomationConfig


@dataclass
class AppState:
    """Current state of an app."""
    package: str
    activity: Optional[str]
    is_foreground: bool


class AppSwitcher:
    """Switch between test app and Gmail reliably."""
    
    def __init__(
        self,
        driver,
        device_id: str,
        test_app_package: str,
        test_app_activity: Optional[str] = None,
        config: Optional[GmailAutomationConfig] = None
    ):
        """
        Initialize app switcher.
        
        Args:
            driver: Appium WebDriver instance
            device_id: Android device ID for ADB
            test_app_package: Package name of app under test
            test_app_activity: Main activity of test app (optional)
            config: Gmail automation configuration
        """
        self.driver = driver
        self.device_id = device_id
        self.test_app_package = test_app_package
        self.test_app_activity = test_app_activity
        self.gmail_package = GMAIL_PACKAGE
        self.gmail_activity = GMAIL_ACTIVITY
        self.config = config or GmailAutomationConfig()
    
    def _run_adb(self, *args) -> subprocess.CompletedProcess:
        """Run an ADB command."""
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    def switch_to_gmail(self, wait_for_ready: bool = True) -> bool:
        """
        Switch to Gmail app.
        
        Args:
            wait_for_ready: Wait for Gmail to be fully loaded
            
        Returns:
            True if switch successful and Gmail visible
        """
        try:
            # Force stop first to reset UI state (back to inbox)
            self._run_adb('shell', 'am', 'force-stop', self.gmail_package)
            time.sleep(0.5)

            # Launch Gmail via ADB
            result = self._run_adb(
                'shell', 'am', 'start', '-n',
                f'{self.gmail_package}/{self.gmail_activity}'
            )
            
            if result.returncode != 0:
                return False
            
            if wait_for_ready:
                time.sleep(self.config.app_switch_delay_seconds)
                return self.is_gmail_foreground()
            
            return True
            
        except Exception:
            return False

    
    def switch_to_test_app(self, wait_for_ready: bool = True) -> bool:
        """
        Switch back to the test app.
        
        Args:
            wait_for_ready: Wait for app to be fully loaded
            
        Returns:
            True if switch successful
        """
        try:
            if self.test_app_activity:
                # Launch with specific activity
                result = self._run_adb(
                    'shell', 'am', 'start', '-n',
                    f'{self.test_app_package}/{self.test_app_activity}'
                )
            else:
                # Try using Appium activate_app
                try:
                    self.driver.activate_app(self.test_app_package)
                except Exception:
                    # Fallback to monkey launch
                    result = self._run_adb(
                        'shell', 'monkey', '-p', self.test_app_package,
                        '-c', 'android.intent.category.LAUNCHER', '1'
                    )
            
            if wait_for_ready:
                time.sleep(self.config.app_switch_delay_seconds)
                return self.is_test_app_foreground()
            
            return True
            
        except Exception:
            return False
    
    def get_current_app(self) -> AppState:
        """
        Get information about the currently foreground app.
        
        Returns:
            AppState with current package and activity
        """
        try:
            # Get current package from driver
            current_package = self.driver.current_package
            current_activity = None
            
            try:
                current_activity = self.driver.current_activity
            except Exception:
                pass
            
            is_foreground = current_package is not None
            
            return AppState(
                package=current_package or "",
                activity=current_activity,
                is_foreground=is_foreground
            )
            
        except Exception:
            # Fallback to ADB
            try:
                result = self._run_adb(
                    'shell', 'dumpsys', 'activity', 'activities',
                    '|', 'grep', 'mResumedActivity'
                )
                # Parse output to extract package
                output = result.stdout
                if self.gmail_package in output:
                    return AppState(
                        package=self.gmail_package,
                        activity=None,
                        is_foreground=True
                    )
                elif self.test_app_package in output:
                    return AppState(
                        package=self.test_app_package,
                        activity=None,
                        is_foreground=True
                    )
            except Exception:
                pass
            
            return AppState(package="", activity=None, is_foreground=False)
    
    def is_gmail_foreground(self) -> bool:
        """Check if Gmail is the current foreground app."""
        state = self.get_current_app()
        return state.package == self.gmail_package
    
    def is_test_app_foreground(self) -> bool:
        """Check if test app is the current foreground app."""
        state = self.get_current_app()
        return state.package == self.test_app_package
    
    def ensure_gmail(self) -> bool:
        """
        Ensure Gmail is in foreground, switching if needed.
        
        Returns:
            True if Gmail is now in foreground
        """
        if self.is_gmail_foreground():
            return True
        return self.switch_to_gmail()
    
    def ensure_test_app(self) -> bool:
        """
        Ensure test app is in foreground, switching if needed.
        
        Returns:
            True if test app is now in foreground
        """
        if self.is_test_app_foreground():
            return True
        return self.switch_to_test_app()
    
    def press_back_until(self, package: str, max_attempts: int = 5) -> bool:
        """
        Press back button repeatedly until target app is foreground.
        
        Args:
            package: Target package to reach
            max_attempts: Maximum back presses to try
            
        Returns:
            True if target reached
        """
        for _ in range(max_attempts):
            state = self.get_current_app()
            if state.package == package:
                return True
            
            # Press back
            self.driver.press_keycode(4)  # KEYCODE_BACK
            time.sleep(0.5)
        
        return self.get_current_app().package == package

    def wait_for_app_to_handle_link(self, timeout: int = 15) -> bool:
        """
        Wait until the test app becomes foreground after a link click.
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            True if app became foreground
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_test_app_foreground():
                return True
            time.sleep(0.5)
        return False
