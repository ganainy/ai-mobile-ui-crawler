# Research: Debug Overlay & Step-by-Step Mode

**Feature**: 008-debug-overlay  
**Date**: 2026-01-12

## Research Topics

### 1. Drawing Overlays on QPixmap/QImage in PySide6

**Decision**: Use `QPainter` to draw directly on `QPixmap` objects in the UI layer.

**Rationale**:
- `QPainter` is the native Qt drawing API, well-integrated with PySide6
- Can draw rectangles, lines, text, and custom shapes
- Works directly on `QPixmap` which is already used in `StepDetailWidget`
- Preserves image quality without additional conversions

**Alternatives Considered**:
1. **Pillow drawing + convert to QPixmap**: Adds extra conversion step (PIL → bytes → QPixmap). More complex and slower.
2. **QGraphicsView/QGraphicsScene**: Overkill for simple overlays on a static image. Better for interactive graphics.
3. **Custom OpenGL widget**: Way overkill for 2D rectangle drawing.

**Implementation Approach**:
```python
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtCore import Qt

def draw_overlay(pixmap: QPixmap, bboxes: List[dict], colors: List[QColor]) -> QPixmap:
    """Draw bounding boxes on a pixmap."""
    result = pixmap.copy()  # Don't modify original
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    for i, (bbox, color) in enumerate(zip(bboxes, colors)):
        pen = QPen(color, 2)
        painter.setPen(pen)
        
        # Draw rectangle
        x1, y1 = bbox['top_left']
        x2, y2 = bbox['bottom_right']
        painter.drawRect(x1, y1, x2 - x1, y2 - y1)
        
        # Draw center point
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        painter.drawEllipse(cx - 4, cy - 4, 8, 8)
        
        # Draw action index
        painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        painter.drawText(x1 + 5, y1 + 18, str(i + 1))
    
    painter.end()
    return result
```

---

### 2. Saving Annotated Screenshots with Pillow

**Decision**: Use Pillow's `ImageDraw` module to draw overlays for file saving (separate from Qt rendering).

**Rationale**:
- Pillow is already a project dependency (used in `screenshot_capture.py`)
- `ImageDraw` provides rectangle, ellipse, and text drawing
- Can save directly to PNG without quality loss
- Keeps file I/O logic separate from Qt UI logic

**Alternatives Considered**:
1. **Convert QPixmap to PIL Image**: Adds Qt dependency to infrastructure layer; violates separation of concerns.
2. **Save QPixmap directly**: `QPixmap.save()` works but would require Qt imports in infrastructure code.

**Implementation Approach**:
```python
from PIL import Image, ImageDraw, ImageFont

def render_overlays_to_image(image: Image.Image, actions: List[dict]) -> Image.Image:
    """Render overlays onto a PIL Image and return the annotated copy."""
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    
    colors = ['#00FF00', '#0088FF', '#FF8800', '#FF00FF', '#00FFFF']
    
    for i, action in enumerate(actions):
        bbox = action.get('target_bounding_box', {})
        if not bbox:
            continue
            
        color = colors[i % len(colors)]
        x1, y1 = bbox['top_left']
        x2, y2 = bbox['bottom_right']
        
        # Draw rectangle
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        
        # Draw center point
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=color)
        
        # Draw action index
        draw.text((x1 + 5, y1 + 5), str(i + 1), fill=color)
    
    return annotated
```

---

### 3. Extending CrawlState for Step-by-Step Mode

**Decision**: Add a new `PAUSED_STEP` state to `CrawlState` enum.

**Rationale**:
- The existing `PAUSED_MANUAL` state is for user-initiated pauses
- `PAUSED_STEP` semantically represents "paused after step, awaiting next step command"
- Allows the control panel to differentiate between pause types and show appropriate buttons
- Minimal change to state machine transition logic

**Alternatives Considered**:
1. **Reuse PAUSED_MANUAL**: Would conflate two different pause reasons, making UI logic harder.
2. **Use a separate boolean flag**: Would require coordination between flag and state, more error-prone.
3. **Event-based without state**: Would lose the benefits of centralized state management.

**State Transitions**:
```
RUNNING → PAUSED_STEP (when step completes and step-by-step enabled)
PAUSED_STEP → RUNNING (when "Next Step" clicked)
PAUSED_STEP → STOPPING (when "Stop" clicked)
PAUSED_STEP → PAUSED_MANUAL (when manual "Pause" clicked - unlikely)
```

---

### 4. Signaling Step Completion for Step-by-Step Mode

**Decision**: Use existing `step_completed` signal plus a new threading `Event` for blocking.

**Rationale**:
- Crawler loop runs in a background thread
- Need to block the thread without spinning (CPU-intensive)
- `threading.Event` provides efficient wait/signal pattern
- UI thread sets the event when "Next Step" is clicked
- Crawler thread waits on the event after each step

**Implementation Approach**:
```python
# In CrawlerLoop
self._step_advance_event = threading.Event()
self._step_by_step_enabled = False

def run(self, run_id: int):
    while self._should_continue(...):
        step_success = self._execute_step(...)
        
        if self._step_by_step_enabled:
            self.state_machine.transition_to(CrawlState.PAUSED_STEP)
            self._step_advance_event.clear()
            self._step_advance_event.wait()  # Block until UI signals
            self.state_machine.transition_to(CrawlState.RUNNING)

def advance_step(self):
    """Called from UI when Next Step is clicked."""
    if self.state_machine.state == CrawlState.PAUSED_STEP:
        self._step_advance_event.set()
```

---

### 5. Coordinate Scaling for Overlays

**Decision**: Draw overlays using AI-returned coordinates directly (no scaling).

**Rationale**:
- The screenshot displayed in UI is the AI-compressed version (max 1024x1024)
- AI returns coordinates relative to this compressed image
- The QPixmap displayed in `StepDetailWidget` is also from this same base64
- Therefore, AI coordinates match the displayed image directly
- The scale_factor returned by `capture_full()` is only needed for action execution (converting back to device coordinates)

**Key Insight**: The overlay is drawn on the image that was sent to the AI, not the original device screenshot. No coordinate conversion is needed for display.

---

### 6. Color Palette for Multiple Actions

**Decision**: Use a predefined palette of 5 distinct, high-contrast colors.

**Rationale**:
- Accessibility: High contrast against typical mobile UI backgrounds
- Distinguishable: Each color is visually distinct
- Sufficient: Rarely more than 3-4 actions per step

**Color Palette**:
| Index | Color Name | Hex Code | Use Case |
|-------|------------|----------|----------|
| 1 | Green | #00FF00 | Primary action |
| 2 | Blue | #0088FF | Secondary action |
| 3 | Orange | #FF8800 | Tertiary action |
| 4 | Magenta | #FF00FF | Fourth action |
| 5 | Cyan | #00FFFF | Fifth+ actions (cycles) |

**Invalid Coordinates**: Use red (#FF0000) with dashed border for out-of-bounds coordinates.

---

## Summary of Decisions

| Topic | Decision |
|-------|----------|
| UI Overlay Drawing | QPainter on QPixmap |
| File Overlay Drawing | Pillow ImageDraw |
| Pause State | New PAUSED_STEP enum value |
| Thread Blocking | threading.Event |
| Coordinate Scaling | None (AI coords match displayed image) |
| Color Palette | 5-color high-contrast palette |
