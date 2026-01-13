# Feature Specification: Organize Session Artifacts

**Feature Branch**: `011-organize-session-artifacts`  
**Created**: 2026-01-13  
**Status**: Draft  
**Input**: User description: "the db files and screenshots and json of the run and mobsf and pdf report for the same sessions are scattered in multiple places i want to group them in one place the when i click the open folder button the ui it opens and i see them all organized in folders"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Centralized Session Folder Access (Priority: P1)

As a user, I want to click a single "Open Folder" button in the Run History UI to access all artifacts related to a specific crawl session, so I don't have to search through multiple directories.

**Why this priority**: Core request. Resolves the main pain point of scattered files.

**Independent Test**: Start a new crawl, wait for it to finish, go to Run History, click "Open Folder", and verify a file explorer window opens to a directory containing that session's artifacts (screenshots, reports, etc.).

**Acceptance Scenarios**:

1. **Given** a completed crawl session, **When** I click "Open Folder" for that session in the Run History view, **Then** the local file explorer opens to the session's root directory.
2. **Given** I am browsing a session's root directory, **Then** I see subfolders for `screenshots`, `reports` (MobSF/PDF), and `data` (JSON/DB files).

---

### User Story 2 - Automated Artifact Grouping (Priority: P1)

As a crawler, I want to automatically save all generated artifacts (screenshots, logs, reports) into a pre-defined session-specific folder structure during the run, so that data is organized from the start.

**Why this priority**: Critical for data integrity and organization. Without this, Story 1 cannot be fulfilled reliably.

**Independent Test**: Trigger a crawl and check the file system in real-time to ensure files are being created in the designated `session_ID` subfolders rather than global default locations.

**Acceptance Scenarios**:

1. **Given** a new crawl is started, **When** a screenshot is captured, **Then** it is saved inside the session's `screenshots` subfolder.
2. **Given** a run is finalised, **When** the MobSF report is generated, **Then** it is saved inside the session's `reports` subfolder.

---

### User Story 3 - Run Export Consolidation (Priority: P2)

As a user, I want the session's JSON export and any database snippets used for that run to be stored alongside the media and reports, so that the session is truly portable and self-contained.

**Why this priority**: Ensures that technical data is also organized, matching the user's request for "db files" and "json of the run".

**Independent Test**: Complete a run and verify that the `.json` export and any relevant `.db` files are present in the session's `data` or root folder.

**Acceptance Scenarios**:

1. **Given** a run export is triggered, **When** the JSON file is generated, **Then** it is placed in the session's unified folder.

---

### Edge Cases

- **What happens when a run is interrupted?** The session folder should still exist with all artifacts captured up to the point of failure.
- **How does system handle duplicate session IDs?** Session IDs should include timestamps or UUIDs to ensure unique folder names.
- **What if the MobSF report generation fails?** The "Open Folder" button should still work, but the `reports` folder might be empty or missing that specific file.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create a unique root directory for each crawl session using the format `run_{ID}_{TIMESTAMP}`.
- **FR-002**: System MUST implement a standardized subfolder structure within each session directory:
    - `/screenshots`: For all captured and annotated images.
    - `/reports`: For MobSF JSON reports and PDF exports.
    - `/data`: For the run's JSON export and any session-specific database files.
- **FR-003**: The UI's "Open Folder" action MUST resolve the path to the specific session directory and open it using the OS-native file explorer.
- **FR-004**: System MUST update the internal session database to store the absolute or relative path to this unified session folder.
- **FR-005**: All crawler components (ScreenshotManager, ReportGenerator, ExportManager) MUST be updated to use the dynamic session-specific path instead of static defaults.

### Key Entities *(include if feature involves data)*

- **Session Folder**: A physical directory representing a single run, containing all related assets.
- **Session Metadata**: Database records linking a Run ID to its high-level folder path.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of artifacts (screenshots, JSON, reports) for a new run are contained within the unified session directory.
- **SC-002**: "Open Folder" button successfully opens the correct directory 100% of the time for sessions started after this feature is implemented.
- **SC-003**: Users can locate any specific artifact for a run in 3 clicks or fewer from the session root.
