"""Utility for force-stopping and restarting the test application."""

import subprocess
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AppRestarter:
    """Handles app process management via ADB."""

    def __init__(self, device_id: str, app_package: str, main_activity: str):
        """Initialize app restarter.
        
        Args:
            device_id: ADB device ID
            app_package: App package name (e.g., com.example.flutter_application_1)
            main_activity: Main hub activity name
        """
        self.device_id = device_id
        self.app_package = app_package
        self.main_activity = main_activity

    def restart_app(self) -> bool:
        """Force-stop and restart the app, then wait for stabilization.
        
        Returns:
            True if restart successful, False otherwise
        """
        try:
            logger.info(f"Restarting app '{self.app_package}' on device '{self.device_id}'")
            
            # 1. Force stop
            subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'am', 'force-stop', self.app_package],
                capture_output=True, timeout=10
            )
            
            # Short pause for process to die
            time.sleep(1)
            
            # 2. Start main activity
            component = f"{self.app_package}/{self.main_activity}"
            result = subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'am', 'start', '-n', component],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to start app: {result.stderr}")
                return False
                
            # Allow app to initialize and show hub
            time.sleep(3)
            return True
            
        except subprocess.SubprocessError as e:
            logger.error(f"Subprocess error during app restart: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during app restart: {e}")
            return False
