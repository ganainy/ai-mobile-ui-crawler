"""
Appium session management and lifecycle control.
"""
import logging
import time
from typing import Dict, Optional, Any, List
from urllib.parse import urlparse

from appium import webdriver
from appium.options.android import UiAutomator2Options

from infrastructure.appium_error_handler import (
    AppiumError,
    is_session_terminated,
)
from infrastructure.capability_builder import AppiumCapabilities

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Manages Appium session lifecycle, including initialization, validation, and recovery.
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0, implicit_wait: int = 5000):
        """
        Initialize SessionManager.
        
        Args:
            max_retries: Maximum retry attempts for operations
            retry_delay: Delay between retries in seconds
            implicit_wait: Implicit wait timeout in milliseconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.implicit_wait = implicit_wait
        
        self.driver: Optional[webdriver.Remote] = None
        self.last_capabilities: Optional[AppiumCapabilities] = None
        self.last_appium_url: Optional[str] = None
        
        # App context state
        self.target_package: Optional[str] = None
        self.target_activity: Optional[str] = None
        self.allowed_external_packages: List[str] = []
        self.consecutive_context_failures: int = 0
        self._current_implicit_wait: Optional[float] = None

    def initialize_driver(
        self,
        capabilities: AppiumCapabilities,
        appium_url: str = 'http://localhost:4723',
        context_config: Optional[Dict[str, Any]] = None
    ) -> webdriver.Remote:
        """
        Initialize WebDriver session with capabilities.
        """
        start_time = time.time()
        
        try:
            logger.debug(
                f'Initializing Appium session: platform={capabilities.get("platformName")}, '
                f'automationName={capabilities.get("appium:automationName")}, '
                f'deviceName={capabilities.get("appium:deviceName")}'
            )
            
            parsed_url = urlparse(appium_url)
            server_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            options = UiAutomator2Options()
            try:
                options.load_capabilities(capabilities)
            except Exception as load_error:
                logger.warning(f'load_capabilities failed, trying direct assignment: {load_error}')
                for key, value in capabilities.items():
                    if value is not None:
                        try:
                            if hasattr(options, key):
                                setattr(options, key, value)
                            elif key.startswith('appium:'):
                                option_key = key.replace('appium:', '')
                                if hasattr(options, option_key):
                                    setattr(options, option_key, value)
                        except Exception:
                            pass
            
            self.driver = webdriver.Remote(
                command_executor=server_url,
                options=options
            )
            
            self.last_capabilities = capabilities
            self.last_appium_url = appium_url
            
            if context_config:
                self.target_package = context_config.get('targetPackage')
                self.target_activity = context_config.get('targetActivity')
                self.allowed_external_packages = context_config.get('allowedExternalPackages', [])
            else:
                self.target_package = capabilities.get('appium:appPackage')
                self.target_activity = capabilities.get('appium:appActivity')
                self.allowed_external_packages = []
            
            self.consecutive_context_failures = 0
            
            implicit_wait_seconds = self.implicit_wait / 1000.0
            self.driver.implicitly_wait(implicit_wait_seconds)
            self._current_implicit_wait = implicit_wait_seconds
            
            self.apply_performance_settings()
            
            duration = (time.time() - start_time) * 1000
            logger.debug(f'Appium session initialized: sessionId={self.driver.session_id}, duration={duration:.0f}ms')
            
            return self.driver
            
        except Exception as error:
            duration = (time.time() - start_time) * 1000
            logger.error(f'Failed to initialize Appium session: {error}, duration={duration:.0f}ms')
            raise AppiumError(f'Failed to initialize Appium session: {error}', 'SESSION_INIT_FAILED')

    def apply_performance_settings(self) -> None:
        """
        Apply performance-optimizing driver settings.
        """
        if not self.driver:
            return
            
        try:
            logger.debug("Applying performance settings to driver...")
            settings = {
                "waitForIdleTimeout": 0,
                "snapshotMaxDepth": 50,
                "ignoreUnimportantViews": True,
                "allowInvisibleElements": False,
                "shouldTerminateApp": False
            }
            self.driver.update_settings(settings)
            logger.debug("✓ Performance settings applied.")
        except Exception as e:
            logger.warning(f"Could not apply performance settings: {e}")

    def validate_session(self) -> bool:
        """
        Validate if current session is still active.
        """
        if not self.driver:
            return False
            
        try:
            # Simple command to check connectivity
            self.driver.current_package
            return True
        except Exception as error:
            if is_session_terminated(error):
                logger.warning(f'Session terminated: {error}')
                return self.recover_session()
            logger.error(f'Session validation failed: {error}')
            return False

    def recover_session(self) -> bool:
        """
        Attempt to recover from session termination.
        """
        if not self.last_capabilities or not self.last_appium_url:
            logger.error('Cannot recover session: missing capabilities or URL')
            return False
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f'Session recovery attempt {attempt}/{self.max_retries}')
                
                if self.driver:
                    try:
                        self.driver.quit()
                    except Exception:
                        pass
                    self.driver = None
                
                self.initialize_driver(
                    self.last_capabilities,
                    self.last_appium_url,
                    {
                        'targetPackage': self.target_package,
                        'targetActivity': self.target_activity,
                        'allowedExternalPackages': self.allowed_external_packages
                    }
                )
                
                logger.info('Session recovery successful')
                return True
                
            except Exception as error:
                logger.error(f'Session recovery attempt {attempt} failed: {error}')
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
        
        logger.error('Session recovery failed after all attempts')
        return False

    def close_session(self) -> None:
        """Close driver and clean up session."""
        if self.driver:
            try:
                session_id = self.driver.session_id
                self.driver.quit()
                logger.info(f'Session closed: {session_id}')
            except Exception as error:
                logger.error(f'Error closing session: {error}')
            finally:
                self.driver = None
                self.last_capabilities = None
                self.last_appium_url = None
                self.target_package = None
                self.target_activity = None
                self.allowed_external_packages = []
                self.consecutive_context_failures = 0
