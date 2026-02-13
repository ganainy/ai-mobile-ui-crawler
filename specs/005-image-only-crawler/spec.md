# Feature Specification: Image-Only UI Crawler

**Feature Branch**: `005-image-only-crawler`  
**Created**: 2026-01-11  
**Status**: Draft  
**Input**: User description: "this is a IMAGE only ui crawler, we dont need any code to do with XML or OCR"

## User Scenarios & Testing

### User Story 1 - Pure Visual Navigation (Priority: P1)

The crawler navigates and interacts with the mobile application using *only* visual information derived from screenshots. It explicitly ignores any underlying view hierarchy (XML) and avoids using Optical Character Recognition (OCR) tools for element detection or text reading.

**Why this priority**: This is the core definition of the feature. Removing XML and OCR dependencies simplifies the architecture, improves reliance on modern VLM capabilities, and aligns with the "Image Only" directive.

**Independent Test**: Configure the crawler to run against a sample app (e.g., the sign-in scenario). Verify that the crawler effectively navigates screens and interacts with elements without fetching the UI source (XML) or invoking OCR functions.

**Acceptance Scenarios**:

1. **Given** the crawler is navigating a screen, **When** it needs to find an interactive element (e.g., a button), **Then** it sends *only* the screenshot to the AI/VLM and receives coordinates, without attempting to dump the window hierarchy.
2. **Given** a text-heavy screen, **When** the crawler assesses the state, **Then** it relies on the VLM's visual understanding of the text, not on a separate OCR text extraction process.
3. **Given** the crawler performs an action, **When** the action is executed, **Then** the logs confirm no XML parsing or OCR-related log entries were generated.

---

### User Story 2 - Legacy Code Cleanup (Priority: P2)

The codebase is refactored to remove logic, imports, and dependencies related to structural view parsing (XML) and optical character recognition (OCR).

**Why this priority**: Ensures the codebase reflects the "Image Only" architecture and prevents accidental usage of legacy methods.

**Independent Test**: Static analysis of the `mobile_crawler` source code.

**Acceptance Scenarios**:

1. **Given** the project codebase, **When** searched for structural UI methods (e.g., retrieving page source), **Then** no active occurrences are found in the crawler logic.
2. **Given** the project codebase, **When** searched for OCR dependencies, **Then** these are removed or unused in the crawler flow.

## Edge Cases

- **Visually Ambiguous Screens**: If a screen has identical buttons with no text, the system must rely on spatial context or guess, as it cannot read the underlying view IDs.
- **Hidden Elements**: Elements that exist in the view hierarchy but are not visible in the screenshot (e.g. requires scroll, or invisible) are completely inaccessible to the crawler.
- **Slow Transitions**: If the screenshot is taken during a transition (blur/empty), the crawler may fail to identify targets. Visual stability checks are implied.

## Assumptions

- A Visual Language Model (VLM) or similar AI capability is available to process screenshots.
- The target application does not require accessibility service interaction (which would require XML/Tree access) for its core functionality.

## Requirements

### Functional Requirements

- **FR-001**: System MUST determine the current application state solely from screenshots captured from the device.
- **FR-002**: System MUST NOT access the underlying application view structure (e.g., view hierarchy, accessibility tree).
- **FR-003**: System MUST NOT use programmatic text extraction (OCR) subsystems to interpret text.
- **FR-004**: System MUST rely on the AI/VLM to interpret UI elements and provide interaction coordinates based on the screenshot.
- **FR-005**: System MUST execute actions (Tap, Scroll, Type) using coordinates or visual references provided by the VLM.
- **FR-006**: System MUST persist the "Image Only" constraint across all defined scenarios.

### Key Entities

- **Screenshot**: The sole input data representing the UI state at any timestamp.
- **Visual Action**: An interaction directive (Type, Coordinates) derived purely from visual analysis.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Crawler successfully completes the 'Sign Up -> Login' flow using 0 XML hierarchy requests.
- **SC-002**: Crawler successfully completes the flow using 0 calls to dedicated OCR libraries.
- **SC-003**: 100% of interactive elements are identified via visual coordinates provided by the VLM.
- **SC-004**: Run export (JSON) contains only screenshot-derived inputs/outputs, with no XML dumps.
