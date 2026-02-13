# GmailService Quickstart

## Installation
The Gmail features are part of the `mobile_crawler.infrastructure.gmail` package.

## Basic Usage

### 1. Initialize the Service
```python
from mobile_crawler.infrastructure.gmail.service import GmailService
from mobile_crawler.infrastructure.gmail.config import GmailAutomationConfig

config = GmailAutomationConfig(
    target_account="your-test-email@gmail.com",
    max_wait_seconds=120
)

# Initialize with Appium driver and target app info
gmail_service = GmailService(
    driver=driver,
    device_id="your_device_id",
    target_app_package="com.example.myapp",
    config=config
)
```

### 2. Extract OTP
```python
from mobile_crawler.infrastructure.gmail.config import GmailSearchQuery

query = GmailSearchQuery(
    sender="noreply@example.com",
    subject_contains="Verification Code"
)

otp = gmail_service.extract_otp(query)
if otp:
    print(f"Found OTP: {otp}")
    # The service automatically switches back to your target app
```

### 3. Click Verification Link
```python
query = GmailSearchQuery(
    sender="verify@example.com",
    subject_contains="Confirm your email"
)

success = gmail_service.click_verification_link(query)
if success:
    print("Verification link clicked and app restored")
```

## How Account Switching Works
If `target_account` is provided in the configuration, the `GmailService` will:
1. Open Gmail.
2. Check if the active account matches `target_account`.
3. If not, it will use UI automation to tap the profile icon and select the specified account before proceeding with the search.
