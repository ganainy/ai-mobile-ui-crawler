# Tasks: UiAutomator2 Crash Detection & Recovery

This document tracks the tasks for implementing automatic detection and recovery from UiAutomator2 crashes.

## Phase 1: Setup & Data Models (Priority: P0) ✅

- [x] T001 Define `UIAUTOMATOR2_CRASH_PATTERNS` in `src/mobile_crawler/core/uiautomator_recovery.py` ✅
- [x] T002 Implement `is_uiautomator2_crash(exception)` utility ✅
- [x] T003 Define `RecoveryConfig` and `RecoveryState` dataclasses ✅
- [x] T004 Define `RecoveryResult` dataclass ✅
- [x] T005 Update `ActionResult` in `src/mobile_crawler/domain/models.py` to include `was_retried`, `retry_count`, and `recovery_time_ms` ✅

## Phase 2: Foundational Recovery Logic (Priority: P1) ✅

- [x] T006 Add `restart_uiautomator2()` method to `AppiumDriver` in `src/mobile_crawler/infrastructure/appium_driver.py` ✅
- [x] T007 Implement `UiAutomatorRecoveryManager.attempt_recovery()` ✅
- [x] T008 Add `is_uiautomator2_crash` helper to `UiAutomatorRecoveryManager` ✅
- [x] T009 Implement `UiAutomatorRecoveryManager.should_retry()` ✅
- [x] T010 Implement `UiAutomatorRecoveryManager.reset_for_new_step()` ✅
- [x] T011 Update `GestureHandler` methods to re-raise `WebDriverException` for crash patterns ✅

## Phase 3: User Story 1 - Automatic Recovery (Priority: P1) ✅

**Goal**: Automatically detect crash and restart session once.

- [x] T012 Integrate `UiAutomatorRecoveryManager` into `CrawlerLoop.__init__()` ✅
- [x] T013 Implement `CrawlerLoop._execute_action_with_recovery()` helper ✅
- [x] T014 Modify `CrawlerLoop._execute_step()` to use `_execute_action_with_recovery()` ✅
- [x] T015 Implement `_ensure_app_foreground()` in `CrawlerLoop` ✅

### Tests for User Story 1

- [x] T016 Add unit test `test_is_uiautomator2_crash_detection` ✅
- [x] T017 Add unit test `test_recovery_state_tracking` ✅
- [x] T018 Add unit test `test_recovery_manager_attempts_restart` ✅
- [x] T019 Add integration test `test_recovery_from_single_crash` in `tests/integration/test_crash_recovery.py` ✅

## Phase 4: User Story 2 - Configurable Retry Behavior (Priority: P2) ✅

**Goal**: Support multiple retries and configurable delays.

- [x] T030 Add unit test `test_recovery_respects_max_attempts` ✅
- [x] T031 Add unit test `test_recovery_manager_uses_config_values` ✅
- [x] T032 Add config keys to `DEFAULTS` in `src/mobile_crawler/config/defaults.py` ✅
- [x] T033 Modify `CrawlerLoop.__init__()` to read recovery config from `ConfigManager` ✅
- [x] T034 Add counter reset logic on successful action in `CrawlerLoop._execute_action_with_recovery()` ✅
- [x] T035 Add graceful crawl termination when max attempts exhausted ✅
- [x] T036 Update `Run` status to `RECOVERY_FAILED` when exhausted ✅
- [x] T037 Add integration test `test_recovery_exhausted` in `tests/integration/test_crash_recovery.py` ✅

## Phase 5: User Story 3 - Logging & Visibility (Priority: P3) ✅

- [x] T038 Add `on_recovery_started` event emission ✅
- [x] T039 Add `on_recovery_completed` event emission ✅
- [x] T040 Add `on_recovery_exhausted` event emission ✅
- [x] T041 Ensure `ActionResult` fields are populated after recovery ✅
- [x] T042 Update `StepLog` and database schema for recovery tracking ✅
- [x] T043 Update `run_stats` with recovery metrics ✅
- [x] T044 Add logging for recovery events ✅
- [x] T045 Update `CrawlerEventListener` and `SignalAdapter` for recovery events ✅

## Phase 6: Polish & Cross-Cutting Concerns ✅

- [x] T046 Update README.md with Phase 5 completion ✅
- [x] T047 Add implementation notes to dev docs ✅
- [x] T048 Verify all tests pass (Unit & Integration) ✅
- [x] T049 Final check for dead code or missing docstrings ✅
