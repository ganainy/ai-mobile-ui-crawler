"""App context manager for tracking and recovering app state."""

from typing import List, Optional

from mobile_crawler.infrastructure.appium_driver import AppiumDriver


class AppContextManager:
    """Manages app context, detects context loss, and handles recovery."""

    def __init__(self, appium_driver: AppiumDriver, target_package: str, allowed_packages: Optional[List[str]] = None):
        """Initialize app context manager.

        Args:
            appium_driver: Appium driver instance
            target_package: The main app package being tested
            allowed_packages: Additional packages allowed (e.g., browsers, OAuth)
        """
        self.appium_driver = appium_driver
        self.target_package = target_package
        self.allowed_packages = allowed_packages or []
        self.allowed_packages.append(target_package)  # Always allow target

        # State tracking
        self.current_package: Optional[str] = None
        self.context_loss_count = 0
        self.context_recovery_count = 0

    def update_context(self) -> str:
        """Update and return the current package context.

        Returns:
            Current package name
        """
        self.current_package = self._get_current_package()
        return self.current_package

    def check_context_loss(self) -> bool:
        """Check if context has been lost (current package not in allowed list).

        Returns:
            True if context lost, False otherwise
        """
        if self.current_package is None:
            return True

        return self.current_package not in self.allowed_packages

    def handle_context_loss(self) -> bool:
        """Attempt to recover from context loss.

        Tries pressing back up to 3 times, then relaunches app.

        Returns:
            True if recovery successful, False otherwise
        """
        if not self.check_context_loss():
            return True  # No loss to handle

        self.context_loss_count += 1

        # Try pressing back up to 3 times
        for _ in range(3):
            try:
                self.appium_driver.get_driver().back()
                # Wait a bit for navigation
                import time
                time.sleep(1.0)

                self.update_context()
                if not self.check_context_loss():
                    self.context_recovery_count += 1
                    return True
            except Exception:
                continue

        # If back presses didn't work, relaunch app
        try:
            self.appium_driver.get_driver().launch_app()
            # Wait for app to start
            import time
            time.sleep(2.0)

            self.update_context()
            if not self.check_context_loss():
                self.context_recovery_count += 1
                return True
        except Exception:
            pass

        return False  # Recovery failed

    def _get_current_package(self) -> str:
        """Get the current foreground package.

        Returns:
            Package name of current foreground app
        """
        driver = self.appium_driver.get_driver()

        # Try UiAutomator2 specific method first
        try:
            # UiAutomator2 has currentPackage capability
            return driver.capabilities.get('currentPackage', '')
        except (AttributeError, KeyError):
            pass

        # Fallback: parse from page source XML
        try:
            page_source = driver.page_source
            # Parse the root element's package attribute
            import xml.etree.ElementTree as ET
            root = ET.fromstring(page_source)
            return root.get('package', '')
        except Exception:
            return ''

    def get_stats(self) -> dict:
        """Get context management statistics.

        Returns:
            Dict with context loss and recovery counts
        """
        return {
            'context_loss_count': self.context_loss_count,
            'context_recovery_count': self.context_recovery_count,
            'current_package': self.current_package,
            'target_package': self.target_package,
            'allowed_packages': self.allowed_packages.copy()
        }