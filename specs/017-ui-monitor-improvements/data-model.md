# Data Model: UI Monitor Improvements

**Feature**: 017-ui-monitor-improvements  
**Date**: 2026-01-14

## Overview

This document defines the data structures used in the UI Monitor improvements. Since this is a UI-only feature, these are Python class definitions and internal data structures, not database entities.

---

## Existing Data Structures (to be modified)

### AIInteractionItem Widget Data

**Location**: `src/mobile_crawler/ui/widgets/ai_monitor_panel.py`

```python
class AIInteractionItem(QWidget):
    """Widget representing a single AI request/response in the monitor list."""
    
    # Existing fields (no changes)
    step_number: int
    timestamp: datetime
    success: bool                    # MODIFIED: Logic for determining this changes
    latency_ms: Optional[float]
    tokens_in: Optional[int]
    tokens_out: Optional[int]
    error_message: Optional[str]
    prompt_preview: str
    response_preview: str
    full_prompt: str
    full_response: str
    parsed_actions: List[dict]
    pending: bool
```

### Interaction Data Dictionary

**Location**: Internal to `AIMonitorPanel._interactions`

```python
# Current structure for self._interactions[step_number]
interaction = {
    "run_id": int,
    "step_number": int,
    "timestamp": datetime,
    "request_data": dict,           # From on_ai_request_sent
    "response_data": dict,          # From on_ai_response_received (SHOULD contain full AI response)
    "success": Optional[bool],      # Determined from response_data
    "error_message": Optional[str],
    "_list_item": QListWidgetItem,  # Reference to list widget item
    "_item_widget": AIInteractionItem,  # Reference to custom widget
    "_response_updated": bool       # NEW: Flag to prevent duplicate updates
}
```

---

## New Data Structures

### JsonTreeWidget

**Location**: `src/mobile_crawler/ui/widgets/json_tree_widget.py` (NEW FILE)

```python
class JsonTreeWidget(QTreeWidget):
    """Collapsible tree widget for displaying JSON data."""
    
    # Constructor accepts JSON data
    def __init__(self, data: Union[dict, list, str], parent: Optional[QWidget] = None):
        """
        Args:
            data: JSON data as dict, list, or JSON string
            parent: Parent widget
        """
        pass
    
    # Internal: Build tree recursively
    def _build_tree(self, data: Any, parent_item: QTreeWidgetItem, key: str = None) -> None:
        """Recursively build tree items from JSON data."""
        pass
    
    # Collapse all items except root level
    def collapse_to_root(self) -> None:
        """Collapse all items, showing only root-level keys."""
        pass
```

**Tree Item Structure**:
```
Key Column          | Value Column
--------------------|------------------------------------
screen_dimensions   | {width: 1080, height: 2300}
├─ width           | 1080
└─ height          | 2300
exploration_progress| {current_screen_id: 19, ...}
├─ current_screen_id| 19
└─ ...             | ...
ocr_grounding       | [15 items]
├─ [0]             | {label: 1, text: "zanadio", ...}
│  ├─ label        | 1
│  ├─ text         | "zanadio"
│  └─ bounds       | [311, 429, 770, 550]
└─ [1]             | ...
```

### StepDetailWidget Data

**Location**: `src/mobile_crawler/ui/widgets/ai_monitor_panel.py` (MODIFIED)

```python
class StepDetailWidget(QWidget):
    """Detailed view of a single step."""
    
    # Existing fields
    step_number: int
    timestamp: datetime
    success: bool
    full_prompt: str
    full_response: str
    parsed_actions: List[dict]
    error_message: Optional[str]
    
    # NEW fields for screenshot toggle
    _annotated_pixmap: Optional[QPixmap]  # Screenshot with action bounding boxes
    _ocr_pixmap: Optional[QPixmap]        # Screenshot with OCR element labels
    _ocr_grounding: List[dict]            # OCR element data for rendering
    _current_view: str                    # "annotated" or "ocr"
```

### OCR Grounding Element

**Structure** (from AI prompt data):

```python
ocr_element = {
    "label": int,           # Numeric label ID (1, 2, 3, ...)
    "text": str,            # Detected text content
    "bounds": List[int]     # [x1, y1, x2, y2] bounding box coordinates
}
```

---

## Response Data Structures

### AIInteractionService Response Data

**Source**: `src/mobile_crawler/infrastructure/ai_interaction_service.py`

This is the **FULL** response data that should be used:

```python
response_data = {
    "success": bool,                # True if AI call succeeded
    "raw_response": str,            # Raw text response from AI
    "parsed_response": str,         # JSON string of parsed actions
    "error_message": Optional[str], # Error if failed
    "latency_ms": float,           # Response time
    "tokens_input": Optional[int], # Input token count
    "tokens_output": Optional[int] # Output token count
}
```

### CrawlerLoop Response Data (SUMMARY ONLY - DO NOT USE FOR UI)

**Source**: `src/mobile_crawler/core/crawler_loop.py` line 543

This is minimal summary data for statistics:

```python
response_data = {
    "actions_count": int,
    "signup_completed": bool,
    "latency_ms": float
}
```

**⚠️ WARNING**: The UI should distinguish between these two response data formats and only use the AIInteractionService data for displaying response details.

---

## Validation Rules

1. **JSON Parsing**:
   - If `full_prompt` or `full_response` is not valid JSON, display as plain text
   - Handle escaped JSON strings (JSON inside JSON)

2. **Success Determination**:
   ```python
   success = (
       "parsed_response" in response_data or
       "actions" in response_data or
       response_data.get("actions_count", 0) > 0
   ) and not response_data.get("error_message")
   ```

3. **Duplicate Prevention**:
   ```python
   # Before processing in add_response()
   if interaction.get("_response_updated"):
       return  # Skip duplicate response
   interaction["_response_updated"] = True
   ```

---

## State Transitions

### AI Interaction Item States

```
┌────────────────────────────────────────────────────────────┐
│                    AI MONITOR ITEM                          │
└────────────────────────────────────────────────────────────┘
                              │
                    add_request() called
                              │
                              ▼
                    ┌─────────────────┐
                    │     PENDING     │  (gray circle indicator)
                    │   ○ Step N      │
                    │   Prompt: ...   │
                    │   Response:     │
                    └────────┬────────┘
                             │
                   add_response() called
                             │
           ┌─────────────────┴─────────────────┐
           │                                   │
           ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│    SUCCESS      │                 │     FAILED      │
│   ✓ Step N      │                 │   ✗ Step N      │
│   Prompt: ...   │                 │   Prompt: ...   │
│   Response: ... │                 │   Response: ... │
└─────────────────┘                 │   Error: ...    │
                                    └─────────────────┘
```

### Screenshot View States

```
┌─────────────────────────────────────────┐
│         SCREENSHOT PANEL                 │
├─────────────────────────────────────────┤
│  (•) Annotated  ( ) OCR                  │
├─────────────────────────────────────────┤
│                                          │
│   ┌────────────────────────────┐        │
│   │                            │        │
│   │    [Screenshot Display]    │        │
│   │                            │        │
│   └────────────────────────────┘        │
│                                          │
└─────────────────────────────────────────┘

Toggle to OCR:
┌─────────────────────────────────────────┐
│  ( ) Annotated  (•) OCR                  │
├─────────────────────────────────────────┤
│   ┌────────────────────────────┐        │
│   │  [1] zanadio               │        │
│   │  [2] Create a free...      │        │
│   │  [3] E-mail*               │        │
│   │    ... OCR labeled image   │        │
│   └────────────────────────────┘        │
└─────────────────────────────────────────┘
```
