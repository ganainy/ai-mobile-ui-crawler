# Tasks: Integrate Mailosaur Service

**Feature**: Integrate Mailosaur Service
**Phase**: Implementation
**Spec**: [specs/018-integrate-mailosaur/spec.md](../spec.md)

## Phase 1: Setup

*Goal: Initialize project dependencies and configuration.*

- [x] T001 Add `mailosaur` to `requirements.txt` and install dependency e:\VS-projects\mobile-crawler\requirements.txt
- [x] T002 Create `src/mobile_crawler/infrastructure/mailosaur/` directory structure e:\VS-projects\mobile-crawler\src\mobile_crawler\infrastructure\mailosaur\

## Phase 2: Foundational

*Goal: Establish core service structure and configuration models.*

- [x] T003 Create `MailosaurConfig` data model in `models.py` to hold API credentials e:\VS-projects\mobile-crawler\src\mobile_crawler\infrastructure\mailosaur\models.py
- [x] T004 Create `MailosaurService` class skeleton in `service.py` with `__init__` and `_get_message` helper e:\VS-projects\mobile-crawler\src\mobile_crawler\infrastructure\mailosaur\service.py
- [x] T005 [P] Expose `MailosaurService` in `__init__.py` for easy import e:\VS-projects\mobile-crawler\src\mobile_crawler\infrastructure\mailosaur\__init__.py

## Phase 3: User Story 1 - Retrieve OTP from Email

*Goal: Enable crawler to extract OTP codes from emails.*

- [x] T006 [US1] Create integration test file `test_mailosaur_e2e.py` with initial OTP test case e:\VS-projects\mobile-crawler\tests\integration\test_mailosaur_e2e.py
- [x] T007 [US1] Implement `get_otp` method in `MailosaurService` using SDK code extraction e:\VS-projects\mobile-crawler\src\mobile_crawler\infrastructure\mailosaur\service.py
- [x] T008 [US1] Add timeout handling logic to `_get_message` to satisfy acceptance criteria e:\VS-projects\mobile-crawler\src\mobile_crawler\infrastructure\mailosaur\service.py

## Phase 4: User Story 2 - Retrieve Magic Link from Email

*Goal: Enable crawler to extract verification links.*

- [x] T009 [US2] Update `test_mailosaur_e2e.py` to include magic link extraction test case e:\VS-projects\mobile-crawler\tests\integration\test_mailosaur_e2e.py
- [x] T010 [US2] Implement `get_magic_link` method in `MailosaurService` with optional text matching e:\VS-projects\mobile-crawler\src\mobile_crawler\infrastructure\mailosaur\service.py




## Phase 6: User Story 4 - Standalone Integration Testing

*Goal: Verify the service with a dedicated test suite.*

- [x] T013 [US4] Refine `test_mailosaur_e2e.py` to ensure it can run standalone with env var support e:\VS-projects\mobile-crawler\tests\integration\test_mailosaur_e2e.py
- [x] T014 [US4] Create a helper script or documentation entry for running mailosaur tests isolation e:\VS-projects\mobile-crawler\docs\testing_mailosaur.md

## Final Phase: Polish

- [x] T015 Perform code cleanup and ensure type hints are complete in `infrastructure/mailosaur` e:\VS-projects\mobile-crawler\src\mobile_crawler\infrastructure\mailosaur\
- [x] T016 Verify all integration tests pass with real Mailosaur credentials e:\VS-projects\mobile-crawler\tests\integration\test_mailosaur_e2e.py

## Dependencies

- US1, US2 depend on Phase 2 (Foundation)
- US4 depends on US1, US2 (collection of tests)

## Parallel Execution Opportunities

- T003 (Models) and T004 (Service Skeleton) can be done in parallel.
- Once T004 is done, T007 (OTP) and T010 (Link) can technically be developed in parallel by different devs, but T006/T009 test files share the same destination, so merging is needed.

## Implementation Strategy

1. **MVP**: Setup + US1 (OTP) is the most critical path.
2. **Expansion**: Add Magic Link (US2) support.
3. **Hardening**: Finalize the standalone test suite (US4).
