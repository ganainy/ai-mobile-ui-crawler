# Data Model: Test App Action Verification

**Date**: 2026-01-12
**Branch**: `007-test-app-actions-verify`

## Entities

### ActionTestConfig

Represents the configuration for a single action verification test.

```python
from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, Optional

@dataclass
class ActionTestConfig:
    """Configuration for a single action verification test."""
    
    # Unique identifier matching test function name (without test_ prefix)
    name: str
    
    # Display name for logging
    display_name: str
    
    # Coordinates (relative 0.0-1.0) to tap on the hub screen
    tile_position: Tuple[float, float]
    
    # Action type to perform
    action_type: str  # "tap", "double_tap", "long_press", "swipe", "drag", "scroll", "input"
    
    # Coordinates (relative 0.0-1.0) where to perform the action
    action_position: Tuple[float, float] = (0.5, 0.5)
    
    # End coordinates for swipe/drag actions (relative 0.0-1.0)
    action_end_position: Optional[Tuple[float, float]] = None
    
    # Additional action parameters
    action_params: Dict[str, Any] = field(default_factory=dict)
    
    # Text to search for to confirm success
    success_text: str = "Success"
    
    # Timeout for success text detection (seconds)
    timeout_seconds: int = 5
    
    def get_tile_coords(self, screen_width: int, screen_height: int) -> Tuple[int, int]:
        """Convert relative tile position to absolute pixel coordinates."""
        return (
            int(screen_width * self.tile_position[0]),
            int(screen_height * self.tile_position[1])
        )
    
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
```

### ActionTestResult

Represents the result of executing an action verification test.

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class TestStatus(Enum):
    """Status of a test execution."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

@dataclass
class ActionTestResult:
    """Result of an action verification test."""
    
    # Name of the test
    test_name: str
    
    # Test status
    status: TestStatus
    
    # Execution timestamp
    timestamp: datetime
    
    # Duration in seconds
    duration_seconds: float
    
    # Error message if failed/error
    error_message: Optional[str] = None
    
    # Screenshot path if captured
    screenshot_path: Optional[str] = None
    
    # OCR detected text (for debugging)
    detected_text: Optional[str] = None
```

## Pre-Defined Configurations

All 14 action test configurations:

```python
ACTION_CONFIGS: Dict[str, ActionTestConfig] = {
    # Row 1
    "tap": ActionTestConfig(
        name="tap",
        display_name="Tap",
        tile_position=(0.25, 0.12),
        action_type="tap",
        action_position=(0.5, 0.5),
    ),
    "double_tap": ActionTestConfig(
        name="double_tap",
        display_name="Double Tap",
        tile_position=(0.75, 0.12),
        action_type="double_tap",
        action_position=(0.5, 0.5),
    ),
    
    # Row 2
    "long_press": ActionTestConfig(
        name="long_press",
        display_name="Long Press",
        tile_position=(0.25, 0.20),
        action_type="long_press",
        action_position=(0.5, 0.5),
        action_params={"duration": 2.0},
    ),
    "drag_drop": ActionTestConfig(
        name="drag_drop",
        display_name="Drag & Drop",
        tile_position=(0.75, 0.20),
        action_type="drag",
        action_position=(0.5, 0.35),
        action_end_position=(0.5, 0.65),
    ),
    
    # Row 3
    "swipe": ActionTestConfig(
        name="swipe",
        display_name="Swipe",
        tile_position=(0.25, 0.28),
        action_type="swipe",
        action_position=(0.8, 0.5),
        action_end_position=(0.2, 0.5),
    ),
    "input": ActionTestConfig(
        name="input",
        display_name="Input",
        tile_position=(0.75, 0.28),
        action_type="input",
        action_position=(0.5, 0.4),
        action_params={"text": "Hello Appium"},
    ),
    
    # Row 4
    "slider": ActionTestConfig(
        name="slider",
        display_name="Slider",
        tile_position=(0.25, 0.36),
        action_type="swipe",
        action_position=(0.2, 0.5),
        action_end_position=(0.8, 0.5),
    ),
    "switch": ActionTestConfig(
        name="switch",
        display_name="Switch",
        tile_position=(0.75, 0.36),
        action_type="tap",
        action_position=(0.5, 0.5),
    ),
    
    # Row 5
    "checkbox": ActionTestConfig(
        name="checkbox",
        display_name="Checkbox",
        tile_position=(0.25, 0.44),
        action_type="tap",
        action_position=(0.5, 0.5),
    ),
    "radio": ActionTestConfig(
        name="radio",
        display_name="Radio",
        tile_position=(0.75, 0.44),
        action_type="tap",
        action_position=(0.5, 0.5),
    ),
    
    # Row 6
    "dropdown": ActionTestConfig(
        name="dropdown",
        display_name="Dropdown",
        tile_position=(0.25, 0.52),
        action_type="tap",  # Will need additional tap for selection
        action_position=(0.5, 0.4),
        action_params={"select_position": (0.5, 0.55)},
    ),
    "stepper": ActionTestConfig(
        name="stepper",
        display_name="Stepper",
        tile_position=(0.75, 0.52),
        action_type="tap",
        action_position=(0.65, 0.5),  # Tap + button
    ),
    
    # Row 7
    "scroll": ActionTestConfig(
        name="scroll",
        display_name="Scroll",
        tile_position=(0.25, 0.60),
        action_type="scroll",
        action_position=(0.5, 0.7),
        action_end_position=(0.5, 0.3),
        action_params={"direction": "up", "distance": 500},
    ),
    "alert": ActionTestConfig(
        name="alert",
        display_name="Alert",
        tile_position=(0.75, 0.60),
        action_type="tap",
        action_position=(0.5, 0.5),
        action_params={"dismiss_position": (0.5, 0.55)},
    ),
}
```

## Relationships

```
ActionTestConfig 1 --- 1 test_* function (mapping via name)
ActionTestConfig 1 --- * ActionTestResult (one per execution)
```

## Validation Rules

1. **name**: Must be a valid Python identifier, lowercase with underscores
2. **tile_position**: Both values must be in range [0.0, 1.0]
3. **action_position**: Both values must be in range [0.0, 1.0]
4. **action_end_position**: If set, both values must be in range [0.0, 1.0]
5. **action_type**: Must be one of: "tap", "double_tap", "long_press", "swipe", "drag", "scroll", "input"
6. **timeout_seconds**: Must be positive integer >= 1

## State Transitions

```
Test Execution Flow:
┌─────────────────┐
│  NOT_STARTED    │
└────────┬────────┘
         │ restart_app()
         ▼
┌─────────────────┐
│  APP_RESTARTED  │
└────────┬────────┘
         │ tap_tile()
         ▼
┌─────────────────┐
│  ON_ACTION_PAGE │
└────────┬────────┘
         │ perform_action()
         ▼
┌─────────────────┐
│  ACTION_DONE    │
└────────┬────────┘
         │ verify_success()
         ▼
┌─────────────────┐      ┌─────────────┐
│     PASSED      │  or  │   FAILED    │
└─────────────────┘      └─────────────┘
```
