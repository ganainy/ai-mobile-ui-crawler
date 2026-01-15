# Feature Specification: Enhanced Report Generation

**Feature Branch**: `022-enhanced-report-gen`  
**Created**: 2026-01-15  
**Status**: Draft  
**Input**: User description: "generate report button currently doesnt do match, i want to expand the report to have as much info as possible since i will rely on it to write my master thesis, also it should use the mobsf json report and the ,pcap file to enrich the infromation collected too"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Comprehensive Crawl Report (Priority: P1)

As a researcher writing a master thesis, I want to generate a detailed report for a specific crawl session that aggregates run details, security findings, and network traffic so that I can easily analyze the results in one place.

**Why this priority**: this is the core value requested by the user to support their thesis work.

**Independent Test**: Can be tested by running a crawl, clicking "Generate Report", and verifying the output file contains sections for Run Summary, Step-by-Step Actions, MobSF Analysis, and Network Traffic.

**Acceptance Scenarios**:

1. **Given** a completed crawl session with MobSF scan and PCAP capture, **When** I click the "Generate Report" button, **Then** a comprehensive HTML report is generated and saved to the session directory.
2. **Given** a session with missing MobSF or PCAP data, **When** I generate the report, **Then** the report is still generated with the available data (steps and screenshots) and placeholders/warnings for missing sections.

---

### User Story 2 - Context-Enriched Data View (Priority: P2)

As a user, I want the report to correlate the security findings and network requests with the specific crawl actions (timeline) so that I can understand what user action triggered a specific network request or security issue.

**Why this priority**: Adds significant value to the report by providing context, not just raw data.

**Independent Test**: Inspect the generated report and verify that network requests are grouped or ordered by the crawl step timestamp they occurred in.

**Acceptance Scenarios**:

1. **Given** a generated report, **When** I view the "Timeline" or "Steps" section, **Then** I can see the screenshots and actions side-by-side with relevant network activity detected at that time.

---

### Edge Cases

- What happens when the PCAP file is extremely large?
    - The system should probably summarize or truncate the detailed packet view to avoid memory issues/unreadable reports.
- What happens if the MobSF report JSON structure changes?
    - The parsing logic should gracefully handle missing keys.
- What happens if the run crashed midway?
    - The report should indicate the "FAILED" status and show data up to the crash point.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a "Generate Report" functionality in the UI for a selected session.
- **FR-002**: The generated report MUST be in a human-readable HTML format, styled to be printer-friendly for PDF export.
- **FR-003**: The report MUST include a "Run Summary" section (Start/End time, Duration, Device, App Package, Status).
- **FR-004**: The report MUST parse and include high-level security findings from the MobSF JSON report (e.g., High/Medium/Low vulnerabilities count, top security issues).
- **FR-005**: The report MUST parse the PCAP file to extract HTTP/HTTPS requests and DNS queries.
- **FR-006**: The report MUST display a sequential timeline of the crawl, including:
    - Screenshot of the state.
    - Action taken (Click, Type, etc.).
    - Associated Network requests (matched by timestamp).
- **FR-007**: The system MUST save the generated report in the session's specific folder.
- **FR-008**: The report generation MUST NOT fail if optional data (MobSF/PCAP) is missing; it should just omit those sections.
- **FR-009**: The system MUST generate a matching structured JSON report (`report.json`) containing the aggregated run data, steps, linked network requests, and security findings for machine analysis.

## Clarifications

### Session 2026-01-15

- Q: What should be the structure of the JSON report? → A: **Structured Aggregate**: A single JSON file containing the Run Summary, ordered Steps, linked Network Requests, and Security Findings (mirrors internal data model).

### Key Entities *(include if feature involves data)*

- **Run Report**: The aggregate object containing all run info.
- **Step Record**: Timestamp, Action, Screenshot Path.
- **Traffic Record**: Timestamp, Method, URL, Status Code (derived from PCAP).
- **Security Finding**: Severity, Description, File/Evidence (derived from MobSF).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: "Generate Report" action completes within 30 seconds for a typical 10-minute crawl.
- **SC-002**: Generated report contains at least 3 distinct sections: Execution Log, Security Analysis, Network Analysis.
- **SC-003**: 100% of captured HTTP requests (up to a limit) are listed in the report.
- **SC-004**: Users can view the final status and all performed steps in the report.
