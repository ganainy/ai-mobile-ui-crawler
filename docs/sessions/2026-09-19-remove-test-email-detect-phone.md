---
author: claude
date: 2026-09-19
---
# Remove Test Email field, detect phone from SIM

- Removed the "Test Email Address" field from Settings (Form Fill Data). The stored `test_email` setting is purged on load.
- Form email now comes from `get_form_email` (`prompt_builder.py`): App Account address override, else Verification Inbox plus-address (`name+<package>@gmail.com`), else empty.
- Phone: `SmsReader.read_own_number` reads `content://telephony/siminfo` over adb (best effort; often empty on non-rooted devices / carriers that don't store the number). `CrawlerAgentService._detect_device_phone` runs before each goal is built and stores `detected_phone` in the in-memory config; the manual Mobile Number field overrides it (`get_form_phone`).
- Not verified on a real device: whether siminfo returns a number there.
