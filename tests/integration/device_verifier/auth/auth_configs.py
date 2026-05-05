"""Auth test configurations and helpers."""
from enum import Enum
from dataclasses import dataclass


class AuthMode(Enum):
    BASIC = "basic"
    OTP = "otp"
    EMAIL_LINK = "email_link"
    CAPTCHA = "captcha"
    COMBINED = "combined"


@dataclass
class TestCredentials:
    email: str
    password: str

    @classmethod
    def signup_unique(cls):
        import time
        return cls(email=f"test{int(time.time())}@example.com", password="TestPass123!")

    @classmethod
    def signin_default(cls):
        return cls(email="test@example.com", password="TestPass123!")
