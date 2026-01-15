# Testing Mailosaur Integration

## Prerequisites

1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variables (if running against real API):
   - `MAILOSAUR_API_KEY`
   - `MAILOSAUR_SERVER_ID`

## Running Tests

To run the integration tests (mocked by default):

```bash
pytest tests/integration/test_mailosaur_service.py
```

The tests verify:
- OTP extraction from email text/html
- Magic link extraction (first link or matching text)
- SMS code extraction
- Timeout handling (mocked via SDK behavior expectation)
