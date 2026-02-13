# Research: UI Monitor Improvements

**Feature**: 017-ui-monitor-improvements  
**Date**: 2026-01-14

## Overview

This document analyzes the root causes of the reported bugs and documents design decisions for the enhancements.

---

## Issue 1: Empty Response and Parsed Actions (P1)

### Root Cause Analysis

**Observation**: The Response panel shows empty text, and Parsed Actions shows "No parsed actions available".

**Investigation**:

1. **Data Flow Trace**:
   - `CrawlerLoop._execute_step()` emits `on_ai_response_received` (line 543) with limited data:
     ```python
     self._emit_event("on_ai_response_received", run_id, step_number, {
         "actions_count": len(ai_response.actions),
         "signup_completed": ai_response.signup_completed,
         "latency_ms": ai_response.latency_ms
     })
     ```
   - The `AIInteractionService` also emits `on_ai_response_received` (line 264) with full response data:
     ```python
     self.event_listener.on_ai_response_received(run_id, step_number, response_data)
     ```
     where `response_data` includes `parsed_response`, `raw_response`, etc.

2. **Signal Connection in `main_window.py` (line 302)**:
   ```python
   self.signal_adapter.ai_response_received.connect(self._on_ai_response_received)
   ```
   - But `ai_request_sent` is connected directly to `add_request` (line 301):
   ```python
   self.signal_adapter.ai_request_sent.connect(self.ai_monitor_panel.add_request)
   ```

3. **The Problem**:
   - The **AI Service** emits the full response data, but the **CrawlerLoop** also emits a separate `on_ai_response_received` with minimal data.
   - Both events hit the same signal, but the CrawlerLoop's version (with less data) may be overwriting or confusing the UI.
   - In `_add_list_item()` (line 579-587), parsing looks for `parsed_response` key but it gets the CrawlerLoop's minimal response dict.

4. **Data Extraction Issues in `_add_list_item()`**:
   ```python
   # Parse actions if available
   parsed_actions = []
   if "parsed_response" in response_data:
       try:
           parsed = json.loads(response_data["parsed_response"])
           if "actions" in parsed:
               parsed_actions = parsed["actions"]
       except (json.JSONDecodeError, KeyError):
           pass
   ```
   - The response_data from CrawlerLoop doesn't have `parsed_response` - only `actions_count`, `signup_completed`, `latency_ms`.
   - The response_data from AIInteractionService has the full data but may arrive AFTER the CrawlerLoop version.

### Solution

**Decision**: Rely ONLY on the `AIInteractionService` event which contains full response data. The `CrawlerLoop` event provides minimal summary data intended for statistics.

**Implementation**:
1. In `main_window.py`, connect `ai_response_received` to a handler that:
   - Checks if `parsed_response` or `raw_response` keys exist (indicates full data from AIInteractionService)
   - Only forwards to `ai_monitor_panel.add_response()` if full data is present
2. Alternatively, add a new signal/flag to distinguish the two event sources.

**Rationale**: The AIInteractionService has access to the complete response data including the raw response text and parsed actions. The CrawlerLoop only has the action count.

---

## Issue 2: Incorrect Failed Status (P2)

### Root Cause Analysis

**Observation**: Actions show as "Failed" (red X) even when executed successfully.

**Investigation**:

1. **Success Determination in `add_response()`** (line 526):
   ```python
   interaction["success"] = response_data.get("success", False)
   ```

2. **The Problem**:
   - Neither the CrawlerLoop nor AIInteractionService explicitly sets `success: true` in the response_data.
   - The CrawlerLoop's response_data is: `{"actions_count": N, "signup_completed": bool, "latency_ms": float}` - NO success field!
   - Default is `False`, so everything shows as failed.

3. **What Should Determine Success?**
   - An AI response is "successful" if:
     - The AI returned actions without error
     - The response was parseable
   - Action execution success is tracked separately via `on_action_executed` events.

### Solution

**Decision**: Determine success based on:
1. Presence of actions (`actions_count > 0`)
2. Absence of `error_message` field

**Implementation**:
```python
# In add_response() or _add_list_item()
success = (
    response_data.get("actions_count", 0) > 0 or 
    "actions" in response_data or
    "parsed_response" in response_data
) and not response_data.get("error_message")
```

**Rationale**: An AI response is successful if it parsed correctly and returned actionable data.

---

## Issue 3: Duplicate Actions in AI Monitor (P2)

### Root Cause Analysis

**Observation**: Each step appears twice in the AI Monitor list.

**Investigation**:

