"""Domain models for the mobile crawler."""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class UIElement:
    """UI element extracted from UiAutomator2 XML hierarchy."""
    element_id: str              # Unique identifier for this element
    bounds: Tuple[int, int, int, int]  # (x1, y1, x2, y2) pixel coordinates
    text: str                    # Visible text content
    content_desc: str            # Accessibility content description
    class_name: str              # Android widget class (e.g., android.widget.Button)
    package: str                 # Package name
    clickable: bool              # Is element clickable?
    visible: bool                # Is element visible on screen?
    enabled: bool                # Is element enabled for interaction?
    resource_id: Optional[str]   # Android resource ID (may be None)
    xpath: Optional[str]         # XPath to element in hierarchy
    center_x: int                # Center X coordinate (derived from bounds)
    center_y: int                # Center Y coordinate (derived from bounds)


@dataclass
class ActionResult:
    """Result of executing an action."""
    success: bool
    action_type: str
    target: str
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    navigated_away: bool = False  # Did screen change?
    input_text: Optional[str] = None  # Text input or extracted OTP


@dataclass
class BoundingBox:
    """Bounding box for UI element targeting."""
    top_left: Tuple[int, int]
    bottom_right: Tuple[int, int]


@dataclass
class AIAction:
    """Action recommended by AI."""
    action: str
    action_desc: str
    target_bounding_box: Optional[BoundingBox] = None
    label_id: Optional[int] = None
    input_text: Optional[str] = None
    reasoning: str = ""


@dataclass
class AIResponse:
    """Response from AI model."""
    actions: List[AIAction]
    signup_completed: bool
    latency_ms: float = 0.0  # AI response time in milliseconds