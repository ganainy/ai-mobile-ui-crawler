import pytest
import time
import logging
import subprocess

from tests.integration.device_verifier.auth.auth_configs import AuthMode, TestCredentials

logger = logging.getLogger(__name__)

# Constants
APP_PACKAGE = "com.example.auth_test_app"

@pytest.fixture(autouse=True)
def isolate_auth_test(android_device):
    """Ensure test isolation by force-stopping the app."""
    # We use android_device from conftest
    subprocess.run(['adb', '-s', android_device, 'shell', 'am', 'force-stop', APP_PACKAGE], timeout=10)
    yield

def test_basic_signup(auth_navigator, auth_form_filler, auth_verifier):
    """
    User Story 1: Basic Signup Flow
    Verify that crawler can complete basic signup with name, email, password, terms checkbox.
    """
    logger.info("Starting US1: Basic Signup Flow")
    
    # 1. Navigate to basic signup
    nav_success = auth_navigator.go_to_signup(mode=AuthMode.BASIC)
    assert nav_success, "Failed to navigate to signup screen"
    time.sleep(1) # Wait for screen transition
    
    # 2. Fill signup form
    creds = TestCredentials.signup_unique()
    logger.info(f"Filling signup form for {creds.email}")
    auth_form_filler.fill_signup_form(creds)
    
    # 3. Submit
    auth_form_filler.submit()
    
    # 4. Verify landing on Home screen
    logger.info("Verifying navigation to Home screen")
    success = auth_verifier.wait_for_home(timeout=30)
    assert success, "Failed to reach Home screen after basic signup"

def test_basic_signin(auth_navigator, auth_form_filler, auth_verifier):
    """
    User Story 2: Basic Sign-In Flow
    Verify that crawler can log in with existing credentials.
    """
    logger.info("Starting US2: Basic Sign-In Flow")
    
    # 1. Navigate to sign-in
    nav_success = auth_navigator.go_to_signin()
    assert nav_success, "Failed to navigate to sign-in screen"
    time.sleep(1)
    
    # 2. Fill sign-in form
    creds = TestCredentials.signin_default()
    logger.info(f"Filling sign-in form for {creds.email}")
    auth_form_filler.fill_signin_form(creds)
    
    # 3. Submit
    auth_form_filler.submit()
    
    # 4. Verify landing on Home screen
    logger.info("Verifying navigation to Home screen")
    success = auth_verifier.wait_for_home(timeout=15)
    assert success, "Failed to reach Home screen after basic sign-in"

def test_otp_verification(auth_navigator, auth_form_filler, auth_verifier):
    """
    User Story 3: Email OTP Verification
    Verify that crawler can handle OTP entry after signup.
    """
    logger.info("Starting US3: Email OTP Verification")
    
    # 1. Navigate to signup with OTP mode
    nav_success = auth_navigator.go_to_signup(mode=AuthMode.OTP)
    assert nav_success, "Failed to navigate to signup screen (OTP mode)"
    time.sleep(1)
    
    # 2. Fill signup form
    creds = TestCredentials.signup_unique()
    auth_form_filler.fill_signup_form(creds)
    auth_form_filler.submit()
    
    # 3. Wait for OTP screen
    logger.info("Waiting for OTP screen")
    on_otp = auth_verifier.wait_for_otp_screen(timeout=10)
    assert on_otp, "Failed to reach OTP verification screen"
    
    # 4. Enter OTP and verify
    logger.info("Entering OTP: 123456")
    auth_form_filler.enter_otp("123456")
    auth_form_filler.submit()
    
    # 5. Verify landing on Home screen
    logger.info("Verifying navigation to Home screen")
    success = auth_verifier.wait_for_home(timeout=15)
    assert success, "Failed to reach Home screen after OTP verification"

