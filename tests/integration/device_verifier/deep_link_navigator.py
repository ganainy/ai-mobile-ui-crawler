"""Deep link navigation utility for Appium action verification tests.

Uses ADB deep links to navigate directly to action screens in the Flutter test app,
eliminating the need for hub tile coordinate calibration.
"""

import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DeepLinkNavigator:
    """Navigates to action screens using ADB deep link intents."""
    
    # Deep link scheme and package for the Flutter test app
    DEEP_LINK_SCHEME = "app://testapp"
    APP_PACKAGE = "com.example.appium_action_test_app"
    
    def __init__(self, device_id: str, app_package: Optional[str] = None):
        """
        Initialize the deep link navigator.
        
        Args:
            device_id: ADB device serial (e.g., 'emulator-5554')
            app_package: Optional app package override
        """
        self.device_id = device_id
        self.app_package = app_package or self.APP_PACKAGE
    
    def navigate_to(self, route: str, timeout_ms: int = 5000) -> bool:
        """
        Navigate directly to an action screen using ADB deep link intent.
        
        Args:
            route: The deep link route (e.g., '/tap', '/double_tap')
            timeout_ms: Timeout for the activity to start (default 5000ms)
            
        Returns:
            True if navigation succeeded, False otherwise
        """
        if "://" in route:
            deep_link_uri = route
        else:
            # Ensure route starts with /
            if not route.startswith('/'):
                route = f'/{route}'
            deep_link_uri = f"{self.DEEP_LINK_SCHEME}{route}"
        
        cmd = [
            'adb', '-s', self.device_id,
            'shell', 'am', 'start',
            '-W',  # Wait for launch to complete
            '-a', 'android.intent.action.VIEW',
            '-d', deep_link_uri,
            self.app_package
        ]
        
        logger.info(f"Navigating to {deep_link_uri} via deep link")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_ms / 1000 + 5  # Add buffer for subprocess
            )
            
            if result.returncode != 0:
                logger.error(f"Deep link navigation failed: {result.stderr}")
                return False
            
            # Check for success indicators in output
            if "Error" in result.stdout or "Error" in result.stderr:
                logger.error(f"Deep link error: {result.stdout} {result.stderr}")
                return False
            
            logger.info(f"Successfully navigated to {route}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"Deep link navigation timed out for {route}")
            return False
        except Exception as e:
            logger.error(f"Deep link navigation error: {e}")
            return False
    
    def force_stop_app(self) -> bool:
        """Force stop the app to reset state."""
        cmd = [
            'adb', '-s', self.device_id,
            'shell', 'am', 'force-stop',
            self.app_package
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Force stop failed: {e}")
            return False
