---
author: claude
date: 2026-09-19
---
# Issue #11: Authentication as first Guided Scenario

- New `domain/authentication.py`: `AuthenticationSession` builds the goal text (sign up if no App Account, else log in, re-login after logout) and the agent tools `get_email_code`, `get_sms_code`, `save_app_account`, `skip_authentication`.
- Code tools share a hard attempt cap (default 3). Email/SMS failure or missing inbox routes to Human Fallback (CODE request); no answer, timeout or Fallback off records "authentication skipped" and the crawl continues on reachable screens.
- `CrawlerAgentService._create_exploration_goal` prepends the section ("FIRST GUIDED SCENARIO - AUTHENTICATION") and passes tools as `custom_tools`; `_run_outcome_details` returns `auth_note` (logged, not yet persisted on the run/report).
- `CrawlerLoop(human_prompter=...)` is fed by `QtHumanPrompter` created in `MainWindow`.
- Sign-up password is generated per run; sign-up address is `name+package@gmail.com` (or the App Account override).
- Tests: `tests/domain/test_authentication.py`, plus goal/tool test in `test_crawler_agent_service.py`. Full suite: 1426 passed, 7 skipped.
- Not done: manual check on a real app needing email verification (acceptance item); `auth_note` in Run Report.

## Test speedup (same day)
Full suite 5m28s -> 3m34s (commit 2bbbba6): virtual clock in `test_traffic_capture_manager.py`, `pre_crawl_wake_device: False` in traffic-capture loop tests (they called real adb), leaked-connection cleanup in `test_screen_repository.py`. Root cause not fixed: `DatabaseManager.get_connection()` opens an unclosed connection per call, locking the file on Windows.
Note: unstaged edits in `crawler_agent_service.py`, `input_dictionary.py`, `prompt_builder.py`, `sms_reader.py`, `main_window.py`, `settings_panel.py` appeared after the commits; not made deliberately, left untouched.
