# Implementation Tasks: Fix Screen Deduplication

**Feature**: `004-fix-screen-deduplication`
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)

## Phase 1: Setup
*Goal: Ensure development environment and dependencies are ready.*

- [X] T001 Setup: Verify `imagehash` dependency is available in environment

## Phase 2: Foundational
*Goal: Implement configuration changes and prepare core components.*

- [X] T002 Foundational: Add `screen_similarity_threshold` and `use_perceptual_hashing` to `CrawlerConfig` in `src/mobile_crawler/domain/models.py`
- [X] T003 Foundational: Update `ScreenTracker.__init__` to accept configuration values in `src/mobile_crawler/domain/screen_tracker.py`
- [X] T003b Foundational: Implement database reset/clear logic (or manual instruction) to remove incompatible legacy hashes (FR-006)

## Phase 3: User Story 1 - Accurate Unique Screen Detection (P1)
*Goal: Replace 256-bit pHash with 64-bit dHash and implement robust deduplication logic.*
*Independent Test: Unit tests pass showing carousel variations resolve to same screen ID.*

- [X] T004 [US1] Create unit tests for screen hashing and deduplication in `tests/unit/domain/test_screen_tracker.py`
- [X] T005 [P] [US1] Implement `dHash` (size=8) algorithm in `ScreenTracker._generate_hash` at `src/mobile_crawler/domain/screen_tracker.py`
- [X] T006 [US1] Implement status bar exclusion (top 100px crop) in `ScreenTracker._generate_hash` at `src/mobile_crawler/domain/screen_tracker.py`
- [X] T007 [US1] Update `ScreenTracker._find_similar_screen` to use Hamming distance comparison with configured threshold in `src/mobile_crawler/domain/screen_tracker.py`
- [X] T008 [P] [US1] Update `ScreenRepository.find_similar_screens` to support threshold-based lookup in `src/mobile_crawler/infrastructure/screen_repository.py`
- [X] T009 [US1] Verify hashing and lookup logic with new unit tests

## Phase 4: User Story 2 - Configurable Threshold & Signals (P2)
*Goal: Ensure similarity threshold is configurable and novel signals are accurate.*
*Independent Test: Changing config value changes deduplication behavior in tests.*

- [X] T010 [US2] Update `CrawlerLoop` to pass configuration to `ScreenTracker` in `src/mobile_crawler/core/crawler_loop.py`
- [X] T011 [US2] Add integration test to verify threshold configuration affects deduplication results in `tests/integration/infrastructure/test_screen_repository.py`
- [X] T012 [US2] Update `ScreenTracker` to use `use_perceptual_hashing` flag to toggle logic in `src/mobile_crawler/domain/screen_tracker.py`

## Phase 5: Polish & Metrics
*Goal: Improve observability and verification.*

- [X] T013 Polish: Add detailed debug logging of hash distances in `ScreenTracker._find_similar_screen` at `src/mobile_crawler/domain/screen_tracker.py` (FR-007)
- [X] T014 Polish: Verify metric reporting in `ScreenRepository.count_unique_screens_for_run` at `src/mobile_crawler/infrastructure/screen_repository.py`
- [X] T015 Polish: Run manual verification script using Run #88 screenshots to confirm fix effectiveness (see `research_hashing.py`)

## Dependencies
1. T001
2. T002 -> T003
3. T003 -> T005, T006, T007
4. T004 (Tests) -> T005, T006, T007 (Implementation)
5. T007 -> T008
6. T005, T006, T007 -> T010, T011

## Parallel Execution Examples
- T005 (Hash Algo) and T008 (Repo Lookup) can be implemented in parallel.
- T013 (Logging) can be done anytime after T007.

## Implementation Strategy
We will strictly follow TDD:
1. Write tests (T004) that fail with current implementation (pHash).
2. Update Config (T002).
3. Implement `dHash` (T005) and logic (T007).
4. Verify tests pass.
