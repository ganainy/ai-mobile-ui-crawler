"""
Gmail Service module.
Main entry point for Gmail automation. Orchestrates navigation, reading, and switching.
"""

import logging
from typing import Optional

from .config import GmailAutomationConfig, GmailSearchQuery
from .navigator import GmailNavigator, NoEmailsFoundError
from .reader import GmailReader
from .app_switcher import AppSwitcher


logger = logging.getLogger(__name__)


class GmailService:
    """
    Production implementation of the Gmail automation service.
    Orchestrates GmailNavigator, GmailReader, and AppSwitcher.
    """

    def __init__(
        self, 
        driver, 
        device_id: str, 
        target_app_package: str,
        target_app_activity: Optional[str] = None,
        config: Optional[GmailAutomationConfig] = None
    ):
        """
        Initialize the Gmail service.

        Args:
            driver: Appium WebDriver instance.
            device_id: Android device ID.
            target_app_package: The package name of the app we are testing/crawling.
            target_app_activity: Optional activity to launch when switching back.
            config: Optional configuration overrides.
        """
        self.config = config or GmailAutomationConfig()
        self.driver = driver
        self.device_id = device_id
        self.target_app_package = target_app_package

        # Initialize components
        self.navigator = GmailNavigator(driver, device_id, self.config)
        self.reader = GmailReader(driver, device_id, self.config)
        self.switcher = AppSwitcher(driver, device_id, target_app_package, target_app_activity, self.config)

    def extract_otp(self, query: GmailSearchQuery, timeout_sec: int = 60) -> Optional[str]:
        """
        Switch to Gmail, find the email matching the query, extract the OTP, 
        switch back to the original app, and return the OTP.
        
        Args:
            query: Search criteria for the email.
            timeout_sec: Max time to wait for email.
            
        Returns:
            The extracted OTP string, or None if not found/timed out.
        """
        try:
            logger.info("Starting OTP extraction with GmailService")
            
            # 1. Switch to Gmail
            if not self.switcher.ensure_gmail():
                logger.error("Failed to switch to Gmail")
                return None
            
            # 2. Ensure correct account
            if not self.navigator.ensure_correct_account():
                logger.error("Failed to ensure correct Gmail account")
                self.switcher.ensure_test_app()
                return None
            
            # 3. Wait for email and open it
            sender = query.sender or query.sender_contains
            subject = query.subject_contains
            
            if not self.navigator.wait_for_email(
                sender=sender, 
                subject=subject, 
                timeout=timeout_sec
            ):
                logger.error(f"Email matching query {query} not found within {timeout_sec}s")
                self.switcher.ensure_test_app()
                return None
            
            # 3. Extract and copy OTP
            otp_result = self.reader.extract_otp()
            if not otp_result:
                logger.error("OTP not found in the opened email")
                self.switcher.ensure_test_app()
                return None
            
            logger.info(f"OTP found: {otp_result.code}")
            
            # Try copying to clipboard as a convenience
            # We ignore failure here as we return the code anyway
            try:
                self.reader.copy_otp_to_clipboard()
            except Exception:
                logger.warning("Failed to auto-copy OTP to clipboard (non-fatal)")
            
            # 4. Switch back to test app
            self.switcher.ensure_test_app()
            
            return otp_result.code
            
        except Exception as e:
            logger.error(f"GmailService extract_otp failed: {e}")
            # Attempt to restore state
            try:
                self.switcher.ensure_test_app()
            except:
                pass
            return None

    def click_verification_link(self, query: GmailSearchQuery, timeout_sec: int = 60) -> bool:
        """
        Switch to Gmail, find the email matching the query, click the verification link,
        wait for the redirect/app switch, and return success status.
        
        Args:
            query: Search criteria for the email.
            timeout_sec: Max time to wait for email.
            
        Returns:
            True if link found and clicked, False otherwise.
        """
        try:
            logger.info("Starting verification link flow with GmailService")
            
            # 1. Switch to Gmail
            if not self.switcher.ensure_gmail():
                logger.error("Failed to switch to Gmail")
                return False
            
            # 2. Ensure correct account
            if not self.navigator.ensure_correct_account():
                logger.error("Failed to ensure correct Gmail account")
                self.switcher.ensure_test_app()
                return False
            
            # 3. Wait for email and open it
            sender = query.sender or query.sender_contains
            subject = query.subject_contains
            
            if not self.navigator.wait_for_email(
                sender=sender, 
                subject=subject, 
                timeout=timeout_sec
            ):
                logger.error(f"Email matching query {query} not found within {timeout_sec}s")
                self.switcher.ensure_test_app()
                return False
            
            # 3. Click verification link
            if not self.reader.click_verification_link():
                logger.error("Failed to click verification link in email")
                self.switcher.ensure_test_app()
                return False
            
            # 4. Wait for app to return (due to deep link)
            success = self.switcher.wait_for_app_to_handle_link()
            if not success:
                logger.warning("App did not return to foreground after link click, attempting forced switch")
                self.switcher.ensure_test_app()
            
            return True

        except Exception as e:
            logger.error(f"GmailService click_verification_link failed: {e}")
            try:
                self.switcher.ensure_test_app()
            except:
                pass
            return False
