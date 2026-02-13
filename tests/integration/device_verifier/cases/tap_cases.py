"""Tap action verification cases for device interaction testing."""

from typing import List

from tests.integration.device_verifier.models import (
    VerificationCase,
    ActionType,
)


def get_tap_cases() -> List[VerificationCase]:
    """Get all tap-related verification cases.

    Returns:
        List of VerificationCase objects for tap actions
    """
    return [
        # T006: Single Tap verification
        VerificationCase(
            name="test_single_tap_coordinates",
            description="Verify single tap using coordinates works correctly",
            action_type=ActionType.TAP,
            target_element={},
            expected_result={"element_found": True},
            coordinates=(540, 1200),  # Approximate center of screen
        ),
        # T007: Double Tap verification
        VerificationCase(
            name="test_double_tap_coordinates",
            description="Verify double tap using coordinates works correctly",
            action_type=ActionType.TAP,
            target_element={},
            expected_result={"element_found": True},
            coordinates=(540, 1200),
            test_data={"tap_count": 2},
        ),
        # T008: Long Press verification
        VerificationCase(
            name="test_long_press_coordinates",
            description="Verify long press using coordinates works correctly",
            action_type=ActionType.TAP,
            target_element={},
            expected_result={"element_found": True},
            coordinates=(540, 1200),
            test_data={"press_duration": 1000},  # 1 second long press
        ),
    ]
