"""
Gmail-integrated auth E2E tests.

These tests verify the ability to extract OTP codes and click
verification links from real emails in the Gmail app using the
production GmailService.

Usage:
    pytest tests/integration/test_auth_gmail_e2e.py -v -s
"""

import pytest
import logging
import time
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Gmail Module Import Tests
# ============================================================================

class TestGmailModuleImports:
    """Test that Gmail module imports work correctly from src."""
    
    def test_gmail_config_import(self):
        """Test that config imports correctly."""
        from mobile_crawler.infrastructure.gmail.config import (
            GMAIL_PACKAGE,
            OTP_PATTERNS,
            GmailAutomationConfig,
            GmailSearchQuery,
        )
        assert GMAIL_PACKAGE == "com.google.android.gm"
        assert len(OTP_PATTERNS) > 0

    def test_gmail_service_import(self):
        """Test that GmailService imports correctly."""
        from mobile_crawler.infrastructure.gmail.service import GmailService
        assert GmailService is not None


# ============================================================================
# Integration Tests (Require Device)
# ============================================================================

@pytest.fixture(scope="module")
def gmail_service(auth_device_session, android_device):
    """Fixture for the production GmailService."""
    from mobile_crawler.infrastructure.gmail.service import GmailService
    from mobile_crawler.infrastructure.gmail.config import GmailAutomationConfig
    
    config = GmailAutomationConfig(
        poll_interval_seconds=5, 
        max_wait_seconds=60,
        capture_screenshots=True,
        screenshot_dir="gmail_failures",
        target_account="afoda50@gmail.com"
    )
    return GmailService(
        driver=auth_device_session.get_driver(),
        device_id=android_device,
        target_app_package="com.example.auth_test_app",
        config=config
    )

@pytest.fixture(scope="module")
def email_sender():
    """Fixture for mock EmailSender."""
    from tests.integration.device_verifier.gmail.email_sender import EmailSender
    return EmailSender(sender_email="afoda50@gmail.com")


class TestGmailOTPExtraction:
    """Test OTP extraction from Gmail using GmailService."""
    
    def test_gmail_otp_extraction(
        self,
        gmail_service,
        auth_navigator,
        auth_form_filler,
        auth_verifier,
        email_sender,
    ):
        """
        Full OTP extraction workflow:
        1. Navigate to signup in test app (OTP mode)
        2. Fill form and submit (triggers OTP email)
        3. Use GmailService to extract OTP
        4. Enter OTP and verify
        """
        from tests.integration.device_verifier.auth.auth_configs import AuthMode, TestCredentials
        from mobile_crawler.infrastructure.gmail.config import GmailSearchQuery
        
        # Step 1: Navigate to signup with OTP mode
        logger.info("Step 1: Navigating to signup (OTP mode)")
        auth_navigator.go_to_signup(mode=AuthMode.OTP)
        time.sleep(2)
        
        # Step 2: Fill signup form
        logger.info("Step 2: Filling signup form")
        creds = TestCredentials.gmail_test()
        auth_form_filler.fill_signup_form(creds)
        auth_form_filler.submit()
        
        # MOCK BACKEND: Send the email that the app doesn't send
        logger.info("MOCK BACKEND: Sending OTP email")
        # Ensure distinct OTP for verification
        otp = "123456"
        send_success = email_sender.send_otp_email(recipient_email=creds.email, otp=otp)
        assert send_success, "Failed to send OTP email via SMTP"
        
        # Wait for OTP screen to appear
        assert auth_verifier.wait_for_otp_screen(), "OTP screen not displayed"
        
        # Step 3: Extract OTP using GmailService
        logger.info("Step 3: Extracting OTP via GmailService")
        query = GmailSearchQuery(
            sender="afoda50@gmail.com",
            subject_contains="Verification"
        )
        
        extracted_otp = gmail_service.extract_otp(query, timeout_sec=120)
        assert extracted_otp, "Failed to extract OTP via GmailService"
        logger.info(f"Extracted OTP: {extracted_otp}")
        assert extracted_otp == otp, f"Extracted OTP {extracted_otp} does not match sent {otp}"
        
        # Step 4: Enter OTP and verify
        logger.info("Step 4: Entering OTP")
        auth_form_filler.enter_otp(extracted_otp)
        auth_form_filler.submit()
        
        # Verify success
        logger.info("Verifying authentication success")
        assert auth_verifier.wait_for_home(), "Failed to reach home screen"


class TestGmailVerificationLink:
    """Test clicking verification links using GmailService."""
    
    def test_gmail_verification_link_click(
        self,
        gmail_service,
        auth_navigator,
        auth_form_filler,
        auth_verifier,
        email_sender,
    ):
        """
        Full verification link workflow using GmailService.
        """
        from tests.integration.device_verifier.auth.auth_configs import AuthMode, TestCredentials
        from mobile_crawler.infrastructure.gmail.config import GmailSearchQuery
        
        # Step 1: Navigate to signup with link mode
        logger.info("Step 1: Navigating to signup (link mode)")
        auth_navigator.go_to_signup(mode=AuthMode.EMAIL_LINK)
        time.sleep(2)
        
        # Step 2: Fill signup form
        logger.info("Step 2: Filling signup form")
        creds = TestCredentials.gmail_test()
        auth_form_filler.fill_signup_form(creds)
        auth_form_filler.submit()
        
        # MOCK BACKEND: Send the email that the app doesn't send
        logger.info("MOCK BACKEND: Sending verification link email")
        send_success = email_sender.send_link_email(recipient_email=creds.email, token="TESTTOKEN")
        assert send_success, "Failed to send verification link email via SMTP"
        
        # Wait for email verification screen
        assert auth_verifier.wait_for_email_screen(timeout=15), "Email verification screen not displayed"
        
        # Step 3: Click verification link using GmailService
        logger.info("Step 3: Clicking verification link via GmailService")
        query = GmailSearchQuery(
            sender="afoda50@gmail.com",
            subject_contains="Verify"
        )
        
        success = gmail_service.click_verification_link(query, timeout_sec=120)
        assert success, "Failed to click verification link via GmailService"
        
        # Step 4: Verify authentication
        logger.info("Step 4: Verifying authentication")
        time.sleep(3)  # Wait for app to handle deep link
        assert auth_verifier.wait_for_home(), "Failed to reach home screen after link click"

# ============================================================================
# Cleanup
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_app():
    """Reset the test app before each test to ensure a clean state."""
    APP_PACKAGE = "com.example.auth_test_app"
    logger.info(f"Resetting app state for {APP_PACKAGE}")
    subprocess.run(["adb", "shell", "pm", "clear", APP_PACKAGE], capture_output=True)
    time.sleep(1)
