# Research: AI Input/Output Monitor

**Feature**: 002-ai-io-monitor  
**Date**: 2026-01-11  
**Phase**: 0 - Research

## Research Tasks

### 1. Existing Signal Infrastructure

**Question**: How are AI events currently communicated from the crawler to the UI?

**Finding**: The `QtSignalAdapter` class in [signal_adapter.py](../../src/mobile_crawler/ui/signal_adapter.py) already defines the required signals:

```python
ai_request_sent = Signal(int, int, dict)      # run_id, step_number, request_data
ai_response_received = Signal(int, int, dict)  # run_id, step_number, response_data
```

These signals implement the `CrawlerEventListener` protocol methods:
- `on_ai_request_sent(run_id, step_number, request_data)`
- `on_ai_response_received(run_id, step_number, response_data)`

**Decision**: Use existing signals directly - no new infrastructure needed.

**Rationale**: Signals are already defined and follow the established event pattern.

**Alternatives Considered**: None - signals already exist.

---

### 2. Data Available for Display

**Question**: What AI interaction data is available for display?

**Finding**: The `AIInteraction` dataclass in [ai_interaction_repository.py](../../src/mobile_crawler/infrastructure/ai_interaction_repository.py) contains:

| Field | Type | Display Use |
|-------|------|-------------|
| `step_number` | int | Step indicator |
| `timestamp` | datetime | Time display |
| `request_json` | str | Prompt content (JSON with system_prompt, user_prompt) |
| `screenshot_path` | str | Optional thumbnail link |
| `response_raw` | str | Raw AI response |
| `response_parsed_json` | str | Parsed actions/reasoning |
| `tokens_input` | int | Token metrics |
| `tokens_output` | int | Token metrics |
| `latency_ms` | float | Performance metric |
| `success` | bool | Success/failure indicator |
| `error_message` | str | Error details |
| `retry_count` | int | Retry indicator |

**Decision**: Display all fields with collapsible sections for long content (prompts, responses).

**Rationale**: Full data visibility for debugging; collapsible UI prevents clutter.

---

### 3. UI Widget Pattern

**Question**: What patterns do existing widgets follow?

**Finding**: Analyzing [log_viewer.py](../../src/mobile_crawler/ui/widgets/log_viewer.py):

- Inherits from `QWidget`
- Uses `QGroupBox` for visual grouping
- Uses `QTextEdit` for scrollable content (read-only)
- Uses `QComboBox` for filtering
- Emits signals for parent communication
- Uses `QVBoxLayout` and `QHBoxLayout` for structure
- Color-codes content based on type

**Decision**: Follow `LogViewer` pattern with these adaptations:
- Use `QTreeWidget` or `QListWidget` for structured interaction entries
- Add collapsible detail panels for each entry
- Use color coding: green for success, red for failure

**Rationale**: Consistency with existing codebase; proven patterns.

---

### 4. Layout Integration

**Question**: Where should the AI monitor panel be placed in the main window?

**Finding**: Current layout in [main_window.py](../../src/mobile_crawler/ui/main_window.py):

```
┌─────────────────────────────────────────────────────────┐
│ Menu Bar                                                │
├──────────┬──────────────┬───────────────────────────────┤
│ Left     │ Center       │ Right                         │
│ (25%)    │ (35%)        │ (40%)                         │
│          │              │                               │
│ Device   │ Crawl        │ Log Viewer                    │
│ App      │ Controls     │                               │
│ AI       │ Stats        │                               │
│ Settings │              │                               │
├──────────┴──────────────┴───────────────────────────────┤
│ Bottom: Run History                                     │
└─────────────────────────────────────────────────────────┘
```

**Decision**: Add AI Monitor as a tab alongside Log Viewer in the right panel, using `QTabWidget`.

**Rationale**: 
- Doesn't require layout restructuring
- Both Log Viewer and AI Monitor serve similar monitoring purposes
- Tab switching allows focus on relevant view
- Maintains current proportions

**Alternatives Considered**:
1. Replace Log Viewer → Rejected: logs still valuable
2. Add as 4th column → Rejected: too cramped
3. Add below Log Viewer → Rejected: vertical space limited

---

### 5. Performance Considerations

**Question**: How to handle 100+ interactions without UI lag?

**Finding**: 
- PySide6 `QListWidget`/`QTreeWidget` handle 1000+ items efficiently with virtual scrolling
- Signal emissions from background thread are already thread-safe via Qt's queued connections
- LogViewer auto-scrolls to bottom which can be expensive with many rapid updates

**Decision**: 
- Use `QListWidget` with custom item widgets for entries
- Batch updates if receiving multiple signals within 100ms
- Only auto-scroll if user is at bottom (smart scroll)
- Limit initial visible items, lazy-load details on expansion

**Rationale**: Proven patterns for large lists in Qt; smart scroll respects user review.

---

### 6. Filtering/Search Implementation

**Question**: How to implement filtering and search efficiently?

**Finding**: 
- `QListWidget` supports `setRowHidden()` for filtering
- Can store interaction data in item's `data(Qt.UserRole)` for search matching
- Real-time filtering as user types is standard UX

**Decision**:
- Filter dropdown: "All", "Success Only", "Failed Only"
- Search box with debounced input (300ms delay)
- Filter/search operates on loaded items in memory
- No database re-queries needed for filtering

**Rationale**: Simple, fast, follows existing patterns.

---

## Summary of Decisions

| Topic | Decision |
|-------|----------|
| Event Source | Use existing `QtSignalAdapter.ai_request_sent`/`ai_response_received` signals |
| Data Model | Use existing `AIInteraction` dataclass - no new models |
| Widget Pattern | Follow `LogViewer` pattern with `QListWidget` for entries |
| Layout Position | Tabbed panel with Log Viewer in right panel |
| Performance | Smart scroll, lazy detail loading, item virtualization |
| Filtering | In-memory filtering via `setRowHidden()`, debounced search |

## Dependencies Identified

- **Required**: PySide6 (already in dependencies)
- **No new dependencies needed**

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| High-frequency updates causing UI lag | Batch updates, limit refresh rate to 10Hz max |
| Large response text slowing rendering | Truncate display, show full on expand |
| Thread safety issues | Use Qt signal/slot mechanism (already thread-safe) |
