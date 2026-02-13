# Contracts: Auth E2E Tests

**Feature**: 016-auth-e2e-tests  
**Date**: 2026-01-13 (Updated)  
**Purpose**: Define deep link API and test utility contracts for Flutter test app and Python test suite

---

## Part 1: Flutter Test App Contracts

### Deep Link API

The test app exposes the following deep link routes:

| Route | Method | Parameters | Response |
|-------|--------|------------|----------|
| `testapp://signup` | VIEW | `mode` (optional) | Opens signup screen with specified auth mode |
| `testapp://signin` | VIEW | none | Opens sign-in screen |
| `testapp://verify` | VIEW | `token` (required) | Validates token and navigates to home |

#### Parameter: `mode`

| Value | Description | Screen Flow |
|-------|-------------|-------------|
| `basic` (default) | No additional verification | Signup → Home |
| `otp` | OTP required after signup | Signup → OTP → Home |
| `link` | Email link required | Signup → Email Wait → (verify link) → Home |
| `captcha` | CAPTCHA before signup | CAPTCHA → Signup → Home |
| `combined` | CAPTCHA + OTP | CAPTCHA → Signup → OTP → Home |

#### Parameter: `token`

| Value | Result |
|-------|--------|
| `TESTTOKEN` | Verification succeeds, navigate to Home |
| Other | Verification fails, show error |

### Android Manifest Intent Filters

```xml
<intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="testapp" />
</intent-filter>
```

---

## Part 2: Screen Accessibility Contracts

Each screen MUST expose Semantics labels for automation:

### Welcome Screen

| Element | Semantics Label | Purpose |
|---------|-----------------|---------|
| Signup Button | `btn_signup` | Navigate to signup |
| Sign-in Button | `btn_signin` | Navigate to signin |

### Signup Screen

| Element | Semantics Label | Purpose |
|---------|-----------------|---------|
| Name Field | `input_name` | Name entry |
| Email Field | `input_email` | Email entry |
| Password Field | `input_password` | Password entry |
| Terms Checkbox | `checkbox_terms` | Accept terms |
| Submit Button | `btn_submit` | Submit form |
| Error Message | `error_message` | Validation errors |

### Sign-in Screen

| Element | Semantics Label | Purpose |
|---------|-----------------|---------|
| Email Field | `input_email` | Email entry |
| Password Field | `input_password` | Password entry |
| Submit Button | `btn_submit` | Submit form |
| Error Message | `error_message` | Login errors |

### CAPTCHA Screen

| Element | Semantics Label | Purpose |
|---------|-----------------|---------|
| Challenge Text | `captcha_challenge` | Displays "TESTCAPTCHA" |
| Input Field | `input_captcha` | CAPTCHA answer |
| Verify Button | `btn_verify` | Validate CAPTCHA |
| Error Message | `error_message` | Wrong solution |

### OTP Screen

| Element | Semantics Label | Purpose |
|---------|-----------------|---------|
| OTP Input | `input_otp` | 6-digit OTP entry |
| Verify Button | `btn_verify` | Validate OTP |
| Resend Button | `btn_resend` | Request new OTP |
| Error Message | `error_message` | Wrong OTP |

### Email Verification Screen

| Element | Semantics Label | Purpose |
|---------|-----------------|---------|
| Status Text | `email_status` | "Check your email" |
| Progress Indicator | `waiting_spinner` | Loading state |
| Resend Button | `btn_resend` | Resend email |

### Home Screen

| Element | Semantics Label | Purpose |
|---------|-----------------|---------|
| Welcome Message | `home_welcome` | Confirms authentication |
| Action List | `home_actions` | Available actions |

---

## Part 3: Python Test Utility Contracts

### AuthNavigator

