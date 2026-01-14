from dataclasses import dataclass
from enum import Enum, auto
import time

@dataclass
class TestCredentials:
    email: str
    password: str
    name: str = ""
    
    @classmethod
    def signin_default(cls) -> "TestCredentials":
        """Hardcoded credentials that work with the test app."""
        return cls(
            email="admin@example.com",
            password="password123"
        )
    
    @classmethod
    def signup_unique(cls, name: str = "Test User") -> "TestCredentials":
        """Generate unique credentials for signup tests."""
        return cls(
            email=f"test_{int(time.time())}@example.com",
            password="Test@123456",
            name=name
        )

    @classmethod
    def gmail_test(cls) -> "TestCredentials":
        """Credentials for real Gmail integration testing."""
        return cls(
            email="appiumtester96@gmail.com",
            password="Test@123456",
            name="Appium Tester"
        )

class AuthMode(Enum):
    BASIC = "basic"
    OTP = "otp"
    EMAIL_LINK = "link"
    CAPTCHA = "captcha"
    COMBINED = "combined"

class AuthScreenState(Enum):
    WELCOME = auto()      # App entry/splash
    SIGNUP = auto()       # Signup form visible
    SIGNIN = auto()       # Sign-in form visible
    CAPTCHA = auto()      # CAPTCHA challenge visible
    OTP = auto()          # OTP entry screen visible
    EMAIL_WAITING = auto() # "Check your email" screen
    HOME = auto()         # Authenticated home screen
    ERROR = auto()        # Error displayed
    UNKNOWN = auto()      # Fallback state
