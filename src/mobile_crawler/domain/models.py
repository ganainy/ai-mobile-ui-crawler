"""Domain models for the mobile crawler."""

from dataclasses import dataclass


@dataclass
class UIElement:
    """UI element metadata used for coordinate targeting."""
    element_id: str              # Unique identifier for this element
    bounds: tuple[int, int, int, int]  # (x1, y1, x2, y2) pixel coordinates
    text: str                    # Visible text content
    content_desc: str            # Accessibility content description
    class_name: str              # Android widget class (e.g., android.widget.Button)
    package: str                 # Package name
    clickable: bool              # Is element clickable?
    visible: bool                # Is element visible on screen?
    enabled: bool                # Is element enabled for interaction?
    resource_id: str | None   # Android resource ID (may be None)
    xpath: str | None         # XPath to element in hierarchy
    center_x: int                # Center X coordinate (derived from bounds)
    center_y: int                # Center Y coordinate (derived from bounds)


@dataclass
class ActionResult:
    """Result of executing an action."""
    success: bool
    action_type: str
    target: str
    duration_ms: float = 0.0
    error_message: str | None = None
    navigated_away: bool = False  # Did screen change?
    input_text: str | None = None  # Text input or extracted OTP
    was_retried: bool = False         # Was this action retried after recovery?
    retry_count: int = 0             # Number of retries before success/failure
    recovery_time_ms: float | None = None  # Total time spent in recovery
    execution_time_ms: float = 0.0   # NEW: Action execution time in milliseconds


@dataclass
class BoundingBox:
    """Bounding box for UI element targeting."""
    top_left: tuple[int, int]
    bottom_right: tuple[int, int]


@dataclass
class AIAction:
    """Action recommended by AI."""
    action: str
    action_desc: str
    target_bounding_box: BoundingBox | None = None
    label_id: int | None = None
    input_text: str | None = None
    reasoning: str = ""


@dataclass
class AIResponse:
    """Response from AI model."""
    actions: list[AIAction]
    signup_completed: bool
    latency_ms: float = 0.0  # AI response time in milliseconds
