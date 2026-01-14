# Feature Specification: UI Monitor Improvements

**Feature Branch**: `017-ui-monitor-improvements`  
**Created**: 2026-01-14  
**Status**: Draft  
**Input**: User description: "Add JSON parser for expanding/minimizing fields in prompt data and AI response, fix empty response and parsed actions in UI, fix action status showing as failed incorrectly, fix duplicate actions in AI monitor, add screenshot viewer toggle between annotated and OCR screenshots"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Expandable JSON Fields in Prompt Data and Response (Priority: P1)

When reviewing AI interactions in the Step Detail view, users need to inspect complex JSON data in the Prompt Data and AI Response sections. Currently, JSON is displayed as formatted text, making it difficult to navigate large nested structures like `ocr_grounding` arrays with many elements.

**Why this priority**: This is a core usability improvement that directly impacts the debugging workflow. Users cannot efficiently navigate large JSON structures in prompt data (screen dimensions, exploration progress, OCR grounding arrays) or AI responses.

**Independent Test**: Can be fully tested by opening a Step Detail tab and interacting with collapsible JSON tree controls. Delivers immediate value for debugging AI interactions.

**Acceptance Scenarios**:

1. **Given** a step detail tab is open with JSON prompt data, **When** the user views the Prompt Data panel, **Then** JSON fields are displayed in an expandable/collapsible tree view
2. **Given** JSON data contains nested objects or arrays, **When** the user clicks an expand icon, **Then** the nested content is revealed; clicking again collapses it
3. **Given** a JSON field like `ocr_grounding` contains a large array, **When** the UI renders it, **Then** the array is initially collapsed showing "[N items]" summary
4. **Given** a JSON response from AI, **When** displayed in the Response panel, **Then** JSON content is parsed and shown with expand/collapse controls

---

### User Story 2 - Fix Empty Response and Parsed Actions Display (Priority: P1)

When viewing Step Details, the Response and Parsed Actions panels show empty even when the AI has returned valid responses with actions. The data exists but is not being extracted and displayed correctly.

**Why this priority**: This is a critical bug that prevents users from seeing AI responses and understanding what actions were parsed, making debugging impossible.

**Independent Test**: Can be fully tested by running a crawl, viewing the AI Monitor, clicking "Show Details" on a completed step, and verifying Response and Parsed Actions panels show content.

**Acceptance Scenarios**:

1. **Given** an AI response contains valid action data, **When** the user views the step detail, **Then** the Response panel shows the complete AI response text
2. **Given** an AI response contains parsed actions, **When** the step detail is displayed, **Then** the Parsed Actions panel lists all actions with their properties (action type, description, target, reasoning)
3. **Given** an AI response was successfully received, **When** viewing the AI Monitor list, **Then** the response preview shows a meaningful summary (not empty)

---

### User Story 3 - Fix Incorrect Failed Status on Actions (Priority: P2)

Actions that execute successfully are being marked as "Failed" (red X) in the AI Monitor. The success/failure status is not being correctly determined from the response or action execution results.

**Why this priority**: This causes confusion when reviewing crawl history, as users cannot trust the status indicators to identify actual failures.

**Independent Test**: Can be tested by running a crawl with successful actions and verifying the status indicators show green checkmarks for successful steps.

**Acceptance Scenarios**:

1. **Given** an action executes successfully on the device, **When** the step is displayed in AI Monitor, **Then** the status indicator shows success (green checkmark)
2. **Given** an AI response is received without errors, **When** the response is processed, **Then** the step success field is correctly set based on action execution outcome
3. **Given** a step contains multiple actions where all succeed, **When** viewing the step in AI Monitor, **Then** the overall step status shows success

---

### User Story 4 - Fix Duplicate Actions in AI Monitor (Priority: P2)

Each action/step appears twice in the AI Monitor list. This occurs because both the request and response are creating separate list entries, or the update logic is adding a new item instead of updating the existing one.

**Why this priority**: This clutters the AI Monitor and makes it difficult to track the actual number of steps in the crawl.

**Independent Test**: Can be tested by running a crawl and counting the number of items in the AI Monitor list versus the actual step count.

