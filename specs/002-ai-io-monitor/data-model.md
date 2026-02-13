# Data Model: AI Input/Output Monitor

**Feature**: 002-ai-io-monitor  
**Date**: 2026-01-11  
**Phase**: 1 - Design

## Overview

This feature uses existing data models with no schema changes. This document describes how existing entities are used and any view-specific data structures.

## Existing Entities (No Changes)

### AIInteraction (existing)

**Source**: `src/mobile_crawler/infrastructure/ai_interaction_repository.py`

| Field | Type | Description |
|-------|------|-------------|
| id | int | Primary key |
| run_id | int | FK to runs table |
| step_number | int | Step in crawl sequence |
| timestamp | datetime | When interaction occurred |
| request_json | str | JSON: {system_prompt, user_prompt} |
| screenshot_path | str? | Path to screenshot used |
| response_raw | str? | Raw AI response text |
| response_parsed_json | str? | JSON: {actions[], signup_completed} |
| tokens_input | int? | Input token count |
| tokens_output | int? | Output token count |
| latency_ms | float? | Response time in milliseconds |
| success | bool | Whether interaction succeeded |
| error_message | str? | Error details if failed |
| retry_count | int | Number of retries before success/failure |

## View Data Structures (UI-only, not persisted)

### AIInteractionDisplayItem

**Purpose**: Lightweight structure for displaying an interaction in the list.

```python
@dataclass
class AIInteractionDisplayItem:
    """Display model for a single AI interaction in the monitor."""
    step_number: int
    timestamp: datetime
    success: bool
    latency_ms: Optional[float]
    tokens_in: Optional[int]
    tokens_out: Optional[int]
    error_message: Optional[str]
    
    # Truncated previews for list display
    prompt_preview: str      # First 100 chars of user prompt
    response_preview: str    # First 100 chars of response
    
    # Full data for detail expansion
    full_prompt: str
    full_response: str
    parsed_actions: List[dict]  # Parsed from response_parsed_json
```

### MonitorFilterState

**Purpose**: Tracks current filter/search state.

```python
@dataclass
class MonitorFilterState:
    """Filter state for AI monitor panel."""
    status_filter: str = "all"  # "all" | "success" | "failed"
    search_text: str = ""
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CRAWLER THREAD                              │
├─────────────────────────────────────────────────────────────────────┤
│  AIInteractionService.get_next_actions()                            │
│       │                                                             │
│       ├── Builds request_json ─────────────────────┐                │
│       │                                            │                │
│       ├── Calls model_adapter.generate_response()  │                │
│       │                                            │                │
│       ├── Creates AIInteraction ───────────────────┤                │
│       │                                            │                │
│       └── Saves to ai_interaction_repository ──────┤                │
│                                                    │                │
│  CrawlerEventListener (signal_adapter)             │                │
│       │                                            │                │
│       ├── on_ai_request_sent(run_id, step, dict) ──┼── Signal ──┐   │
│       │                                            │            │   │
│       └── on_ai_response_received(run_id, step, dict) ── Signal ┼───┤
└─────────────────────────────────────────────────────────────────│───┘
                                                                  │
┌─────────────────────────────────────────────────────────────────│───┐
│                           UI THREAD                             │   │
├─────────────────────────────────────────────────────────────────│───┤
│                                                                 │   │
│  QtSignalAdapter                                                │   │
│       │                                                         │   │
│       ├── ai_request_sent.emit() ←──────────────────────────────┘   │
│       │                                                             │
│       └── ai_response_received.emit() ←─────────────────────────────┘
│               │                                                     │
│               └── Connected to AIMonitorPanel._on_ai_response()     │
│                       │                                             │
│                       ├── Create AIInteractionDisplayItem           │
│                       │                                             │
│                       ├── Add to QListWidget                        │
│                       │                                             │
│                       └── Apply current filters                     │
└─────────────────────────────────────────────────────────────────────┘
```

## JSON Schema Reference

### request_json structure

```json
{
  "system_prompt": "You are an AI that controls a mobile app...",
  "user_prompt": "Analyze this screenshot and decide the next action..."
}
```

### response_parsed_json structure

```json
{
  "actions": [
    {
      "action": "tap",
      "action_desc": "Tap the login button",
      "target_bounding_box": {
        "top_left": [100, 200],
        "bottom_right": [300, 250]
      },
      "input_text": null,
      "reasoning": "The login button will open the authentication flow"
    }
  ],
  "signup_completed": false
}
```

## No Database Migrations Required

This feature only reads from existing tables and structures. No schema changes needed.
