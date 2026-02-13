# Quickstart: UI Monitor Improvements

**Feature**: 017-ui-monitor-improvements  
**Date**: 2026-01-14

## Overview

This guide helps developers understand and work with the UI Monitor improvements. It covers the key files, patterns, and testing strategies.

---

## Key Files

| File | Purpose |
|------|---------|
| `src/mobile_crawler/ui/widgets/ai_monitor_panel.py` | Main AI Monitor widget with list and detail views |
| `src/mobile_crawler/ui/widgets/json_tree_widget.py` | **NEW**: Collapsible JSON tree widget |
| `src/mobile_crawler/ui/main_window.py` | Signal connections and event handlers |
| `src/mobile_crawler/ui/signal_adapter.py` | Qt signals for crawler events |

---

## Development Setup

### Prerequisites

1. Python 3.11+ with PySide6 installed
2. Run the UI to test changes live:
   ```bash
   cd e:\VS-projects\mobile-crawler
   python .\run_ui.py
   ```

### Quick Test Cycle

1. Make changes to `ai_monitor_panel.py`
2. Restart the UI (`Ctrl+C` then `python .\run_ui.py`)
3. Start a crawl and observe the AI Monitor panel
4. Click "Show Details" to see the Step Detail view

---

## Understanding the Event Flow

### AI Monitor Event Sequence

```
CrawlerLoop                  AIInteractionService           MainWindow              AIMonitorPanel
    │                              │                            │                        │
    │──on_ai_request_sent─────────────────────────────────────>│                        │
    │                              │                            │───add_request()─────>│
    │                              │                            │                        │
    │                              │──on_ai_response_received──>│                        │
    │                              │  (FULL DATA)               │───add_response()────>│
    │                              │                            │                        │
    │──on_ai_response_received─────────────────────────────────>│                        │
    │  (SUMMARY DATA)              │                            │  (SHOULD IGNORE)       │
```

### Key Insight

Two sources emit `on_ai_response_received`:
1. **AIInteractionService** - Contains full response data (`parsed_response`, `raw_response`)
2. **CrawlerLoop** - Contains summary data only (`actions_count`, `latency_ms`)

The UI should only act on the **AIInteractionService** data.

---

## Code Patterns

### Detecting Full vs Summary Response

```python
def _is_full_response(response_data: dict) -> bool:
    """Check if response_data contains full AI response (not just summary)."""
    return (
        "parsed_response" in response_data or
        "raw_response" in response_data or
        "response" in response_data
    )
```

### Preventing Duplicate Updates

```python
def add_response(self, run_id: int, step_number: int, response_data: dict):
    if step_number not in self._interactions:
        return
    
    interaction = self._interactions[step_number]
    
    # Skip if already updated with full data
    if interaction.get("_response_updated"):
        return
    
    # Only mark as updated if this is full data
    if self._is_full_response(response_data):
        interaction["_response_updated"] = True
    
    # ... rest of update logic
```

### Determining Success Status

```python
def _determine_success(response_data: dict) -> bool:
    """Determine if AI response was successful."""
    # Has error? → Failed
    if response_data.get("error_message"):
        return False
    
    # Has parsed actions? → Success
    if "parsed_response" in response_data:
        try:
            parsed = json.loads(response_data["parsed_response"])
            if "actions" in parsed and len(parsed["actions"]) > 0:
                return True
        except:
            pass
    
    # Has actions count > 0? → Success
    if response_data.get("actions_count", 0) > 0:
        return True
    
    # Default to False
    return False
```

---

## JsonTreeWidget Usage

### Basic Usage

```python
from mobile_crawler.ui.widgets.json_tree_widget import JsonTreeWidget

# From dict
data = {"key": "value", "nested": {"inner": 123}}
tree = JsonTreeWidget(data)

# From JSON string
json_str = '{"key": "value"}'
tree = JsonTreeWidget(json_str)

# Add to layout
layout.addWidget(tree)
```

