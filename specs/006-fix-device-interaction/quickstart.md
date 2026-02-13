# Quickstart: Device Verification

## Prerequisites

1.  **Appium Server**: Must be running (`npx appium`).
2.  **Device**: Local Android device connected via ADB.
3.  **Target App**: The `com.example.flutter_application_1` app must be installed.

## Running the Verification Suite

Run the provided script to verify all actions:

```bash
python scripts/verify_device_interactions.py
```

### Options

Verify only "tap" actions:
```bash
python scripts/verify_device_interactions.py --test-type tap
```

Verify with a custom package (if not the default):
```bash
python scripts/verify_device_interactions.py --package com.my.other.app
```

## Interpreting Results

- **PASS**: All listed actions worked successfully on the device. The AppiumDriver is safe to use.
- **FAIL**: The log will indicate which action failed (e.g., `test_coordinate_tap`).
    - **Fix**: Check `src/mobile_crawler/infrastructure/appium_driver.py` adjustments.
    - **Fix**: Ensure the device screen was not locked.
