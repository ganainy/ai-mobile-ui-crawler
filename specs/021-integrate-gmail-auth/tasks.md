# Tasks: Integrate Gmail Auth

## Phase 1: Foundational Design & Research
- [x] T001 Conduct research on Gmail account switching UI selectors in Android
- [x] T002 Update `data-model.md` to include `target_account` in `GmailAutomationConfig`
- [x] T003 Update `contracts/gmail_service.py` to ensure it aligns with requirements

## Phase 2: Configuration & UI Integration
- [x] T004 Update `src/mobile_crawler/ui/widgets/settings_panel.py` to add "Test Gmail Account" field in the "Test Credentials" section
- [x] T005 Update `src/mobile_crawler/ui/widgets/settings_panel.py` load/save methods for `test_gmail_account`
- [x] T006 Update `src/mobile_crawler/config/config_manager.py` to handle `gmail_account` in the global config object

## Phase 3: Gmail Infrastructure Porting
- [x] T007 Port `config.py` with standard Gmail selectors and patterns
- [x] T008 Port `reader.py` with `OTPResult`, `GmailReader` logic
- [x] T009 Port `navigator.py` with `GmailNavigator` logic
- [x] T010 Port `app_switcher.py` with `AppSwitcher` logic
- [x] T011 Port `clipboard.py` with `ClipboardHelper` logic

## Phase 4: Account Switching Implementation
- [x] T012 Implement `GmailAccountSwitcher` logic (likely in `navigator.py` or new `account_switcher.py`)
- [x] T013 Update `GmailNavigator` to perform auto-switching if the configured `target_account` mismatch is detected

## Phase 5: Service Orchestration & E2E Verification
- [x] T014 Implement `GmailService` orchestration in `service.py`
- [x] T015 Update `GmailService` to pass the `target_account` from global config to the navigator
- [x] T016 Refactor `tests/integration/test_auth_gmail_e2e.py` to use the new service
- [x] T017 Add a specific test case for account switching verification (if possible with multiple mock accounts)
- [x] T018 Final verification of `extract_otp` and `click_verification_link` flows