### Styling

The tree automatically applies dark theme styling to match the application:

```python
tree.setStyleSheet("""
    QTreeWidget {
        background-color: #2b2b2b;
        color: #e0e0e0;
        border: none;
    }
    QTreeWidget::item {
        padding: 4px;
    }
    QTreeWidget::item:selected {
        background-color: #3d3d3d;
    }
""")
```

---

## Screenshot Toggle Implementation

### Drawing OCR Overlays

```python
def draw_ocr_overlays_on_pixmap(pixmap: QPixmap, ocr_elements: List[dict]) -> QPixmap:
    """Draw OCR element labels on a pixmap."""
    if not ocr_elements:
        return pixmap
    
    result = pixmap.copy()
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Alternating colors for labels
    colors = [QColor("#FF6B6B"), QColor("#4ECDC4"), QColor("#45B7D1")]
    
    for element in ocr_elements:
        label = element.get("label", 0)
        bounds = element.get("bounds", [])
        
        if len(bounds) < 4:
            continue
        
        x1, y1, x2, y2 = bounds
        color = colors[label % len(colors)]
        
        # Draw rectangle
        pen = QPen(color, 2)
        painter.setPen(pen)
        painter.drawRect(x1, y1, x2 - x1, y2 - y1)
        
        # Draw label number
        font = QFont("Arial", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(x1 + 2, y1 - 2, f"[{label}]")
    
    painter.end()
    return result
```

---

## Testing

### Manual Testing Steps

1. **JSON Expand/Collapse**:
   - Start a crawl
   - Go to AI Monitor → Click "Show Details" on any step
   - Verify Prompt Data shows collapsible tree
   - Click to expand/collapse nodes

2. **Empty Response Fix**:
   - Start a crawl
   - Verify Response panel shows AI response text
   - Verify Parsed Actions shows action details

3. **Failed Status Fix**:
   - Run a successful crawl
   - Verify steps show green checkmark (✓)
   - Force an error and verify red X (✗)

4. **Duplicate Fix**:
   - Run a crawl with 5 steps
   - Count items in AI Monitor → Should be exactly 5

5. **Screenshot Toggle**:
   - Open Step Detail
   - Toggle between Annotated and OCR views
   - Verify different overlays appear

### Unit Test Example

```python
# tests/ui/test_json_tree_widget.py
import pytest
from mobile_crawler.ui.widgets.json_tree_widget import JsonTreeWidget

def test_json_tree_widget_from_dict():
    data = {"name": "test", "value": 123}
    widget = JsonTreeWidget(data)
    
    assert widget.topLevelItemCount() == 2
    assert widget.topLevelItem(0).text(0) == "name"
    assert widget.topLevelItem(1).text(0) == "value"

def test_json_tree_widget_nested():
    data = {"outer": {"inner": "value"}}
    widget = JsonTreeWidget(data)
    
    outer_item = widget.topLevelItem(0)
    assert outer_item.childCount() == 1
    assert outer_item.child(0).text(0) == "inner"

def test_json_tree_widget_array():
    data = {"items": [1, 2, 3]}
    widget = JsonTreeWidget(data)
    
    items_node = widget.topLevelItem(0)
    assert "[3 items]" in items_node.text(1)
```

---

## Common Issues

### Issue: Tree widget shows raw JSON string

**Cause**: Input is a JSON string inside a JSON string (escaped)  
**Fix**: Double-parse if first parse returns a string

```python
def _parse_json(data):
    if isinstance(data, str):
        parsed = json.loads(data)
        # Handle double-encoded JSON
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        return parsed
    return data
```

### Issue: Screenshot toggle shows blank

**Cause**: OCR grounding data not extracted from prompt  
**Fix**: Parse prompt JSON and extract `ocr_grounding` key

```python
try:
    prompt_data = json.loads(full_prompt)
    ocr_grounding = prompt_data.get("ocr_grounding", [])
except:
    ocr_grounding = []
```
