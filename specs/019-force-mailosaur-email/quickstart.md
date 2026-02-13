# Quickstart: Force Mailosaur for Email Verification

**Feature**: 019-force-mailosaur-email  
**Date**: 2026-01-15

## Prerequisites

1. **Mailosaur Account**: Sign up at [mailosaur.com](https://mailosaur.com)
2. **API Key**: Get from Mailosaur Dashboard → API Settings
3. **Server ID**: Get from Mailosaur Dashboard → Servers (8-character ID)

## Configuration

### Option 1: Environment Variables (Recommended for CI/CD)

```bash
export MAILOSAUR_API_KEY="your-api-key-here"
export MAILOSAUR_SERVER_ID="abc12345"
```

### Option 2: UI Configuration

1. Open Mobile Crawler
2. Navigate to Settings panel
3. Fill in:
   - **Mailosaur API Key**: Your API key
   - **Mailosaur Server ID**: Your server ID (e.g., `abc12345`)
   - **Test Email**: Your Mailosaur test email (e.g., `test@abc12345.mailosaur.net`)
4. Click Save

## Usage

### Test Email Address Format

Mailosaur email addresses follow this pattern:
```
anything@<server-id>.mailosaur.net
```

Examples:
- `test@abc12345.mailosaur.net`
- `signup-test@abc12345.mailosaur.net`
- `user123@abc12345.mailosaur.net`

### Running a Crawl with Email Verification

1. Configure your Mailosaur credentials (see above)
2. Set the Test Email in Settings
3. Start a crawl of an app that sends verification emails
4. When the AI detects email verification is needed:
   - For OTP: `MailosaurService.get_otp()` retrieves the code
   - For Magic Links: `MailosaurService.get_magic_link()` retrieves the URL

### Manual Testing

Run the Mailosaur integration tests:

```bash
cd src
pytest tests/integration/test_mailosaur_e2e.py -v
```

## Verification

After implementation, verify the migration:

```bash
# 1. Check Gmail code is removed
find src tests -name "*gmail*" -type f  # Should return nothing

# 2. Check imports work
python -c "from mobile_crawler.infrastructure.mailosaur.service import MailosaurService; print('OK')"

# 3. Run tests
pytest tests/integration/test_mailosaur_e2e.py -v
pytest tests/unit/infrastructure/mailosaur/ -v
```

## Troubleshooting

### "Mailosaur service not configured"

**Cause**: Missing API key or Server ID

**Fix**: Set environment variables or configure via UI:
```bash
export MAILOSAUR_API_KEY="..."
export MAILOSAUR_SERVER_ID="..."
```

### "No email received within timeout"

**Cause**: Email not sent, or sent to wrong address

**Fix**:
1. Verify the test email matches Mailosaur server ID
2. Check that the app actually sent an email
3. Increase timeout if network is slow

### "No OTP found in email"

**Cause**: Email doesn't contain recognizable OTP format

**Fix**: Mailosaur looks for codes in `message.html.codes` and `message.text.codes`. Verify the email contains a recognizable verification code.

### Import errors after migration

**Cause**: Old Gmail imports still present

**Fix**: Search and remove any remaining Gmail references:
```bash
grep -r "gmail" src/ --include="*.py"
```
