# Feature Specification: Debug Overlay & Step-by-Step Mode

**Feature Branch**: `008-debug-overlay`  
**Created**: 2026-01-12  
**Status**: COMPLETED  
**Input**: User description: "I want to draw boxes on the coordinates as they return from the AI response on the screenshot that is shown in the UI so that I can see in the moment if the returned coordinates are correct or not, also I want a checkbox that enables step by step so that the crawler stops after each step until I press next step or something. Also I want the screenshot with boxes to be saved like we are saving the normal screenshots to the screenshots folder"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Coordinate Visualization on Screenshots (Priority: P1)

As a developer debugging the mobile crawler, I want to see visual overlays of the AI-predicted bounding boxes drawn on the screenshot displayed in the UI, so that I can immediately verify whether the AI is targeting the correct UI elements before or after actions are executed.

**Why this priority**: This is critical for debugging coordinate accuracy issues. Without visual feedback, developers must mentally calculate whether AI-returned coordinates are correct, which is error-prone and time-consuming. This directly addresses the core need to validate AI targeting in real-time.

**Independent Test**: Can be fully tested by running a crawl, observing the screenshot panel, and verifying that colored boxes appear on the screenshot matching the AI-predicted target areas. Delivers immediate visual feedback value without requiring step-by-step mode.

**Acceptance Scenarios**:

1. **Given** the crawler is running and an AI response is received, **When** the screenshot is displayed in the AI Monitor Panel, **Then** the target bounding box from each action should be drawn as a visible colored rectangle on the screenshot.

2. **Given** multiple actions are returned in a single AI response, **When** the screenshot is displayed, **Then** each action's bounding box should be drawn with a distinct color or label to differentiate them.

3. **Given** the AI returns coordinates for a click action, **When** the overlay is drawn, **Then** the center point of the bounding box should also be marked (e.g., with a crosshair or dot) to show exactly where the tap will occur.

4. **Given** the coordinates from AI are in the scaled-down image space, **When** displaying overlays, **Then** the boxes must be drawn using the same scaled coordinates (since the displayed image is also scaled down from the original).

---

### User Story 2 - Step-by-Step Debugging Mode (Priority: P2)

As a developer debugging the mobile crawler, I want to enable a "step-by-step" mode via a checkbox so that the crawler pauses after each step and waits for me to press a "Next Step" button before continuing, allowing me to inspect the current state and AI decisions before the next action is taken.

**Why this priority**: While coordinate visualization (P1) provides passive debugging, step-by-step mode provides active debugging control. It allows developers to inspect AI reasoning, verify coordinates, and catch issues before they cascade into further steps. It depends on having P1 working to be most useful.

**Independent Test**: Can be fully tested by enabling the checkbox, starting a crawl, and verifying the crawler pauses after step 1 until the "Next Step" button is clicked. Delivers interactive debugging capability.

**Acceptance Scenarios**:

1. **Given** step-by-step mode is disabled (checkbox unchecked), **When** a crawl is started, **Then** the crawler should run continuously as normal.

2. **Given** step-by-step mode is enabled (checkbox checked), **When** a crawl is started and the first step completes, **Then** the crawler should pause and display the current step's screenshot with coordinate overlays, AI response, and enable a "Next Step" button.

3. **Given** the crawler is paused in step-by-step mode, **When** the "Next Step" button is clicked, **Then** the crawler should execute the next step and pause again after it completes.

4. **Given** the crawler is paused in step-by-step mode, **When** the "Stop" button is clicked, **Then** the crawl should be terminated gracefully.

5. **Given** step-by-step mode is enabled during a running crawl (toggle mid-run), **When** the current step completes, **Then** the crawler should pause before the next step.

---

### User Story 3 - Action Index Labels on Overlay (Priority: P3)

As a developer, I want each bounding box overlay to display the action index number (1, 2, 3...) so that I can correlate the visual overlay with the action list in the AI response panel.

**Why this priority**: This is an enhancement to P1 that improves usability when multiple actions are returned. It provides better correlation between visual and textual information but is not essential for core debugging functionality.

**Independent Test**: Can be fully tested by triggering an AI response with 2+ actions and verifying that each box on the screenshot shows a numbered label matching the action order.

**Acceptance Scenarios**:

1. **Given** the AI returns three actions with bounding boxes, **When** the overlay is rendered, **Then** each box should display a label "1", "2", "3" in the corner showing the action execution order.

---

### User Story 4 - Save Annotated Screenshots (Priority: P1)

As a developer debugging the mobile crawler, I want the annotated screenshots (with bounding box overlays drawn on them) to be automatically saved to the screenshots folder alongside the original screenshots, so that I can review the AI's coordinate predictions after a run completes and share them with others for analysis.

**Why this priority**: This is equally critical as the visual overlay feature (User Story 1). While real-time viewing helps during a live session, saved annotated screenshots enable post-run analysis, comparison across runs, and sharing with team members who weren't present during the crawl. It creates a permanent debugging record.