```python
class AuthNavigator:
    """Navigates to auth screens using deep links."""
    
    def __init__(self, deep_link_navigator: DeepLinkNavigator):
        self.navigator = deep_link_navigator
        self.base_url = "testapp://"
    
    def go_to_signup(self, mode: AuthMode = AuthMode.BASIC) -> bool:
        """
        Navigate to signup screen with specified auth mode.
        
        Contract:
            - MUST trigger deep link: testapp://signup?mode={mode}
            - MUST wait for activity to launch
            - MUST return True if navigation succeeded
        """
        url = f"{self.base_url}signup?mode={mode.value}"
        return self.navigator.navigate_to(url)
    
    def go_to_signin(self) -> bool:
        """
        Navigate to sign-in screen.
        
        Contract:
            - MUST trigger deep link: testapp://signin
            - MUST return True if navigation succeeded
        """
        return self.navigator.navigate_to(f"{self.base_url}signin")
    
    def trigger_email_verification(self, token: str = "TESTTOKEN") -> bool:
        """
        Trigger email verification deep link.
        
        Contract:
            - MUST trigger deep link: testapp://verify?token={token}
            - MUST be called while on Email Verification screen
            - MUST return True if verification triggered
        """
        return self.navigator.navigate_to(f"{self.base_url}verify?token={token}")
```

### AuthFormFiller

```python
class AuthFormFiller:
    """Fills authentication forms using Appium gestures."""
    
    def __init__(self, gesture_handler, screen_dims: Tuple[int, int]):
        self.gestures = gesture_handler
        self.width, self.height = screen_dims
    
    def fill_signup_form(self, creds: TestCredentials) -> bool:
        """
        Fill signup form with credentials.
        
        Contract:
            - MUST tap name field, enter name
            - MUST TAB to email field, enter email
            - MUST TAB to password field, enter password
            - MUST check terms checkbox
            - MUST NOT submit form (call submit() separately)
        """
        ...
    
    def fill_signin_form(self, creds: TestCredentials) -> bool:
        """
        Fill sign-in form with credentials.
        
        Contract:
            - MUST tap email field, enter email
            - MUST TAB to password field, enter password
            - MUST NOT submit form
        """
        ...
    
    def enter_otp(self, otp: str = "123456") -> bool:
        """
        Enter OTP on OTP screen.
        
        Contract:
            - MUST tap OTP input field
            - MUST enter 6-digit OTP
        """
        ...
    
    def enter_captcha(self, solution: str = "TESTCAPTCHA") -> bool:
        """
        Enter CAPTCHA solution.
        
        Contract:
            - MUST tap CAPTCHA input field
            - MUST enter solution text
        """
        ...
    
    def submit(self) -> bool:
        """
        Submit the current form.
        
        Contract:
            - MUST tap the submit/verify button
            - MUST wait briefly for submission to process
        """
        ...
```

### AuthVerifier

```python
class AuthVerifier:
    """Verifies authentication screen states."""
    
    def __init__(self, driver):
        self.driver = driver
    
    def wait_for_home(self, timeout: int = 30) -> bool:
        """
        Wait for authenticated Home screen.
        
        Contract:
            - MUST detect 'home_welcome' or 'home_actions' label
            - MUST return True if found within timeout
            - MUST return False on timeout
        """
        ...
    
    def wait_for_otp_screen(self, timeout: int = 10) -> bool:
        """
        Wait for OTP entry screen.
        
        Contract:
            - MUST detect 'input_otp' label
            - MUST return True if found within timeout
        """
        ...
    
    def wait_for_email_screen(self, timeout: int = 10) -> bool:
        """
        Wait for email verification waiting screen.
        
        Contract:
            - MUST detect 'email_status' or 'waiting_spinner' label
            - MUST return True if found within timeout
        """
        ...
    
    def wait_for_captcha_screen(self, timeout: int = 10) -> bool:
        """
        Wait for CAPTCHA challenge screen.
        
        Contract:
            - MUST detect 'captcha_challenge' label
            - MUST return True if found within timeout
        """
        ...
    
    def wait_for_error(self, timeout: int = 5) -> bool:
        """
        Wait for error message.
        
        Contract:
            - MUST detect 'error_message' label
            - MUST return True if found within timeout
        """
        ...
```

---

## Part 4: Test Isolation Contract

All auth tests MUST:

1. Force-stop app before starting
2. Launch via deep link to specific screen
3. Clean up session after completion
4. Not depend on state from previous tests

```python
@pytest.fixture(autouse=True)
def isolate_auth_test(deep_link_navigator):
    """Ensure test isolation."""
    # Setup - force stop any existing instance
    subprocess.run(['adb', 'shell', 'am', 'force-stop', 'com.example.auth_test_app'])
    yield
    # Teardown - clean stop
    subprocess.run(['adb', 'shell', 'am', 'force-stop', 'com.example.auth_test_app'])
```

---

*Contracts complete. Phase 1 artifacts generated.*
