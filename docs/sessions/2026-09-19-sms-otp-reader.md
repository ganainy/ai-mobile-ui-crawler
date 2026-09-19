---
author: claude
date: 2026-09-19
---
# Issue #9: SMS OTP reader over adb

New standalone module `infrastructure/sms_reader.py` (`SmsReader`), tests in `tests/infrastructure/test_sms_reader.py` (mocked adb output).

- `has_sim` / `check_sim`: `getprop gsm.sim.state`; `check_sim` returns `NO_SIM_WARNING` when there is no SIM (caller shows it before the run).
- `read_otp`: polls `content query --uri content://sms/inbox` (non-rooted), keeps SMS newer than `since_ms` (default: device time), returns the first 4-8 digit code from the newest match.
- Result status `FOUND` / `TIMEOUT` / `UNREADABLE`; `UNREADABLE` (permission denied, adb failure) is the signal for Human Fallback (#10).
- Not wired into the agent yet: that is #11 ("get SMS code" tool). Not tried on a real device: OEMs may deny `content query` on SMS.
- Full suite has 7 unrelated failures (`test_crawler_agent_finalize`, `test_crawler_agent_service` wire observers, `test_crawl_control_panel` stopping state) in files touched by uncommitted #6 work.
