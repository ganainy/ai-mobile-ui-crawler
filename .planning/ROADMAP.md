# Roadmap: Mobile UI Crawler - v1.0 Crawl Stability & Resumability

## Overview

Transform the crawler from a crash-fragile, silently-failing loop into a durable system with typed error handling, a single ADB/DroidRun device path, explicit step state machine, reliable UI synchronization, and ADB-powered context guardrails. The build order follows the dependency chain: errors must be typed before they can be trusted, Appium must be removed before ADB context work can proceed, and UI sync depends on having a clean device interaction layer.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Error Model Overhaul** - Replace blanket exception handling with typed taxonomy and structured failure context
- [ ] **Phase 2: Remove Appium** - Eliminate Appium provider, consolidate to single ADB/DroidRun device path
- [ ] **Phase 3: Step State Machine & UI Sync** - Durable step phases with persisted transitions and explicit wait/verify actions
- [ ] **Phase 4: ADB Context Guardrails** - Capture device context per step, validate UI dumps, detect and recover from app switches
- [ ] **Phase 5: Test Coverage & Reliability** - Fix all failing tests, add unit tests for main/base functionality modules

## Phase Details

### Phase 1: Error Model Overhaul
**Goal**: Every crawl-loop failure is classified, contextualized, and fails closed on critical paths
**Depends on**: Nothing (first phase)
**Requirements**: ERRO-01, ERRO-02, ERRO-03, ERRO-04
**Success Criteria** (what must be TRUE):
  1. No bare `except: pass` or `except Exception` handlers remain in the crawl loop or device interaction code
  2. Every caught exception is classified as retryable, fatal, or operator-actionable with a typed exception class
  3. Error log entries include run_id, step_id, action type, and device state context for every failure
  4. A recorder or checkpoint failure immediately halts the run instead of continuing silently
**Plans**: 3 plans

Plans:
**Wave 1**
- [x] 01-01: Implement typed exception taxonomy and replace blanket handlers
**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-02: Add structured error logging with run/step/device context
- [x] 01-03: Enforce fail-closed behavior on recorder and checkpoint paths

### Phase 2: Remove Appium
**Goal**: All device interaction flows through a single ADB/DroidRun adapter with zero Appium remnants
**Depends on**: Phase 1
**Requirements**: PROV-01, PROV-02, PROV-03
**Success Criteria** (what must be TRUE):
  1. No Appium imports, dependencies, configuration, or provider adapter code remains in the codebase
  2. All crawl actions (tap, scroll, input, navigate) execute successfully through the ADB/DroidRun path alone
  3. The provider layer is a single adapter with no abstraction for swappable providers
**Plans**: 3 plans

Plans:
**Wave 1**
- [x] 02-01: Remove Appium dependency and code remnants from project files
- [x] 02-02: Consolidate provider layer to single ADB/DroidRun adapter and update scripts/docs
**Wave 2** *(blocked on Wave 1 completion)*
- [x] 02-03: Verify all device interactions work through ADB/DroidRun only

### Phase 3: Step State Machine & UI Sync
**Goal**: Crawl steps follow a persisted phase lifecycle and every action waits for the UI to be ready before and after execution
**Depends on**: Phase 2
**Requirements**: DURB-01, DURB-02, DURB-03, SYNC-01, SYNC-02, SYNC-03
**Success Criteria** (what must be TRUE):
  1. Each crawl step transitions through CAPTURE, DECIDE, EXECUTE, RECORD, and CHECKPOINT phases with every transition persisted to storage
  2. After a process restart, the step phase state can be loaded from storage and inspected (current phase, timing, step count)
  3. Actions wait for explicit readiness predicates (element visible, UI settled) instead of using fixed-duration sleeps
  4. Each action is followed by a verification step confirming the expected UI transition occurred
  5. Wait durations adapt by action type (tap, scroll, input, navigate) with configurable backoff parameters
**Plans**: 4 plans

Plans:
**Wave 1** (parallel, no dependencies between them)
- [x] 03-01: Implement step state machine with persisted phase transitions (DURB-01, DURB-02)
- [x] 03-03: Replace fixed sleeps with explicit wait predicates (SYNC-01)
**Wave 2** *(blocked on Wave 1 completion)*
- [x] 03-02: Add step observability queries and event listener callback (DURB-03)
- [ ] 03-04: Wire action verifier, adaptive wait, and event stream into DroidRun (SYNC-02, SYNC-03)

### Phase 4: ADB Context Guardrails
**Goal**: Device context is captured and validated every step, with automatic recovery from unintended app switches
**Depends on**: Phase 3
**Requirements**: CTX-01, CTX-02, CTX-03
**Success Criteria** (what must be TRUE):
  1. Current package and activity are captured via ADB and persisted alongside each step record
  2. UI tree dumps are validated (succeeded, parseable, non-empty) before the decision layer processes them
  3. Unintended app switches (home press, notification pull, recents screen) are detected and the crawler automatically navigates back to the target app
**Plans**: 3 plans

Plans:
- [ ] 04-01: Capture and persist package/activity context per step
- [ ] 04-02: Add UI tree dump validation before decision processing
- [ ] 04-03: Implement app-switch detection and recovery

### Phase 5: Test Coverage & Reliability
**Goal**: All main/base functionality modules have reliable unit tests and the entire test suite passes with zero failures
**Depends on**: Phase 3 (step state machine, error model, and Appium removal must be stable for test fixes)
**Requirements**: TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):
  1. `pytest tests/` exits with 0 failures and 0 collection errors
  2. Every core module (crawler_loop, crawler_event_listener, crawl_controller, log_sinks, logging_service) has a test file with ≥3 meaningful test cases
  3. Every key domain service (droidrun_agent_service, adb_action_executor, ui_context, models, providers/registry) has a test file with ≥3 meaningful test cases
  4. All previously-failing 56 tests are fixed and passing
  5. All 5 collection errors are resolved (syntax errors fixed, import mismatches corrected, duplicate modules removed)
  6. No test file duplicates exist (unit/ and domain/ or ui/ copies of same test)
**Plans**: 2 plans

Plans:
**Wave 1**
- [ ] 05-01: Fix all failing tests and collection errors, establish green baseline
- [ ] 05-02: Add unit tests for core, domain, and infrastructure modules without coverage

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Error Model Overhaul | 3/3 | Complete | 2026-05-01 |
| 2. Remove Appium | 3/3 | Complete | 2026-05-01 |
| 3. Step State Machine & UI Sync | 3/4 | In progress | - |
| 4. ADB Context Guardrails | 0/3 | Not started | - |
| 5. Test Coverage & Reliability | 0/2 | Not started | - |
