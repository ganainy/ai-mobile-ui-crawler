# Quickstart: App Authentication and Signup Support

**Feature Branch**: `013-app-auth-signup`

## Prerequisites

1. **Gmail App**: Must be installed on the Android device and logged in to the test email account
2. **Test Email**: Configure a test email address in Settings panel (Settings → Test Credentials → Test Email)
3. **Appium Server**: Must be running (`npx appium`)
4. **Device**: Android device connected via ADB with USB debugging enabled

## Quick Setup

### 1. Configure Test Email

1. Open the mobile-crawler GUI
2. Navigate to **Settings** panel
3. Find **Test Credentials** section
4. Enter your test email address in the **Test Email** field
5. Click **Save Settings**

The email will be stored encrypted and used for all authentication flows.

### 2. Start Crawling an App

1. Select your device in the Device Selector
2. Select the target app package
3. Click **Start Crawl**

The crawler will automatically:
- Detect if the app requires authentication
- Check for stored credentials
- Use stored credentials if available (skip signup)
- Complete signup flow if needed (including email verification)
- Store credentials for future crawls

## How It Works

### First-Time Signup Flow

1. **Detection**: Crawler detects signup screen using AI vision analysis
2. **Form Filling**: Crawler fills signup form with test email and generated credentials
3. **Email Verification**: 
   - Crawler switches to Gmail app
   - Locates verification email
   - Extracts OTP code or clicks confirmation link
   - Returns to target app
   - Completes verification
4. **Credential Storage**: Credentials are encrypted and stored per app package
5. **Continue Crawling**: Crawler proceeds with authenticated session

### Subsequent Crawls (Credential Reuse)

1. **Credential Check**: Crawler checks for stored credentials at crawl start
2. **Auto-Login**: If credentials exist, crawler automatically logs in
3. **Continue Crawling**: Crawler proceeds without signup flow
4. **Fallback**: If login fails, crawler falls back to signup and updates credentials

## Testing

### Test Signup Flow

```bash
# Start crawl on an app requiring signup
mobile-crawler-cli crawl \
  --device emulator-5554 \
  --package com.example.app \
  --model gemini-1.5-pro
```

**Expected Behavior**:
- Crawler detects signup screen
- Fills signup form
- Switches to Gmail to retrieve verification
- Completes signup
- Stores credentials
- Continues crawling

### Test Credential Reuse

```bash
# Run crawl again on same app
mobile-crawler-cli crawl \
  --device emulator-5554 \
  --package com.example.app \
  --model gemini-1.5-pro
```

**Expected Behavior**:
- Crawler detects login screen
- Uses stored credentials automatically
- Logs in successfully
- Continues crawling (no signup flow)

### Verify Credential Storage

Check that credentials are stored:

```python
from mobile_crawler.domain.credential_manager import CredentialManager
from mobile_crawler.infrastructure.user_config_store import UserConfigStore
from mobile_crawler.infrastructure.credential_store import CredentialStore

credential_manager = CredentialManager(
    user_config_store=UserConfigStore(),
    credential_store=CredentialStore()
)

# Check if credentials exist
has_creds = credential_manager.has_credentials("com.example.app")
print(f"Has credentials: {has_creds}")

# List all apps with credentials
apps = credential_manager.list_apps_with_credentials()
print(f"Apps with credentials: {apps}")
```

## Troubleshooting

### Gmail App Not Found

**Error**: `AppSwitchError: Failed to switch to Gmail`

**Solution**:
- Ensure Gmail app is installed: `adb shell pm list packages | grep gmail`
- Ensure Gmail is logged in to test email account
- Verify package name: `com.google.android.gm`

### Verification Email Not Found

**Error**: `GmailInteractionError: Verification email not found`

**Solution**:
- Check Gmail inbox (not spam folder)
- Ensure email was received (check email account)
- Increase timeout in `GmailInteraction.retrieve_verification()`
- Verify test email matches configured email

### OTP Code Not Extracted

**Error**: `VerificationResult.success = False`

**Solution**:
- Check OCR service is working correctly
- Verify email contains visible OTP code (not image)
- Check OTP pattern matches expected format (4-8 digits)
- Try using confirmation link instead (if available)

### Credentials Not Stored

**Error**: Credentials not found on subsequent crawl

**Solution**:
- Check database: `user_config.db` → `app_credentials` table
- Verify encryption is working (check `CredentialStore`)
- Check app package name matches exactly
- Verify signup completed successfully (check logs)

### Login Fails with Stored Credentials

**Behavior**: Crawler falls back to signup flow

**Expected**: This is normal if:
- Password was changed
- Account was locked
- Credentials expired

**Solution**: Crawler automatically handles this by:
- Deleting old credentials
- Completing new signup
- Storing new credentials

## Configuration

### Test Email

Set via UI: Settings → Test Credentials → Test Email

Or via config:
```python
config_manager.set('test_email', 'test@example.com')
```

### Gmail Package Name

Default: `com.google.android.gm`

Can be overridden (if using different email app):
```python
config_manager.set('gmail_package', 'com.custom.email')
```

### Verification Timeout

Default: 30 seconds

Can be configured:
```python
config_manager.set('gmail_verification_timeout', 60)  # 60 seconds
```

## Architecture Overview

```
CrawlerLoop
    ↓
AuthManager (orchestrates)
    ├─→ CredentialManager (storage)
    ├─→ GmailInteraction (email retrieval)
    └─→ AppSwitcher (app switching)
```

**Key Components**:
- `AuthManager`: Main orchestration
- `CredentialManager`: Encrypted credential storage
- `GmailInteraction`: Gmail app interaction and OTP extraction
- `AppSwitcher`: App switching utilities

## Next Steps

1. **Implement Core Modules**: See [tasks.md](tasks.md) for implementation tasks
2. **Add Tests**: Unit tests for each component, integration tests for full flow
3. **Update UI**: Add test email field to Settings panel
4. **Database Migration**: Add `app_credentials` table to `user_config.db`

## Related Documentation

- [Specification](spec.md) - Feature requirements
- [Data Model](data-model.md) - Database schema and entities
- [Contracts](contracts/) - API interfaces
- [Research](research.md) - Technical decisions and rationale
