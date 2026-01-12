# Internal Contracts: Debug Overlay & Step-by-Step Mode

**Feature**: 008-debug-overlay  
**Date**: 2026-01-12

This document defines the internal interfaces (contracts) between components. These are not REST APIs but Python interface contracts.

---

## 1. OverlayRenderer Interface

**Module**: `mobile_crawler.domain.overlay_renderer`

### Class: OverlayRenderer

```python
class OverlayRenderer:
    """Renders coordinate overlays onto images."""
    
    # Color palette for actions (0-indexed)
    COLORS: List[str] = ["#00FF00", "#0088FF", "#FF8800", "#FF00FF", "#00FFFF"]
    ERROR_COLOR: str = "#FF0000"
    
    def render_overlays(
        self,
        image: PIL.Image.Image,
        actions: List[Dict[str, Any]],
        image_dimensions: Optional[Tuple[int, int]] = None
    ) -> PIL.Image.Image:
        """
        Render bounding box overlays onto an image.
        
        Args:
            image: Source image to render overlays on
            actions: List of action dicts with 'target_bounding_box' key
                     Each bbox has 'top_left' and 'bottom_right' as [x, y] lists
            image_dimensions: Optional (width, height) for bounds checking
                              Defaults to image.size
        
        Returns:
            New image with overlays rendered (original is not modified)
        
        Overlay includes:
            - Rectangle border in action color
            - Filled circle at center point
            - Action index label (1-based) at top-left of box
            - Dashed red border for out-of-bounds coordinates
        """
        ...
    
    def save_annotated(
        self,
        image: PIL.Image.Image,
        actions: List[Dict[str, Any]],
        original_path: str
    ) -> str:
        """
        Render overlays and save annotated image to disk.
        
        Args:
            image: Source image
            actions: List of action dicts
            original_path: Path to original screenshot (e.g., "screenshots/run_1/step_001.png")
        
        Returns:
            Path to saved annotated image (e.g., "screenshots/run_1/step_001_annotated.png")
        
        Raises:
            IOError: If save fails (disk full, permissions, etc.)
        """
        ...
```

---

## 2. CrawlerLoop Extensions

**Module**: `mobile_crawler.core.crawler_loop`

### Extended Methods

```python
class CrawlerLoop:
    # Existing methods...
    
    # NEW: Step-by-step mode control
    
    def set_step_by_step_enabled(self, enabled: bool) -> None:
        """
        Enable or disable step-by-step mode.
        
        Can be called during a running crawl. Change takes effect
        after current step completes.
        
        Args:
            enabled: True to enable step-by-step mode
        """
        ...
    
    def is_step_by_step_enabled(self) -> bool:
        """
        Check if step-by-step mode is enabled.
        
        Returns:
            True if step-by-step mode is active
        """
        ...
    
    def advance_step(self) -> None:
        """
        Advance to the next step when paused in step-by-step mode.
        
        Must only be called when state is PAUSED_STEP.
        Signals the crawler thread to resume for one step.
        
        Raises:
            RuntimeError: If not in PAUSED_STEP state
        """
        ...
```

---

## 3. CrawlState Extension

**Module**: `mobile_crawler.core.crawl_state_machine`

### Extended Enum

```python
class CrawlState(Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED_MANUAL = "paused_manual"
    PAUSED_STEP = "paused_step"  # NEW
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
```

### Extended Transitions

Add to `_is_valid_transition`:
```python
CrawlState.RUNNING: [
    CrawlState.PAUSED_MANUAL, 
    CrawlState.PAUSED_STEP,  # NEW
    CrawlState.STOPPING, 
    CrawlState.ERROR
],
CrawlState.PAUSED_STEP: [  # NEW
    CrawlState.RUNNING,
    CrawlState.PAUSED_MANUAL,
    CrawlState.STOPPING,
    CrawlState.ERROR
],
```

---

## 4. Signal Adapter Extensions

**Module**: `mobile_crawler.ui.signal_adapter`

### Extended Signals

```python
class QtSignalAdapter(QObject):
    # Existing signals...
    
    # NEW: Step-by-step mode signals
    step_paused = Signal(int, int)  # run_id, step_number
```

### New Event Handler

```python
def on_step_paused(self, run_id: int, step_number: int) -> None:
    """Called when crawler pauses after a step in step-by-step mode."""
    self.step_paused.emit(run_id, step_number)
```

---

## 5. CrawlControlPanel Extensions

**Module**: `mobile_crawler.ui.widgets.crawl_control_panel`

### New UI Elements

```python
class CrawlControlPanel(QWidget):
    # NEW signals
    step_by_step_toggled = Signal(bool)  # enabled state
    next_step_requested = Signal()
    
    def _setup_ui(self):
        # Existing UI...
        
        # NEW: Step-by-step checkbox
        self.step_by_step_checkbox = QCheckBox("Step-by-Step Mode")
        self.step_by_step_checkbox.toggled.connect(self.step_by_step_toggled.emit)
        
        # NEW: Next Step button (initially hidden/disabled)
        self.next_step_button = QPushButton("Next Step")
        self.next_step_button.setEnabled(False)
        self.next_step_button.setVisible(False)
        self.next_step_button.clicked.connect(self.next_step_requested.emit)
    
    def update_state(self, state: CrawlState):
        # Extended to handle PAUSED_STEP state
        if state == CrawlState.PAUSED_STEP:
            self.status_label.setText("Paused (Step-by-Step)")
            self.status_label.setStyleSheet("color: purple; font-weight: bold;")
            self.next_step_button.setEnabled(True)
            self.next_step_button.setVisible(True)
            self.stop_button.setEnabled(True)
```

---

## 6. ScreenshotCapture Extensions

**Module**: `mobile_crawler.infrastructure.screenshot_capture`

### Extended Class

```python
class ScreenshotCapture:
    # Existing methods...
    
    def capture_full_with_annotations(
        self,
        actions: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> Tuple[Image.Image, str, str, str, float]:
        """
        Capture screenshot, save original and annotated versions.
        
        Args:
            actions: List of actions with bounding boxes for overlay
            filename: Optional base filename
        
        Returns:
            Tuple of:
                - PIL Image (original)
                - Original file path
                - Annotated file path
                - AI-optimized base64 string
                - Scale factor
        """
        ...
```

**Note**: This method uses `OverlayRenderer` internally to create the annotated version.

---

## Usage Flow

```
1. MainWindow connects:
   - control_panel.step_by_step_toggled → crawler_loop.set_step_by_step_enabled
   - control_panel.next_step_requested → crawler_loop.advance_step
   - signal_adapter.step_paused → control_panel.update_state

2. During crawl:
   a. screenshot_capture.capture_full() returns image + paths
   b. AI response parsed for actions
   c. overlay_renderer.save_annotated() saves annotated version
   d. If step-by-step enabled:
      - crawler_loop transitions to PAUSED_STEP
      - signal_adapter emits step_paused
      - control_panel shows Next Step button
      - User clicks Next Step
      - control_panel emits next_step_requested
      - crawler_loop.advance_step() resumes

3. UI overlay drawing:
   - StepDetailWidget receives parsed_actions
   - Uses QPainter to draw overlays on displayed QPixmap
   - (Independent of file-saving logic)
```
