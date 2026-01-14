
import sys
import os

# Add src to sys.path
sys.path.append(os.path.abspath("src"))

try:
    from mobile_crawler.infrastructure.gmail.config import GmailSearchQuery, OTP_PATTERNS
    print("Config imported")
    from mobile_crawler.infrastructure.gmail.reader import GmailReader, OTPResult
    print("Reader imported")
    from mobile_crawler.infrastructure.gmail.navigator import GmailNavigator
    print("Navigator imported")
    from mobile_crawler.infrastructure.gmail.app_switcher import AppSwitcher
    print("Switcher imported")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
