# Requirements: Mobile UI Crawler

**Defined:** 2026-05-01
**Core Value:** Maximize reliable discovery of unique app screens and states while preserving resumable run history for analysis.

## v1.0 Requirements

### Step State Machine (DURB)

- [x] **DURB-01**: Crawl steps transition through explicit phases (CAPTURE -> DECIDE -> EXECUTE -> RECORD -> CHECKPOINT) with each transition persisted
- [x] **DURB-02**: Step phase state survives process restart and can be inspected from storage
- [x] **DURB-03**: Step state is queryable for observability (current phase, timing, step count)

### Error Model (ERRO)

- [ ] **ERRO-01**: All critical-path exceptions use typed taxonomy (retryable, fatal, operator-actionable) — no bare `except: pass`
- [ ] **ERRO-02**: Error logs include structured context (run_id, step_id, action type, device state) for every failure
- [ ] **ERRO-03**: Recorder and checkpoint failures halt the run (fail-closed) rather than continuing silently
- [ ] **ERRO-04**: Existing blanket exception handlers in crawl loop are replaced with typed handling

### UI Synchronization (SYNC)

- [ ] **SYNC-01**: Actions use explicit wait predicates (element visible, UI settled) instead of fixed-duration sleeps
- [ ] **SYNC-02**: Each action is followed by verification that the expected UI transition occurred
- [ ] **SYNC-03**: Wait timing adapts by action type (tap, scroll, input, navigate) with configurable backoff

### Provider Simplification (PROV)

- [ ] **PROV-01**: Appium provider adapter is removed from the codebase entirely
- [ ] **PROV-02**: All device interaction goes through ADB/DroidRun path only
- [ ] **PROV-03**: Provider layer simplified to single ADB/DroidRun adapter with no Appium remnants

### ADB Context (CTX)

- [ ] **CTX-01**: Current package and activity are captured via ADB and persisted each step
- [ ] **CTX-02**: UI tree dump is validated (succeeded, parseable, non-empty) before decision layer processes it
- [ ] **CTX-03**: Unintended app switches (home press, notification pull, recents) are detected and trigger recovery back to target app

### Test Coverage (TEST)

- [ ] **TEST-01**: The entire test suite passes with zero failures and zero collection errors (`pytest tests/` exits 0)
- [ ] **TEST-02**: Every core module (crawler_loop, crawler_event_listener, crawl_controller, log_sinks, logging_service) has a corresponding test file with ≥3 meaningful test cases covering main functionality
- [ ] **TEST-03**: Every key domain service (droidrun_agent_service, adb_action_executor, ui_context, models, providers/registry) has a corresponding test file with ≥3 meaningful test cases covering main functionality

## v2 Requirements

Deferred to future milestone.

### Durable Run State (continued)

- **DURB-04**: Crawler resumes from last checkpoint after crash/restart without duplicating actions
- **DURB-05**: Step events are idempotent — retries produce no duplicate records using (run_id, step_id, phase) uniqueness keys
- **DURB-06**: Run lease with heartbeat prevents concurrent modification of same run
- **DURB-07**: Checkpoint data includes all context needed to continue (step cursor, device state, AI history)

### Coverage Intelligence

- **COV-01**: Composite screen fingerprint combining UI tree structure, text tokens, package/activity
- **COV-02**: Transition graph service tracks state-to-state navigation edges
- **COV-03**: Exploration policy uses novelty scoring to prioritize underexplored branches
- **COV-04**: Coverage metrics (unique states, revisit ratio, novelty decay) computed incrementally

### Report Quality

- **RPT-01**: Coverage reports include state transition graphs with visual exploration paths
- **RPT-02**: Run comparison shows diff of discovered states between sessions
- **RPT-03**: Exploration quality scoring highlights dead-ends, shallow coverage areas

## Out of Scope

| Feature | Reason |
|---------|--------|
| Fully autonomous login/CAPTCHA bypass | Fragile, high-risk, non-core value |
| Cloud multi-device orchestration | Single local operator is current target |
| OmniParser integration improvements | Deferred to coverage-focused milestone |
| Real-time monitoring dashboard | CLI/GUI monitoring sufficient for v1.0 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DURB-01 | Phase 3 | Complete (03-01) |
| DURB-02 | Phase 3 | Complete (03-01) |
| DURB-03 | Phase 3 | Complete (03-02) |
| ERRO-01 | Phase 1 | Pending |
| ERRO-02 | Phase 1 | Pending |
| ERRO-03 | Phase 1 | Pending |
| ERRO-04 | Phase 1 | Pending |
| SYNC-01 | Phase 3 | Pending |
| SYNC-02 | Phase 3 | Pending |
| SYNC-03 | Phase 3 | Pending |
| PROV-01 | Phase 2 | Pending |
| PROV-02 | Phase 2 | Pending |
| PROV-03 | Phase 2 | Pending |
| CTX-01 | Phase 4 | Pending |
| CTX-02 | Phase 4 | Pending |
| CTX-03 | Phase 4 | Pending |
| TEST-01 | Phase 5 | Pending |
| TEST-02 | Phase 5 | Pending |
| TEST-03 | Phase 5 | Pending |

**Coverage:**
- v1.0 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0

---
*Requirements defined: 2026-05-01*
*Last updated: 2026-05-01 after roadmap creation*
