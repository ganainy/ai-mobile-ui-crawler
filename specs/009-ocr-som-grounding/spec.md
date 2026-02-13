# Feature Specification: OCR + Set-of-Mark Grounding

**Feature Branch**: `009-ocr-som-grounding`  
**Created**: 2026-01-12  
**Status**: Draft  
**Input**: User description: "sketch out a more detailed implementation plan for the OCR + Set-of-Mark approach"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Robust Text Interaction (Priority: P1)

The AI Agent needs to interact with text-based elements (buttons, links, input fields) with high spatial precision, eliminating "missed clicks" caused by potential VLM hallucination of coordinates.

**Why this priority**: Coordinates prediction is the #1 source of failure in VLM-based crawlers. Visual Grounding is critical for stability.

**Independent Test**:
- Create a screen with multiple small text buttons close together.
- Verify the AI can reliably click a specific one by name (e.g., "Tap 'Edit'") 10/10 times using the label system.

**Acceptance Scenarios**:

1. **Given** a screen with text "Login" and "Sign Up", **When** the AI decides to click "Login", **Then** it outputs a label targeting the "Login" text, and the system clicks the center of the "Login" bounding box.
2. **Given** a screen with dense text, **When** the system captures a screenshot, **Then** it overlays unique numeric tags on all detected text regions before sending to the AI.
3. **Given** the AI outputs a specific label ID, **When** the system executes the action, **Then** it uses the precise center coordinates of the corresponding OCR bounding box.

---

### User Story 2 - Hybrid Fallback for Non-Text Elements (Priority: P2)

The AI Agent needs to interact with icon-only buttons (non-text) which OCR will miss.

**Why this priority**: Apps have back buttons, home icons, and gear icons that have no text.

**Independent Test**:
- Load a screen with an icon-only button.
- Verify the AI can still click it using raw coordinate prediction or a spatial fallback if no label exists.

**Acceptance Scenarios**:

1. **Given** a screen with an icon (no text), **When** OCR finds no text at that location, **Then** the AI can still output generic coordinates (or the system handles it via a fallback mechanism) to click the icon.
   *(Note: The primary goal is Text Grounding, but we must not break Icon interaction. The AI should be instructed to use labels for text and coordinates for non-labeled items.)*

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST integrate a local OCR engine to detect text and bounding boxes on the current screenshot.
- **FR-002**: System MUST generate a "Labeled Screenshot" where detected text regions are overlaid with unique, clearly visible numeric markers (Set-of-Mark).
- **FR-003**: System MUST provide the VLM with the Labeled Screenshot instead of (or in addition to) the raw screenshot.
- **FR-004**: System MUST inject a prompt instruction explaining the label system (e.g., "To click text, provide the label ID").
- **FR-005**: System MUST map the VLM's selected numeric label back to the center coordinates of the detected bounding box for execution.
- **FR-006**: System MUST allow the VLM to fall back to raw (x, y) coordinates for elements that are not detected by OCR (e.g., icons).
- **FR-007**: System MUST perform OCR processing within a reasonable time window to maximize crawler speed.

### Key Entities

- **OCRResult**: List of `(text, bounding_box, confidence)`.
- **LabelMap**: Dictionary mapping `Label_ID` -> `Coordinates`.
- **MarkedScreenshot**: The image artifact with overlays.

### Edge Cases

- **Dense Text**: If text elements are too close, labels might overlap. The system should prioritize readability or merge regions.
- **No Text Detected**: If OCR finds nothing, the system should proceed with the raw screenshot/coordinate mode functionality seamlessly.
- **Misaligned OCR**: If OCR bounding boxes are slightly off, the center point might miss small buttons. Padding strategies should be considered in implementation.

### Assumptions

- The selected VLM is capable of understanding "Set-of-Mark" prompting strategies.
- OCR execution time is acceptable for the interactive loop.


## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Text-based element click accuracy increases to >99% (measured on a test harness of 50 text buttons).
- **SC-002**: VLM "retries" due to missed clicks on text elements are reduced to near zero.
- **SC-003**: OCR processing overhead is less than 2 seconds per step on standard hardware.
- **SC-004**: The system successfully clicks both text (via label) and icons (via coordinates) in a single mixed-UI session.
