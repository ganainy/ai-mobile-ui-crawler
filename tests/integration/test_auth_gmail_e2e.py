"""
Gmail-integrated auth E2E tests.

These tests verify the ability to extract OTP codes and click
verification links from real emails in the Gmail app.

Prerequisites:
- Gmail app installed and signed in on the test device
- A real email service that can send OTP/verification emails
- Proper network connectivity

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
    """Test that Gmail module imports work correctly."""
    
    def test_gmail_configs_import(self):
        """Test that gmail_configs imports correctly."""
        from tests.integration.device_verifier.gmail.gmail_configs import (
            GMAIL_PACKAGE,
            GMAIL_ACTIVITY,
            OTP_PATTERNS,
            LINK_PATTERNS,
            GMAIL_SELECTORS,
            GmailAutomationConfig,
            GmailSearchQuery,
        )
        
        assert GMAIL_PACKAGE == "com.google.android.gm"
        assert len(OTP_PATTERNS) > 0
        assert len(LINK_PATTERNS) > 0
    
    def test_gmail_navigator_import(self):
        """Test that gmail_navigator imports correctly."""
        from tests.integration.device_verifier.gmail.gmail_navigator import (
            GmailNavigator,
            GmailNavigationError,
            GmailNotInstalledError,
            NoEmailsFoundError,
        )
        
        assert GmailNavigator is not None
    
    def test_gmail_reader_import(self):
        """Test that gmail_reader imports correctly."""
        from tests.integration.device_verifier.gmail.gmail_reader import (
            GmailReader,
            OTPResult,
            LinkResult,
            GmailReadError,
            OTPNotFoundError,
            LinkNotFoundError,
        )
        
        assert GmailReader is not None
        assert OTPResult is not None
    
    def test_app_switcher_import(self):
        """Test that app_switcher imports correctly."""
        from tests.integration.device_verifier.gmail.app_switcher import (
            AppSwitcher,
            AppState,
        )
        
        assert AppSwitcher is not None
    
    def test_clipboard_helper_import(self):
        """Test that clipboard_helper imports correctly."""
        from tests.integration.device_verifier.gmail.clipboard_helper import (
            ClipboardHelper,
        )
        
        assert ClipboardHelper is not None


# ============================================================================
# Gmail Search Query Tests
# ============================================================================

class TestGmailSearchQuery:
    """Test GmailSearchQuery functionality."""
    
    def test_query_with_sender(self):
        """Test query building with sender filter."""
        from tests.integration.device_verifier.gmail.gmail_configs import GmailSearchQuery
        
        query = GmailSearchQuery(sender="test@example.com")
        assert query.to_gmail_query() == "from:test@example.com is:unread"
    
    def test_query_with_subject(self):
        """Test query building with subject filter."""
        from tests.integration.device_verifier.gmail.gmail_configs import GmailSearchQuery
        
        query = GmailSearchQuery(subject_contains="Verification")
        assert "subject:Verification" in query.to_gmail_query()
    
    def test_query_validation(self):
        """Test query validation."""
        from tests.integration.device_verifier.gmail.gmail_configs import GmailSearchQuery
        
        empty_query = GmailSearchQuery()
        assert not empty_query.is_valid()
        
        valid_query = GmailSearchQuery(sender="test@example.com")
        assert valid_query.is_valid()


# ============================================================================
# OTP Pattern Tests
# ============================================================================

class TestOTPPatterns:
    """Test OTP extraction patterns."""
    
    def test_extract_6_digit_otp(self):
        """Test extraction of 6-digit OTP."""
        import re
        from tests.integration.device_verifier.gmail.gmail_configs import OTP_PATTERNS
        
        test_text = "Your verification code is 123456. Please enter it to continue."
        
        for pattern in OTP_PATTERNS:
            match = re.search(pattern, test_text, re.IGNORECASE)
            if match:
                assert match.group(1) == "123456"
                return
        
        pytest.fail("No OTP pattern matched")
    
    def test_extract_otp_with_label(self):
        """Test extraction of OTP with label."""
        import re
        from tests.integration.device_verifier.gmail.gmail_configs import OTP_PATTERNS
        
        test_text = "Your OTP: 987654"
        
        for pattern in OTP_PATTERNS:
            match = re.search(pattern, test_text, re.IGNORECASE)
            if match:
                assert match.group(1) == "987654"
                return
        
        pytest.fail("No OTP pattern matched")


# ============================================================================
# Link Pattern Tests
# ============================================================================

class TestLinkPatterns:
    """Test verification link extraction patterns."""
    
    def test_extract_verify_link(self):
        """Test extraction of verification link."""
        import re
        from tests.integration.device_verifier.gmail.gmail_configs import LINK_PATTERNS
        
        test_text = "Click here to verify: https://example.com/verify?token=abc123"
        
        for pattern in LINK_PATTERNS:
            match = re.search(pattern, test_text, re.IGNORECASE)
            if match:
                url = match.group(1)
                assert "verify" in url
                assert "token=abc123" in url
                return
        
        pytest.fail("No link pattern matched")


# ============================================================================
# Integration Tests (Require Device)
# ============================================================================

class TestGmailNavigation:
    """Test Gmail app navigation."""
    
    def test_open_gmail(self, gmail_navigator):
        """Test opening Gmail app."""
        result = gmail_navigator.open_gmail()
        assert result, "Failed to open Gmail"
        assert gmail_navigator.is_inbox_visible(), "Inbox not visible"
    
    def test_refresh_inbox(self, gmail_navigator):
        """Test refreshing the inbox."""
        gmail_navigator.open_gmail()
        result = gmail_navigator.refresh_inbox()
        assert result, "Failed to refresh inbox"


class TestAppSwitching:
    """Test app switching functionality."""
    
    def test_switch_to_gmail(self, app_switcher):
        """Test switching to Gmail."""
        result = app_switcher.switch_to_gmail()
        assert result, "Failed to switch to Gmail"
        assert app_switcher.is_gmail_foreground(), "Gmail not in foreground"
    
    def test_switch_to_test_app(self, app_switcher):
        """Test switching back to test app."""
        app_switcher.switch_to_gmail()
        result = app_switcher.switch_to_test_app()
        assert result, "Failed to switch to test app"


class TestClipboard:
    """Test clipboard operations."""
    
    def test_set_and_get_clipboard(self, clipboard_helper):
        """Test setting and getting clipboard content."""
        test_text = "123456"
        result = clipboard_helper.set_clipboard(test_text)
        assert result, "Failed to set clipboard"
        
        content = clipboard_helper.get_clipboard()
        assert content == test_text, f"Expected {test_text}, got {content}"


@pytest.fixture(autouse=True)
def cleanup_app():
    """Reset the test app before each test to ensure a clean state."""
    APP_PACKAGE = "com.example.auth_test_app"
    logger.info(f"Resetting app state for {APP_PACKAGE}")
    subprocess.run(["adb", "shell", "pm", "clear", APP_PACKAGE], capture_output=True)
    time.sleep(1)


# ============================================================================
# Full Flow Tests (Require Real Email Service)
# ============================================================================

class TestGmailOTPExtraction:
    """Test OTP extraction from real Gmail emails."""
    
    def test_gmail_otp_extraction(
        self,
        gmail_navigator,
        gmail_reader,
        app_switcher,
        clipboard_helper,
        auth_navigator,
        auth_form_filler,
        auth_verifier,
        email_sender,
    ):
        """
        Full OTP extraction workflow:
        1. Navigate to signup in test app (OTP mode)
        2. Fill form and submit (triggers OTP email)
        3. Switch to Gmail
        4. Wait for and open OTP email
        5. Extract OTP from email
        6. Copy OTP to clipboard
        7. Switch back to test app
        8. Paste OTP and verify
        """
        from tests.integration.device_verifier.auth.auth_configs import AuthMode, TestCredentials
        
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
        send_success = email_sender.send_otp_email(recipient_email=creds.email, otp="123456")
        assert send_success, "Failed to send OTP email via SMTP"
        
        # Wait for OTP screen to appear
        assert auth_verifier.wait_for_otp_screen(), "OTP screen not displayed"
        
        # Step 3: Switch to Gmail
        logger.info("Step 3: Switching to Gmail")
        assert app_switcher.switch_to_gmail(), "Failed to switch to Gmail"
        
        # Step 4: Wait for OTP email
        logger.info("Step 4: Waiting for OTP email")
        # Sender: afoda50@gmail.com (Recipient: appiumtester96@gmail.com)
        email_found = gmail_navigator.wait_for_email(
            sender="afoda50@gmail.com",
            subject="Verification",
            timeout=60
        )
        assert email_found, "OTP email not received"
        
        # Step 5: Extract OTP
        logger.info("Step 5: Extracting OTP")
        otp_result = gmail_reader.extract_otp()
        assert otp_result, "Failed to extract OTP from email"
        logger.info(f"Found OTP: {otp_result.code}")
        
        # Step 6: Copy OTP
        logger.info("Step 6: Copying OTP to clipboard")
        assert gmail_reader.copy_otp_to_clipboard(), "Failed to copy OTP"
        
        # Step 7: Switch back to app
        logger.info("Step 7: Switching back to test app")
        assert app_switcher.switch_to_test_app(), "Failed to switch to test app"
        
        # Step 8: Enter OTP and verify
        logger.info("Step 8: Entering OTP")
        auth_form_filler.enter_otp(otp_result.code)
        auth_form_filler.submit()
        
        # Verify success
        logger.info("Verifying authentication success")
        assert auth_verifier.wait_for_home(), "Failed to reach home screen"


class TestGmailVerificationLink:
    """Test clicking verification links in Gmail emails."""
    
    def test_gmail_verification_link_click(
        self,
        gmail_navigator,
        gmail_reader,
        app_switcher,
        auth_navigator,
        auth_form_filler,
        auth_verifier,
        email_sender,
    ):
        """
        Full verification link workflow:
        1. Navigate to signup in test app (link mode)
        ...
        """
        from tests.integration.device_verifier.auth.auth_configs import AuthMode, TestCredentials
        
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
        
        # Step 3: Switch to Gmail
        logger.info("Step 3: Switching to Gmail")
        assert app_switcher.switch_to_gmail(), "Failed to switch to Gmail"
        
        # Step 4: Wait for verification email
        logger.info("Step 4: Waiting for verification email")
        email_found = gmail_navigator.wait_for_email(
            sender="afoda50@gmail.com",
            subject="Verify",
            timeout=60
        )
        assert email_found, "Verification email not received"
        
        # Step 5: Click verification link
        logger.info("Step 5: Clicking verification link")
        assert gmail_reader.click_verification_link(), "Failed to click verification link"
        
        # Step 6: Verify authentication
        logger.info("Step 6: Verifying authentication")
        time.sleep(3)  # Wait for app to handle deep link
        assert auth_verifier.wait_for_home(), "Failed to reach home screen after link click"
