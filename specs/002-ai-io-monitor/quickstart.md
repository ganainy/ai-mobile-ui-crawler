# Quickstart: AI Input/Output Monitor

**Feature**: 002-ai-io-monitor  
**Date**: 2026-01-11  
**Phase**: 1 - Design

## Overview

Add an AI Monitor panel to the mobile-crawler GUI that displays AI prompts and responses in real-time during crawling.

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `src/mobile_crawler/ui/widgets/ai_monitor_panel.py` | Main AI monitor widget |
| `tests/ui/test_ai_monitor_panel.py` | Widget unit tests |

### Modified Files

| File | Change |
|------|--------|
| `src/mobile_crawler/ui/main_window.py` | Integrate AI monitor panel as tab with LogViewer |

## Implementation Order

### Step 1: Create AIMonitorPanel Widget

Create `ai_monitor_panel.py` with:

1. `AIMonitorPanel(QWidget)` class
2. UI components:
   - Filter dropdown (All/Success/Failed)
   - Search box
   - Clear button
   - `QListWidget` for interaction entries
3. Public methods:
   - `add_request(run_id, step_number, request_data)` - add pending request
   - `add_response(run_id, step_number, response_data)` - complete interaction
   - `clear()` - clear all entries
4. Internal helpers:
   - `_create_list_item(interaction)` - create display item
   - `_apply_filters()` - filter visible items
   - `_on_item_expanded(item)` - show full details

### Step 2: Create Interaction Item Widget

Create a custom widget for each list item showing:

```
┌──────────────────────────────────────────────────────────┐
│ [✓] Step 5 | 2.3s | 150→89 tokens           12:34:56 PM │
│ ▶ Tap the 'Sign Up' button to begin registration...     │
└──────────────────────────────────────────────────────────┘

Expanded:
┌──────────────────────────────────────────────────────────┐
│ [✓] Step 5 | 2.3s | 150→89 tokens           12:34:56 PM │
├──────────────────────────────────────────────────────────┤
│ Prompt:                                                  │
│ ┌────────────────────────────────────────────────────┐   │
│ │ Analyze this screenshot and decide...             │   │
│ │ [full prompt text, scrollable]                    │   │
│ └────────────────────────────────────────────────────┘   │
│ Response:                                                │
│ ┌────────────────────────────────────────────────────┐   │
│ │ Action: tap                                        │   │
│ │ Target: [100,200] to [300,250]                     │   │
│ │ Reasoning: The login button will open...           │   │
│ └────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### Step 3: Integrate into MainWindow

Modify `_create_right_panel()` in `main_window.py`:

```python
# Before: Single LogViewer
right_panel = self.log_viewer

# After: Tabbed panel
right_panel = QTabWidget()
right_panel.addTab(self.log_viewer, "Logs")
right_panel.addTab(self.ai_monitor_panel, "AI Monitor")
```

Connect signals:
```python
self.signal_adapter.ai_request_sent.connect(self.ai_monitor_panel.add_request)
self.signal_adapter.ai_response_received.connect(self.ai_monitor_panel.add_response)
```

### Step 4: Write Tests

Create `test_ai_monitor_panel.py` with:

1. Test panel initialization
2. Test adding request shows pending state
3. Test adding response completes interaction
4. Test success/failure visual distinction
5. Test filter by status
6. Test search functionality
7. Test clear functionality
8. Test expansion/collapse

## Key Patterns

### Thread Safety

All updates come via Qt signals (queued connections by default when crossing threads):

```python
# In AIMonitorPanel
def add_response(self, run_id: int, step_number: int, response_data: dict):
    """Slot connected to signal_adapter.ai_response_received."""
    # This runs in UI thread - safe to update widgets
    item = self._find_pending_item(step_number)
    if item:
        self._complete_item(item, response_data)
```

### Smart Scroll

```python
def _should_auto_scroll(self) -> bool:
    """Only auto-scroll if user is near bottom."""
    scrollbar = self.list_widget.verticalScrollBar()
    return scrollbar.value() >= scrollbar.maximum() - 50
```

### Debounced Search

```python
def _on_search_text_changed(self, text: str):
    """Debounce search input."""
    self._search_timer.stop()
    self._search_timer.start(300)  # 300ms delay

def _perform_search(self):
    """Apply search after debounce."""
    self._apply_filters()
```

## Visual Indicators

| State | Indicator |
|-------|-----------|
| Pending (request sent, awaiting response) | ⏳ Yellow background |
| Success | ✓ Green icon |
| Failed | ✗ Red icon, red text |
| Retried | Retry count badge |

## Dependencies

None new - uses existing PySide6 components.

## Acceptance Criteria Mapping

| Spec Criterion | Implementation |
|----------------|----------------|
| SC-001: Updates within 1 second | Direct signal connection, no batching delay |
| SC-002: 100 interactions without lag | QListWidget with item virtualization |
| SC-003: Visual distinction for failures | Red icon + colored background |
| SC-004: Understand AI decision | Show action + reasoning in expanded view |
| SC-005: Historical review in 3 clicks | Click step in history → Switch to AI Monitor tab → Click expand |
| SC-006: Filter/search in 500ms | In-memory filtering, debounced at 300ms |
