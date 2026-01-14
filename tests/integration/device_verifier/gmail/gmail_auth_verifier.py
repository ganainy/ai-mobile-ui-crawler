"""
Gmail Auth Verifier - Orchestrates the full Gmail-based authentication verification.

This class combines GmailNavigator, GmailReader, and AppSwitcher to provide
a high-level API for verifying OTP and email links.
"""

import logging
import time
from typing import Optional

from .gmail_navigator import GmailNavigator
from .gmail_reader import GmailReader
from .app_switcher import AppSwitcher

logger = logging.getLogger(__name__)

class GmailAuthVerifier:
    """Orchestrates Gmail-based authentication verification."""
    
    def __init__(
        self,
        navigator: GmailNavigator,
        reader: GmailReader,
        switcher: AppSwitcher
    ):
        """
        Initialize the verifier.
        
        Args:
            navigator: GmailNavigator instance
            reader: GmailReader instance
            switcher: AppSwitcher instance
        """
        self.navigator = navigator
        self.reader = reader
        self.switcher = switcher

    def verify_otp_flow(
        self,
        sender: Optional[str] = None,
        subject: str = "Verification",
        timeout: int = 60
    ) -> Optional[str]:
        """
        Execute full OTP verification flow in Gmail.
        1. Switch to Gmail
        2. Wait for email
        3. Extract OTP
        4. Copy to clipboard
        5. Switch back to test app
        
        Returns:
            Extracted OTP code if successful, None otherwise
        """
        try:
            logger.info("Starting OTP verification flow in Gmail")
            
            # Switch to Gmail
            if not self.switcher.ensure_gmail():
                logger.error("Failed to switch to Gmail")
                return None
            
            # Wait for email and open it
            if not self.navigator.wait_for_email(sender=sender, subject=subject, timeout=timeout):
                logger.error(f"Email with subject '{subject}' not found")
                self.switcher.ensure_test_app()
                return None
            
            # Extract and copy OTP
            otp_result = self.reader.extract_otp()
            if not otp_result:
                logger.error("OTP not found in email")
                self.switcher.ensure_test_app()
                return None
            
            logger.info(f"OTP found: {otp_result.code}")
            
            if not self.reader.copy_otp_to_clipboard():
                logger.error("Failed to copy OTP to clipboard")
                # We can still return the code and let the filler type it
            
            # Switch back to test app
            self.switcher.ensure_test_app()
            
            return otp_result.code
            
        except Exception as e:
            logger.error(f"OTP verification flow failed: {e}")
            self.switcher.ensure_test_app()
            return None

    def verify_link_flow(
        self,
        sender: Optional[str] = None,
        subject: str = "Verify",
        timeout: int = 60
    ) -> bool:
        """
        Execute full link verification flow in Gmail.
        1. Switch to Gmail
        2. Wait for email
        3. Click verification link
        4. Detect app return
        
        Returns:
            True if flow completed successfully
        """
        try:
            logger.info("Starting link verification flow in Gmail")
            
            # Switch to Gmail
            if not self.switcher.ensure_gmail():
                logger.error("Failed to switch to Gmail")
                return False
            
            # Wait for email and open it
            if not self.navigator.wait_for_email(sender=sender, subject=subject, timeout=timeout):
                logger.error(f"Email with subject '{subject}' not found")
                self.switcher.ensure_test_app()
                return False
            
            # Click link
            if not self.reader.click_verification_link():
                logger.error("Failed to click verification link")
                self.switcher.ensure_test_app()
                return False
            
            # Wait for app to handle link
            success = self.switcher.wait_for_app_to_handle_link()
            if not success:
                logger.warning("App did not return to foreground after link click")
                # Try forced switch
                self.switcher.ensure_test_app()
            
            return True
            
        except Exception as e:
            logger.error(f"Link verification flow failed: {e}")
            self.switcher.ensure_test_app()
            return False
