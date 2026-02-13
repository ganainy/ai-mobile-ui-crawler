---
description: "Task list for Enhanced Report Generation"
---

# Tasks: Enhanced Report Generation

**Input**: Design documents from `/specs/022-enhanced-report-gen/`
**Prerequisites**: plan.md, spec.md, research.md, contracts/

**Tests**: Tests are included as requested by the test-first principle in the Constitution.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create reporting package structure `src/mobile_crawler/reporting/` and subdirectories
- [x] T002 [P] Install `jinja2` and `dpkt` dependencies and update `requirements.txt` (if applicable)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core contracts and parsers that MUST be complete before report generation logic

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Create `src/mobile_crawler/reporting/contracts.py` with defined interfaces and data classes
- [x] T004 [P] Implement `DpktPcapParser` in `src/mobile_crawler/reporting/parsers/pcap_parser.py`
- [x] T005 [P] Implement `JsonMobSFParser` in `src/mobile_crawler/reporting/parsers/mobsf_parser.py`
- [x] T006 [P] Create unit tests for parsers in `tests/unit/reporting/test_parsers.py`

**Checkpoint**: Parsers can read files and return structured data objects.

---

## Phase 3: User Story 1 - Comprehensive Crawl Report (Priority: P1) 🎯 MVP

**Goal**: Generate a detailed HTML and JSON report that aggregates run details, security findings, and network traffic.

**Independent Test**: Run a mock crawl (or use existing artifacts), trigger report generation, and verify `report.html` and `report.json` are created with correct sections.

### Tests for User Story 1
- [x] T007 [P] [US1] Create test for `JinjaReportGenerator` in `tests/unit/reporting/test_generator.py`
- [x] T008 [P] [US1] Create test for `RunCorrelator` (basic pass-through) in `tests/unit/reporting/test_correlator.py`

### Implementation for User Story 1
- [x] T009 [P] [US1] Create Jinja2 template `src/mobile_crawler/reporting/templates/report.html.j2` with placeholders
- [x] T010 [P] [US1] Implement `JinjaReportGenerator` in `src/mobile_crawler/reporting/generator.py` (HTML generation)
- [x] T011 [US1] Extend `ReportGenerator` to support or add separate logic for JSON generation in `src/mobile_crawler/reporting/generator.py`
- [x] T012 [US1] Create a basic `RunCorrelator` in `src/mobile_crawler/reporting/correlator.py` (aggregates data without complex matching yet)
- [x] T013 [US1] Add "Generate Report" button to `CrawlControlPanel` in `src/mobile_crawler/ui/control_panel.py`
- [x] T014 [US1] Connect button to `_generate_report` method in `CrawlerLoop` or `MainWindow` to trigger generation logic

**Checkpoint**: Clicking "Generate Report" creates a valid HTML and JSON report with raw data lists.

---

## Phase 4: User Story 2 - Context-Enriched Data View (Priority: P2)

**Goal**: Correlate security findings and network requests with specific crawl steps (timeline).

**Independent Test**: Verify that the generated report's Timeline section shows network requests nested under the specific step where they occurred.

### Tests for User Story 2
- [x] T015 [P] [US2] Add test cases for time-window correlation in `tests/unit/reporting/test_correlator.py`

### Implementation for User Story 2
- [x] T016 [US2] Update `RunCorrelator` in `src/mobile_crawler/reporting/correlator.py` to implement time-window matching logic
- [x] T017 [US2] Update `RunReportData` construction to populate `EnrichedStep.network_requests`
- [x] T018 [US2] Update Jinja2 template `src/mobile_crawler/reporting/templates/report.html.j2` to render per-step network data in the timeline

**Checkpoint**: Report now shows "Network Requests" inside each Step card in the timeline.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T019 [P] Style the HTML report (CSS) for betting printing/PDF export
- [x] T020 [P] Handle large PCAP files (truncate or summarize) in `pcap_parser.py`
- [x] T021 [P] Ensure robust error handling if MobSF/PCAP files are missing (Test with missing files)
- [x] T022 Update documentation/README with reporting feature usage

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup.
- **US1 (Phase 3)**: Depends on Foundational.
- **US2 (Phase 4)**: Depends on US1 (iterates on the correlator and template).

### User Story Dependencies
- **US1**: Needs parsers (Foundational).
- **US2**: Needs the basic report structure from US1 to enhance it.

### Parallel Opportunities
- Parsers (T004, T005) can be built in parallel.
- Template design (T009) can happen while backend logic (T010, T012) is being written.
- UI button (T013) can be added while reporting logic is being built.