**Acceptance Scenarios**:

1. **Given** a crawl runs with N steps, **When** viewing the AI Monitor, **Then** exactly N items appear in the list (not 2N)
2. **Given** an AI request is sent and a response is received, **When** viewing the AI Monitor, **Then** a single item represents the complete request/response cycle
3. **Given** a pending request exists in the AI Monitor, **When** the response arrives, **Then** the existing item is updated in-place (not a new item added)

---

### User Story 5 - Screenshot Viewer Toggle (Annotated vs OCR) (Priority: P3)

In the Step Detail view's Screenshot panel, users need to switch between viewing the annotated screenshot (with bounding box overlays) and the OCR screenshot (with text element labels/highlights). Currently, only the annotated view is available.

**Why this priority**: While useful for debugging OCR issues, this is an enhancement rather than a bug fix. Users can still see the annotated screenshot with action overlays.

**Independent Test**: Can be tested by opening a Step Detail tab and using toggle controls to switch between screenshot views.

**Acceptance Scenarios**:

1. **Given** a step detail tab is open, **When** the user views the Screenshot panel, **Then** toggle buttons/tabs are available to switch between "Annotated" and "OCR" views
2. **Given** the "Annotated" view is selected, **When** displayed, **Then** the screenshot shows action bounding boxes drawn by `draw_overlays_on_pixmap`
3. **Given** the "OCR" view is selected, **When** displayed, **Then** the screenshot shows OCR element labels/boxes from the grounding data
4. **Given** OCR grounding data is available, **When** rendering OCR view, **Then** each detected text element has a numbered label matching the grounding array

---

### Edge Cases

- What happens when prompt data is not valid JSON? Display as plain text with no expand/collapse controls.
- What happens when there's no screenshot in the prompt data? Show "No screenshot available" placeholder for both views.
- What happens when there are no parsed actions? Show "No parsed actions available" message in Parsed Actions panel.
- What happens when OCR grounding data is empty? Show annotated view only with disabled/hidden OCR toggle.
- How does the system handle very large JSON structures (100+ nodes)? Use lazy loading/virtualization for deeply nested structures.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display JSON data in Prompt Data panel as an expandable/collapsible tree structure
- **FR-002**: System MUST display JSON data in Response panel as an expandable/collapsible tree structure when the response contains JSON
- **FR-003**: System MUST correctly extract and display the AI response text in the Response panel
- **FR-004**: System MUST correctly parse and display action details in the Parsed Actions panel from response data
- **FR-005**: System MUST accurately reflect action execution success/failure status in the AI Monitor list
- **FR-006**: System MUST display exactly one entry per step in the AI Monitor (update existing item when response arrives)
- **FR-007**: System MUST provide a toggle or tab control to switch between Annotated and OCR screenshot views
- **FR-008**: System MUST render OCR grounding labels on the screenshot when OCR view is selected

### Key Entities

- **AIInteractionItem**: Widget representing a single AI request/response cycle in the monitor list, with step number, status, timing, and preview data
- **StepDetailWidget**: Detailed view of a single step showing screenshot, prompt data, response, and parsed actions in a tabbed layout
- **OCR Grounding**: Array of detected text elements with label IDs, text content, and bounding coordinates

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can expand/collapse any JSON field in Prompt Data within 1 click
- **SC-002**: Response and Parsed Actions panels display content for 100% of steps with valid AI responses
- **SC-003**: Action success/failure status matches actual execution outcome for 100% of actions
- **SC-004**: AI Monitor displays exactly 1 item per crawl step (no duplicates)
- **SC-005**: Users can switch between Annotated and OCR screenshot views within 1 click

## Assumptions

- The Qt framework supports tree view widgets suitable for JSON display (QTreeView or custom implementation)
- OCR grounding data is available in the prompt data JSON under the `ocr_grounding` key
- The response data structure includes fields like `response`, `raw_response`, or `parsed_response` that contain the AI output
- Annotated screenshots are generated during `_add_list_item` using `draw_overlays_on_pixmap`
- The `_update_list_item` method in `AIMonitorPanel` is responsible for updating existing items when responses arrive