def test_email_link_verification(auth_navigator, auth_form_filler, auth_verifier):
    """
    User Story 4: Email Verification Link
    Verify that crawler can handle "click link to verify" flows via deep link.
    """
    logger.info("Starting US4: Email Verification Link")
    
    # 1. Navigate to signup with Email Link mode
    nav_success = auth_navigator.go_to_signup(mode=AuthMode.EMAIL_LINK)
    assert nav_success, "Failed to navigate to signup screen (Link mode)"
    time.sleep(1)
    
    # 2. Fill signup form
    creds = TestCredentials.signup_unique()
    auth_form_filler.fill_signup_form(creds)
    auth_form_filler.submit()
    
    # 3. Wait for "Check email" screen
    logger.info("Waiting for email verification waiting screen")
    on_email_screen = auth_verifier.wait_for_email_screen(timeout=10)
    assert on_email_screen, "Failed to reach email verification waiting screen"
    
    # 4. Trigger the verification deep link (simulating clicking link in email)
    logger.info("Triggering verification deep link: TESTTOKEN")
    time.sleep(2) # Simulating user opening email
    trigger_success = auth_navigator.trigger_email_verification(token="TESTTOKEN")
    assert trigger_success, "Failed to trigger email verification deep link"
    
    # 5. Verify landing on Home screen
    logger.info("Verifying navigation to Home screen")
    success = auth_verifier.wait_for_home(timeout=15)
    assert success, "Failed to reach Home screen after email link verification"

def test_captcha_signup(auth_navigator, auth_form_filler, auth_verifier):
    """
    User Story 5: CAPTCHA Simulation
    Verify that crawler can solve a text-based CAPTCHA challenge.
    """
    logger.info("Starting US5: CAPTCHA Simulation")
    
    # 1. Navigate to signup with CAPTCHA mode
    nav_success = auth_navigator.go_to_signup(mode=AuthMode.CAPTCHA)
    assert nav_success, "Failed to navigate to signup flow (CAPTCHA mode)"
    time.sleep(1)
    
    # 2. Wait for CAPTCHA screen
    logger.info("Waiting for CAPTCHA screen")
    on_captcha = auth_verifier.wait_for_captcha_screen(timeout=10)
    assert on_captcha, "Failed to reach CAPTCHA challenge screen"
    
    # 3. Enter CAPTCHA and verify
    logger.info("Entering CAPTCHA: TESTCAPTCHA")
    auth_form_filler.enter_captcha("TESTCAPTCHA")
    auth_form_filler.submit()
    
    # 4. Fill signup form (should be on signup screen now)
    logger.info("Filling signup form")
    creds = TestCredentials.signup_unique()
    auth_form_filler.fill_signup_form(creds)
    auth_form_filler.submit()
    
    # 5. Verify landing on Home screen
    logger.info("Verifying navigation to Home screen")
    success = auth_verifier.wait_for_home(timeout=30)
    assert success, "Failed to reach Home screen after CAPTCHA signup"

def test_invalid_signin(auth_navigator, auth_form_filler, auth_verifier):
    """
    User Story 6: Invalid Credentials Handling
    Verify that error messages are displayed for incorrect login.
    """
    logger.info("Starting US6: Invalid Credentials Handling")
    
    # 1. Navigate to sign-in
    auth_navigator.go_to_signin()
    time.sleep(1)
    
    # 2. Enter wrong credentials
    creds = TestCredentials(email="wrong@example.com", password="wrongpassword")
    auth_form_filler.fill_signin_form(creds)
    auth_form_filler.submit()
    
    # 3. Verify error message
    logger.info("Verifying error message display")
    error_shown = auth_verifier.wait_for_error(timeout=5)
    assert error_shown, "Error message not displayed for invalid credentials"

def test_combined_flow(auth_navigator, auth_form_filler, auth_verifier):
    """
    User Story 7: Combined Multi-Step Flow
    Verify multi-step flow: CAPTCHA -> Signup -> OTP -> Home.
    """
    logger.info("Starting US7: Combined Multi-Step Flow")
    
    # 1. Start Signup with Combined mode
    nav_success = auth_navigator.go_to_signup(mode=AuthMode.COMBINED)
    assert nav_success, "Failed to start signup flow (Combined mode)"
    time.sleep(1)
    
    # 2. Solve CAPTCHA
    logger.info("Step 1: Solving CAPTCHA")
    auth_verifier.wait_for_captcha_screen(timeout=10)
    auth_form_filler.enter_captcha("TESTCAPTCHA")
    auth_form_filler.submit()
    
    # 3. Fill Signup Form
    logger.info("Step 2: Filling Signup Form")
    creds = TestCredentials.signup_unique()
    auth_form_filler.fill_signup_form(creds)
    auth_form_filler.submit()
    
    # 4. Enter OTP
    logger.info("Step 3: Entering OTP")
    auth_verifier.wait_for_otp_screen(timeout=10)
    auth_form_filler.enter_otp("123456")
    auth_form_filler.submit()
    
    # 5. Verify landing on Home screen
    logger.info("Step 4: Final Verification")
    success = auth_verifier.wait_for_home(timeout=30)
    assert success, "Failed to reach Home screen after combined multi-step flow"
