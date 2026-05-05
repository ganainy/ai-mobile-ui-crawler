# Phase 5: Test Coverage & Reliability - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Source:** Direct user request — test main/base functionalities

<domain>
## Phase Boundary

Delivers: A reliable, passing test suite covering all main/base functionality modules with meaningful unit tests. Fixes 56 failing tests and 5 collection errors. Adds tests for 15+ previously-untested source modules representing the core crawl loop, event system, DroidRun integration, ADB interaction, and domain models.

In scope:
- Fix all failing tests (56 failures + 5 collection errors)
- Add unit tests for all core modules without test coverage
- Add unit tests for key domain services without test coverage
- Add unit tests for key infrastructure modules without test coverage
- Establish a green baseline (all tests pass)

Out of scope:
- UI widget tests (existing coverage is adequate)
- Integration tests requiring live devices (existing integration tests are separate)
- Performance/load testing
- Migration to a different test framework
</domain>

<decisions>
## Implementation Decisions

### Testing Framework
- **D-01:** Use existing pytest infrastructure — no framework changes
  - Rationale: pytest is already configured (pytest.ini, pyproject.toml), has fixtures, markers, and 468 passing tests. No reason to change.

### Fix vs. Rewrite Failing Tests
- **D-02:** Fix failing tests to match current API signatures — do not rewrite from scratch unless the original test was testing removed functionality
  - Rationale: Most failures are signature mismatches from Phases 1-3 (Appium removal, state machine additions, method renames). The tests document intent — fix the setup/mocking to match current APIs.

### Collection Errors
- **D-03:** Fix all 5 collection errors — they block the test suite from running
  - `test_crawl_command.py`: Fix IndentationError (backslash continuation issue)
  - `test_mobsf_manager.py`: Fix ImportError (MobSFConfig renamed/removed)
  - `test_auth_e2e.py`: Fix ModuleNotFoundError (missing device_verifier module)
  - `test_stats_dashboard.py` / `test_traffic_capture_manager.py`: Fix duplicate module names (one in unit/, one in domain/)

### Test Design
- **D-04:** Unit tests must use mocked external dependencies (ADB, DroidRun, AI providers, SQLite). No live device or network calls.
  - Rationale: CI environment has no devices or API keys. Tests must be self-contained.

### Coverage Scope
- **D-05:** Prioritize modules by architectural importance: core crawl loop > domain services > infrastructure > config
  - Rationale: Core loop and event system are the heart of the app. If they break, everything breaks.

### Duplicate Test Files
- **D-06:** Remove duplicate `tests/unit/test_traffic_capture_manager.py` — keep `tests/domain/test_traffic_capture_manager.py` (closer to source). Remove `tests/unit/test_stats_dashboard.py` — keep `tests/ui/test_stats_dashboard.py` (UI widget tests belong in ui/).
  - Rationale: Duplicate test module names cause import resolution errors. Keep the version closer to the source module.

### the agent's Discretion
- Exact test case names and assertion details per module
- Whether to use pytest fixtures vs. direct setup in each test class
- Mock granularity (full mock vs. partial mock) per module
- Whether untested data-only modules (models.py, dtos.py) need test files or just import validation
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Testing Conventions
- `.planning/codebase/TESTING.md` — Test framework, patterns, fixture locations, mocking conventions
- `.planning/codebase/CONVENTIONS.md` — Naming, code style, import organization
- `pytest.ini` — Test configuration, markers, paths

### Core Source Modules (need test coverage)
- `src/mobile_crawler/core/crawler_loop.py` — Main crawl orchestrator
- `src/mobile_crawler/core/crawler_event_listener.py` — Event listener contract (ABC)
- `src/mobile_crawler/core/log_sinks.py` — Logging sink abstractions
- `src/mobile_crawler/core/logging_service.py` — Logging service
- `src/mobile_crawler/domain/droidrun_agent_service.py` — DroidRun integration hub (1120 lines)
- `src/mobile_crawler/domain/adb_action_executor.py` — ADB action execution
- `src/mobile_crawler/domain/models.py` — Domain data models
- `src/mobile_crawler/domain/ui_context.py` — UI context model
- `src/mobile_crawler/infrastructure/adb_input_handler.py` — ADB input handling
- `src/mobile_crawler/infrastructure/ai_interaction_repository.py` — AI interaction persistence

### Existing Test Files (need fixes)
- `tests/cli/test_crawl_command.py` — IndentationError (collection fails)
- `tests/cli/test_delete_command.py` — 2 failures
- `tests/cli/test_main.py` — 1 failure (exit code assertion)
- `tests/config/test_config_manager.py` — 1 failure
- `tests/core/test_crawl_state_machine.py` — 1 failure (enum values)
- `tests/core/test_pre_crawl_validator.py` — 15 failures (API signature changes)
- `tests/core/test_runtime_stats_collector.py` — 4 failures
- `tests/core/test_stale_run_cleaner.py` — 13 failures
- `tests/domain/providers/test_vision_detector.py` — 2 failures (model fetching)
- `tests/domain/test_report_generator.py` — 4 failures
- `tests/domain/test_traffic_capture_manager.py` — 4 failures
- `tests/infrastructure/test_ai_interaction_service.py` — 1 failure
- `tests/infrastructure/test_session_folder_manager.py` — 4 failures
- `tests/infrastructure/test_mobsf_manager.py` — ImportError (collection fails)
- `tests/integration/test_auth_e2e.py` — ModuleNotFoundError (collection fails)

### Duplicate Test Files (need removal)
- `tests/unit/test_traffic_capture_manager.py` — Duplicate of `tests/domain/test_traffic_capture_manager.py`
- `tests/unit/test_stats_dashboard.py` — Duplicate of `tests/ui/test_stats_dashboard.py`
</canonical_refs>

<specifics>
## Specific Ideas

- Fix collection errors first — they prevent the entire test suite from running
- For `test_crawl_command.py`: Fix the backslash continuation indentation error at line 72
- For `test_mobsf_manager.py`: Update import to match renamed/removed MobSFConfig class
- For `test_auth_e2e.py`: Either create the missing `device_verifier` module or remove the import
- For duplicate test modules: Delete `tests/unit/test_traffic_capture_manager.py` and `tests/unit/test_stats_dashboard.py`
- For `test_pre_crawl_validator.py`: Update all 15 tests to match current PreCrawlValidator signature (likely changed during Phases 1-3)
- For `test_stale_run_cleaner.py`: Update 13 tests — likely signature changes in StaleRunCleaner or VideoRecordingManager
- For `test_crawl_state_machine.py::test_enum_values`: Update to match current CrawlState enum members
- For crawler_event_listener tests: Create a concrete test subclass that verifies the ABC contract (all methods callable, default implementations work)
- For droidrun_agent_service tests: Mock DroidRun dependency heavily — test service initialization, cleanup, step tracking, and error handling
</specifics>

<deferred>
## Deferred Ideas

- Coverage percentage targets (e.g., "80% line coverage") — establish baseline first, set targets later
- CI/CD pipeline setup — separate concern, will be addressed later
- Property-based testing or mutation testing — overkill for baseline establishment
- Adding tests for UI widgets (already have adequate coverage) — not base functionality
- Adding tests for CLI commands beyond fixing existing ones — CLI is thin, model tests cover logic
- Refactoring test infrastructure (conftest changes, shared fixture modules) — keep changes minimal to fix failures
</deferred>

---
*Phase: 05-test-coverage-reliability*
*Context gathered: 2026-05-05*