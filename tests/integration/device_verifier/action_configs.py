"""Configuration for action verification tests.

Updated to use deep links for navigation and normalized coordinates from TESTAPP_README.md.
"""

from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, Optional

@dataclass
class ActionTestConfig:
    """Configuration for a single action verification test."""
    
    # Unique identifier matching test function name (without test_ prefix)
    name: str
    
    # Display name for logging
    display_name: str
    
    # Deep link route for direct navigation (e.g., "/tap", "/double_tap")
    deep_link_route: str
    
    # Action type to perform
    action_type: str  # "tap", "double_tap", "long_press", "swipe", "drag", "scroll", "input"
    
    # Coordinates (relative 0.0-1.0) where to perform the action
    action_position: Tuple[float, float] = (0.5, 0.5)
    
    # End coordinates for swipe/drag actions (relative 0.0-1.0)
    action_end_position: Optional[Tuple[float, float]] = None
    
    # Additional action parameters
    action_params: Dict[str, Any] = field(default_factory=dict)
    
    # Timeout for success indicator detection (seconds)
    timeout_seconds: int = 3
    
    # DEPRECATED: Hub tile position (no longer used with deep links)
    tile_position: Optional[Tuple[float, float]] = None
    
    def get_action_coords(self, screen_width: int, screen_height: int) -> Tuple[int, int]:
        """Convert relative action position to absolute pixel coordinates."""
        return (
            int(screen_width * self.action_position[0]),
            int(screen_height * self.action_position[1])
        )
    
    def get_action_end_coords(self, screen_width: int, screen_height: int) -> Optional[Tuple[int, int]]:
        """Convert relative end position to absolute pixel coordinates."""
        if self.action_end_position is None:
            return None
        return (
            int(screen_width * self.action_end_position[0]),
            int(screen_height * self.action_end_position[1])
        )


# Action configurations based on TESTAPP_README.md
# All coordinates are normalized (0.0 to 1.0) from the README
ACTION_CONFIGS: Dict[str, ActionTestConfig] = {
    "tap": ActionTestConfig(
        name="tap",
        display_name="Tap",
        deep_link_route="/tap",
        action_type="tap",
        action_position=(0.50, 0.60),  # Calibrated: (0.5, 0.60) center of button
    ),
    "double_tap": ActionTestConfig(
        name="double_tap",
        display_name="Double Tap",
        deep_link_route="/double_tap",
        action_type="double_tap",
        action_position=(0.50, 0.68),  # Calibrated: (0.5, 0.68) center of box
    ),
    "long_press": ActionTestConfig(
        name="long_press",
        display_name="Long Press",
        deep_link_route="/long_press",
        action_type="long_press",
        action_position=(0.50, 0.68),  # Calibrated: (0.5, 0.68) center of box
        action_params={"duration": 1.0},  # ~1 second as per README
    ),
    "drag_drop": ActionTestConfig(
        name="drag_drop",
        display_name="Drag & Drop",
        deep_link_route="/drag_drop",
        action_type="drag",
        action_position=(0.50, 0.53),  # Calibrated: DRAG center y=0.53
        action_end_position=(0.50, 0.83),  # Calibrated: Drop Target center y=0.83
    ),
    "swipe": ActionTestConfig(
        name="swipe",
        display_name="Swipe",
        deep_link_route="/swipe",
        action_type="swipe",
        action_position=(0.80, 0.50),  # Start: right side
        action_end_position=(0.20, 0.50),  # End: left side (swipe left)
    ),
    "input": ActionTestConfig(
        name="input",
        display_name="Input",
        deep_link_route="/input_test",
        action_type="input",
        action_position=(0.50, 0.55),  # From README: (0.50, 0.55)
        action_params={"text": "test"},  # Any non-empty string
    ),
    "slider": ActionTestConfig(
        name="slider",
        display_name="Slider",
        deep_link_route="/slider",
        action_type="swipe",
        action_position=(0.20, 0.59),  # Calibrated: Slider vertical center y=0.59
        action_end_position=(0.80, 0.59),  # Calibrated: Slider vertical center y=0.59
    ),
    "switch": ActionTestConfig(
        name="switch",
        display_name="Switch",
        deep_link_route="/switch",
        action_type="tap",
        action_position=(0.50, 0.56),  # Calibrated: Switch center y=0.56
    ),
    "checkbox": ActionTestConfig(
        name="checkbox",
        display_name="Checkbox",
        deep_link_route="/checkbox",
        action_type="tap",
        action_position=(0.50, 0.56),  # Calibrated: Checkbox center y=0.56
    ),
    "radio": ActionTestConfig(
        name="radio",
        display_name="Radio",
        deep_link_route="/radio",
        action_type="tap",
        action_position=(0.30, 0.61),  # Calibrated: Option 2 y=0.61, shifted left for button
    ),
    "dropdown": ActionTestConfig(
        name="dropdown",
        display_name="Dropdown",
        deep_link_route="/dropdown",
        action_type="tap",
        action_position=(0.50, 0.59),  # Calibrated: Trigger at y=0.59
        action_params={"select_position": (0.50, 0.65)},  # Calibrated: Banana at y=0.65
    ),
    "stepper": ActionTestConfig(
        name="stepper",
        display_name="Stepper",
        deep_link_route="/stepper",
        action_type="tap",
        action_position=(0.60, 0.58),  # Calibrated: Plus button at y=0.58
        action_params={"repeat": 5},  # Tap 5 times to reach count=5
    ),
    "scroll": ActionTestConfig(
        name="scroll",
        display_name="Scroll",
        deep_link_route="/scroll",
        action_type="scroll",
        action_position=(0.50, 0.80),  # Start position
        action_end_position=(0.50, 0.20),  # End position (scroll up gesture)
        action_params={"direction": "down", "repeat": 5},  # Scroll until item 49 visible
    ),
    "alert": ActionTestConfig(
        name="alert",
        display_name="Alert",
        deep_link_route="/alert",
        action_type="tap",
        action_position=(0.50, 0.60),  # Calibrated: SHOW ALERT at y=0.60
        action_params={"dismiss_position": (0.75, 0.58)},  # Calibrated: Standard OK location
    ),
}
