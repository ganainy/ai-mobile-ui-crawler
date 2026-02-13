# Data Model: Debug Overlay & Step-by-Step Mode

**Feature**: 008-debug-overlay  
**Date**: 2026-01-12

## Entities

### 1. BoundingBox

Represents a rectangular region on a screenshot.

| Field | Type | Description |
|-------|------|-------------|
| top_left | Tuple[int, int] | (x, y) coordinates of top-left corner |
| bottom_right | Tuple[int, int] | (x, y) coordinates of bottom-right corner |

**Derived Properties**:
- `center`: Tuple[int, int] = ((top_left[0] + bottom_right[0]) // 2, (top_left[1] + bottom_right[1]) // 2)
- `width`: int = bottom_right[0] - top_left[0]
- `height`: int = bottom_right[1] - top_left[1]
- `is_valid`: bool = width > 0 and height > 0

**Validation Rules**:
- `top_left[0] < bottom_right[0]` (positive width)
- `top_left[1] < bottom_right[1]` (positive height)
- Coordinates can be outside image bounds (will be clipped when drawn)

---

### 2. OverlayAction

Represents an action to be drawn as an overlay.

| Field | Type | Description |
|-------|------|-------------|
| action_index | int | 1-based index for display |
| action_type | str | Action type (click, input, etc.) |
| bounding_box | BoundingBox | Target region |
| color | str | Hex color code (e.g., "#00FF00") |
| is_valid | bool | Whether coordinates are within image bounds |

**State Transitions**: N/A (immutable value object)

---

### 3. AnnotatedScreenshot

Represents a screenshot with overlays applied.

| Field | Type | Description |
|-------|------|-------------|
| step_number | int | Step this screenshot belongs to |
| original_path | str | Path to original screenshot file |
| annotated_path | str | Path to annotated screenshot file |
| overlays | List[OverlayAction] | Overlays applied |
| created_at | datetime | When annotation was created |

**Naming Convention**:
- Original: `screenshot_{timestamp}.png`
- Annotated: `screenshot_{timestamp}_annotated.png`

---

### 4. CrawlState (Extended)

Existing enum extended with new state.

| Value | Description |
|-------|-------------|
| UNINITIALIZED | Initial state before crawl starts |
| INITIALIZING | Setting up crawl (connecting to device) |
| RUNNING | Actively executing steps |
| PAUSED_MANUAL | Paused by user clicking Pause button |
| **PAUSED_STEP** | **NEW: Paused after step, awaiting Next Step** |
| STOPPING | Gracefully stopping |
| STOPPED | Crawl completed or stopped |
| ERROR | Error occurred |

**State Transitions** (additions for PAUSED_STEP):
```
RUNNING → PAUSED_STEP       (step completes with step-by-step enabled)
PAUSED_STEP → RUNNING       (Next Step clicked)
PAUSED_STEP → STOPPING      (Stop clicked)
PAUSED_STEP → PAUSED_MANUAL (Pause clicked - unlikely but valid)
```

---

### 5. StepByStepConfig

Configuration for step-by-step mode (stored in UI state, not persisted).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| enabled | bool | False | Whether step-by-step mode is active |

**Notes**:
- Toggling during a run takes effect after current step completes
- Not persisted between application sessions
- Controlled via checkbox in CrawlControlPanel

---

## Relationships

```
CrawlerLoop
    ├── has state: CrawlStateMachine → CrawlState
    ├── has config: StepByStepConfig
    └── emits: step_completed signal
           │
           ├── triggers: OverlayRenderer.render()
           │      └── creates: AnnotatedScreenshot
           │             ├── contains: List[OverlayAction]
           │             │      └── has: BoundingBox
           │             └── saved to: screenshots folder
           │
           └── if step-by-step enabled:
                  └── transitions to: PAUSED_STEP
                         └── awaits: advance_step() call
```

---

## Data Flow

### Overlay Rendering Flow
```
1. AI response received (with actions + bounding boxes)
2. Screenshot already captured (PIL Image)
3. OverlayRenderer.render(image, actions) called
   a. For each action:
      - Create OverlayAction with bounding_box, color, index
      - Validate coordinates against image dimensions
   b. Draw overlays using PIL ImageDraw
   c. Save annotated image to disk
   d. Return AnnotatedScreenshot
4. UI receives step data with parsed_actions
5. StepDetailWidget draws overlays on QPixmap using QPainter
```

### Step-by-Step Flow
```
1. User checks "Step-by-Step Mode" checkbox
   → StepByStepConfig.enabled = True
2. Crawl starts, first step executes
3. Step completes, CrawlerLoop checks if step-by-step enabled
   → Transitions to PAUSED_STEP
   → Blocks on threading.Event
4. UI shows "Next Step" button (enabled), current step overlays
5. User clicks "Next Step"
   → advance_step() called
   → Event set, crawler thread resumes
   → Transitions back to RUNNING
6. Repeat until crawl completes or stopped
```
