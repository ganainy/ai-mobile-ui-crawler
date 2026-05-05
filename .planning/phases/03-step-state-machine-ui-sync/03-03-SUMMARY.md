---
phase: 03-step-state-machine-ui-sync
plan: 03
subsystem: domain
tags: [async, polling, wait-predicate, adaptive-timeout, ui-sync]

# Dependency graph
requires:
  - phase: 02-remove-appium
    provides: "ADB/DroidRun provider layer (state_provider interface)"
provides:
  - "UIWaitPredicate class with wait_for_ui_settled polling loop"
  - "AdaptiveWaitConfig with per-action-type timeout/poll profiles"
  - "WaitProfile dataclass with ms-to-s conversions"
  - "18 wait_* config defaults in defaults.py"
affects: [03-04, "ADBActionExecutor integration"]

# Tech tracking
tech-stack:
  added: [pytest-asyncio]
  patterns: [polling-based-wait, adaptive-timeout-profiles, protocol-based-dependency]

key-files:
  created:
    - src/mobile_crawler/domain/ui_wait_predicate.py
    - tests/domain/test_ui_wait_predicate.py
  modified:
    - src/mobile_crawler/config/defaults.py

key-decisions:
  - "Used Protocol (structural typing) for StateProvider dependency instead of abstract base class"
  - "Caching profiles in AdaptiveWaitConfig._profiles dict to avoid repeated config lookups"
  - "Monotonic deadline enforcement ensures wait always terminates within timeout_ms + one poll_interval"

patterns-established:
  - "Polling-based wait: poll state_provider at configured intervals, compare consecutive formatted_text reads"
  - "Adaptive profiles: per-action-type timeout/poll_interval with config override support"
  - "Exception-tolerant polling: catch and log provider exceptions, retry until deadline"

requirements-completed: [SYNC-01]

# Metrics
duration: 3min
completed: 2026-05-05
---

# Phase 3 Plan 03: Replace Fixed Sleeps with Explicit Wait Predicates Summary

**Polling-based UIWaitPredicate with adaptive per-action-type wait profiles replacing fixed-duration sleeps in ADBActionExecutor**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-05T18:40:14Z
- **Completed:** 2026-05-05T18:43:25Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- UIWaitPredicate.wait_for_ui_settled polls state_provider until two consecutive formatted_text reads match (UI settled)
- AdaptiveWaitConfig provides per-action-type profiles (tap=2s, scroll=1.5s, start_app=5s, default=3s) with ConfigManager override support
- 18 wait_* defaults added to config/defaults.py covering all action types
- Graceful exception handling during polls with retry-until-deadline pattern
- All 12 async tests pass (10 test methods, 12 collected with parameterization)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for UIWaitPredicate** - `b60e0c6` (test)
2. **Task 1 (GREEN): Implement UIWaitPredicate with adaptive wait profiles** - `afa9a0d` (feat)

_Note: TDD flow - test commit followed by implementation commit_

## Files Created/Modified
- `src/mobile_crawler/domain/ui_wait_predicate.py` - UIWaitPredicate, AdaptiveWaitConfig, WaitProfile, DEFAULT_WAIT_PROFILES, StateProvider protocol
- `src/mobile_crawler/config/defaults.py` - Added 18 wait_* timeout and poll_interval defaults for all action types
- `tests/domain/test_ui_wait_predicate.py` - 12 tests covering settle detection, timeout, profiles, polling, exceptions, config override

## Decisions Made
- Used Protocol (structural typing) for StateProvider dependency -- enables duck-typing with any async get_state() provider without inheritance
- Cached profiles in AdaptiveWaitConfig._profiles dict -- avoids repeated config_manager.get() calls for the same action type
- Monotonic deadline enforcement -- time.monotonic() prevents wall-clock issues and ensures loop terminates

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed pytest-asyncio dependency**
- **Found during:** Task 1 (test setup)
- **Issue:** pytest-asyncio not in project dependencies; async test markers require it
- **Fix:** Installed pytest-asyncio via pip
- **Files modified:** None (environment dependency only)
- **Verification:** All 12 async tests pass
- **Committed in:** Not committed (dev dependency, not code change)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor -- pytest-asyncio is a standard dev dependency for async testing. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- UIWaitPredicate ready for integration into ADBActionExecutor (replaces _action_delay_ms=1500 and time.sleep() calls)
- AdaptiveWaitConfig can be wired through existing ConfigManager for user-configurable timeouts
- Plan 03-04 can reference UIWaitPredicate.wait_for_ui_settled in the step state machine transitions

---
*Phase: 03-step-state-machine-ui-sync*
*Completed: 2026-05-05*

## Self-Check: PASSED

All files verified present:
- src/mobile_crawler/domain/ui_wait_predicate.py
- src/mobile_crawler/config/defaults.py
- tests/domain/test_ui_wait_predicate.py
- .planning/phases/03-step-state-machine-ui-sync/03-03-SUMMARY.md

All commits verified:
- b60e0c6 (RED: failing tests)
- afa9a0d (GREEN: implementation passing all tests)