**Independent Test**: Can be fully tested by running a crawl, navigating to the screenshots folder, and verifying that for each step there are both the original screenshot and an annotated version with bounding boxes saved.

**Acceptance Scenarios**:

1. **Given** a screenshot is captured and an AI response with actions is received, **When** the step completes, **Then** an annotated version of the screenshot with all bounding box overlays should be saved to the screenshots folder.

2. **Given** the original screenshot is saved as `step_001.png`, **When** the annotated version is saved, **Then** it should be saved with a distinct filename such as `step_001_annotated.png` in the same folder.

3. **Given** the AI returns multiple actions with bounding boxes, **When** the annotated screenshot is saved, **Then** all action overlays, center points, and action index labels should be included in the saved image.

4. **Given** the annotated screenshot is saved, **When** it is opened in an image viewer, **Then** the overlay quality should be preserved (no compression artifacts on the drawn boxes).

---

### Edge Cases

- What happens when the AI returns invalid or out-of-bounds coordinates?
  - The overlay should still draw the box (clipped to image bounds) and display in a distinct "error" color (e.g., red with dashed border).
  
- How does the system handle coordinates at (0,0) or at exact image boundaries?
  - Coordinates should be drawn correctly without visual artifacts; boundary boxes should still be visible.

- What happens if step-by-step mode is toggled while the crawler is paused?
  - The crawler should remain paused; toggling to "off" should not auto-resume (user must explicitly click Next Step or Resume).

- What happens if the user closes the application while paused in step-by-step mode?
  - The crawl should be gracefully stopped and recorded as interrupted.

- What happens if saving the annotated screenshot fails (e.g., disk full, permissions)?
  - The system should log a warning but continue the crawl; the original screenshot is already saved separately, so no critical data is lost.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST draw bounding box rectangles on the screenshot image for each action's `target_bounding_box` coordinates when an AI response is received.

- **FR-002**: System MUST use coordinates from the AI response directly (scaled image coordinates) when drawing on the displayed screenshot (which is also scaled).

- **FR-003**: System MUST draw a center point indicator (dot or crosshair) within each bounding box to show precise tap location.

- **FR-004**: System MUST use distinct colors for each action's bounding box when multiple actions are returned (e.g., action 1: green, action 2: blue, action 3: orange).

- **FR-005**: System MUST provide a checkbox in the Control Panel labeled "Step-by-Step Mode" that enables/disables stepping behavior.

- **FR-006**: System MUST pause the crawler loop after each step completes when step-by-step mode is enabled, entering a "PAUSED_STEP" state.

- **FR-007**: System MUST provide a "Next Step" button that becomes enabled when the crawler is paused in step-by-step mode.

- **FR-008**: System MUST resume the crawler for exactly one step when "Next Step" is clicked, then pause again.

- **FR-009**: System MUST allow toggling step-by-step mode on/off during a running crawl (changes take effect after current step).

- **FR-010**: System MUST maintain all existing pause/resume/stop functionality when step-by-step mode is enabled.

- **FR-011**: System MUST display the coordinate overlay BEFORE executing the action (so developer can verify before execution in step-by-step mode).

- **FR-012**: System MUST save an annotated version of each screenshot (with bounding box overlays drawn) to the same screenshots folder as the original screenshots.

- **FR-013**: System MUST use a distinct filename convention for annotated screenshots (e.g., `step_XXX_annotated.png`) to differentiate them from original screenshots.

### Key Entities

- **CoordinateOverlay**: Visual representation of bounding box coordinates drawn on a screenshot. Contains: bounding_box (x1,y1,x2,y2), color, action_index, is_valid.

- **StepDebugState**: Captures the state needed for debugging a step. Contains: step_number, screenshot with overlays, AI actions list, current pause status.

- **AnnotatedScreenshot**: A screenshot image with coordinate overlays rendered onto it. Contains: original_path, annotated_path, step_number, overlays_applied.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can visually verify AI coordinate accuracy within 2 seconds of viewing the screenshot overlay (no mental calculation needed).

- **SC-002**: 100% of AI-returned bounding boxes are visually represented on the screenshot within the same UI refresh cycle.

- **SC-003**: Step-by-step mode allows developers to pause and inspect each step, reducing debugging time for coordinate issues by at least 50% compared to reviewing logs after a full run.

- **SC-004**: Developers can complete a 10-step crawl in step-by-step mode with full inspection capability, clicking "Next Step" to advance each stage.

- **SC-005**: Toggle of step-by-step mode during a run takes effect within one step cycle (no restart required).

- **SC-006**: 100% of steps with AI actions have both original and annotated screenshots saved to the screenshots folder.

- **SC-007**: Developers can review annotated screenshots after a run to analyze coordinate accuracy without needing to re-run the crawl.