1. **Event Flow**:
   - `add_request()` creates a pending item and calls `_add_list_item(pending=True)` - adds item to list
   - `add_response()` updates the interaction and calls `_update_list_item()` which:
     - Removes the old item (line 657-659)
     - Calls `_add_list_item()` again - adds NEW item to list

2. **The Problem in `_update_list_item()`** (lines 655-662):
   ```python
   # Remove old item
   list_item = interaction["_list_item"]
   row = self.interactions_list.row(list_item)
   if row >= 0:
       self.interactions_list.takeItem(row)
   
   # Add updated item
   self._add_list_item(step_number)  # <-- Creates brand new item!
   ```
   - This creates a NEW widget, which is fine, but the DOUBLE appearance suggests either:
     - The remove is failing (row is -1, so nothing is removed)
     - OR both `add_response()` from AIInteractionService AND from CrawlerLoop are triggering

3. **Likely Cause**: BOTH sources of `on_ai_response_received` are triggering `add_response()`:
   - First from AIInteractionService with full data
   - Second from CrawlerLoop with summary data
   - This calls `_update_list_item()` twice for the same step!

### Solution

**Decision**: 
1. Prevent CrawlerLoop's summary event from triggering UI updates for the AI Monitor
2. OR deduplicate by checking if update already happened

**Implementation**:
- Option A: In `main_window.py._on_ai_response_received()`, filter out minimal responses
- Option B: In `add_response()`, check if already updated: if interaction already has full response_data, ignore subsequent calls

**Rationale**: Option B is more robust as it handles both current issues and future edge cases.

---

## Issue 4: JSON Expand/Collapse (P1 Enhancement)

### Design Decision

**Question**: What Qt widget should be used for collapsible JSON display?

**Options Evaluated**:

| Option | Pros | Cons |
|--------|------|------|
| QTreeView + QStandardItemModel | Native tree widget, efficient for large data | Requires more setup code |
| QTreeWidget | Simpler API, built-in item manipulation | Less efficient for very large trees |
| Custom collapsible labels | Maximum control | Reinventing the wheel |
| Third-party JSON viewer | Ready-made | External dependency |

**Decision**: Use **QTreeWidget** for simplicity. It handles the expected data sizes (< 1000 nodes) efficiently.

**Implementation Approach**:
1. Create `JsonTreeWidget(QTreeWidget)` class in `json_tree_widget.py`
2. Accept a Python dict/list and recursively build tree items
3. Initially collapse all items except the root level
4. Show value previews for collapsed items: `"ocr_grounding": [15 items]`

**Rationale**: QTreeWidget balances simplicity with performance for our use case.

---

## Issue 5: Screenshot Toggle (Annotated vs OCR) (P3)

### Design Decision

**Question**: How should the screenshot toggle UI be implemented?

**Options Evaluated**:

| Option | Pros | Cons |
|--------|------|------|
| Tab widget | Clear visual separation | Takes more vertical space |
| Radio buttons | Familiar toggle pattern | May look dated |
| Segmented button | Modern, compact | Less common in Qt |

**Decision**: Use **Radio buttons** (QRadioButton in QButtonGroup) for familiarity and Qt native support.

**Implementation Approach**:
1. Add radio buttons above the screenshot label: "Annotated" (default) | "OCR"
2. Store both pixmaps (annotated and OCR-rendered) in the widget
3. On toggle, swap the displayed pixmap
4. OCR rendering: Use existing `draw_overlays_on_pixmap()` pattern but for OCR elements

**Data Requirements**:
- The OCR grounding data is already in the prompt JSON under `ocr_grounding` key
- Each element has: `label`, `text`, `bounds` [x1, y1, x2, y2]

**Rationale**: Radio buttons are the most familiar toggle pattern for users.

---

## Summary of Decisions

| Issue | Decision | Rationale |
|-------|----------|-----------|
| Empty Response | Use AIInteractionService data only | Contains full response data |
| Failed Status | Base success on actions_count > 0 and no error | Matches actual success criteria |
| Duplicates | Skip update if response_data already has full data | Prevents double processing |
| JSON Tree | QTreeWidget with recursive builder | Simple and efficient enough |
| Screenshot Toggle | Radio buttons with lazy rendering | Familiar UX pattern |

---

## Alternatives Rejected

1. **Separate signals for AI service vs CrawlerLoop responses**: Too invasive, requires changes across multiple modules
2. **JSON viewer as external dependency**: Adds maintenance burden for simple feature
3. **Tab widget for screenshot views**: Wastes vertical space in an already dense layout
