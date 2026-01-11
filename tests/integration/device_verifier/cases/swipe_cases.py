"""Swipe action verification cases for device interaction testing."""

from typing import List

from tests.integration.device_verifier.models import (
    VerificationCase,
    ActionType,
)


def get_swipe_cases() -> List[VerificationCase]:
    """Get all swipe-related verification cases.

    Returns:
        List of VerificationCase objects for swipe actions
    """
    return [
        # T010: Swipe/Scroll verification
        VerificationCase(
            name="test_swipe_up",
            description="Verify swipe up gesture works correctly",
            action_type=ActionType.SWIPE,
            target_element={},
            expected_result={"element_found": True},
            test_data={
                "start_x": 540,
                "start_y": 1500,
                "end_x": 540,
                "end_y": 500,
                "duration": 500,
            },
        ),
        VerificationCase(
            name="test_swipe_down",
            description="Verify swipe down gesture works correctly",
            action_type=ActionType.SWIPE,
            target_element={},
            expected_result={"element_found": True},
            test_data={
                "start_x": 540,
                "start_y": 500,
                "end_x": 540,
                "end_y": 1500,
                "duration": 500,
            },
        ),
        VerificationCase(
            name="test_swipe_left",
            description="Verify swipe left gesture works correctly",
            action_type=ActionType.SWIPE,
            target_element={},
            expected_result={"element_found": True},
            test_data={
                "start_x": 900,
                "start_y": 1000,
                "end_x": 200,
                "end_y": 1000,
                "duration": 500,
            },
        ),
        VerificationCase(
            name="test_swipe_right",
            description="Verify swipe right gesture works correctly",
            action_type=ActionType.SWIPE,
            target_element={},
            expected_result={"element_found": True},
            test_data={
                "start_x": 200,
                "start_y": 1000,
                "end_x": 900,
                "end_y": 1000,
                "duration": 500,
            },
        ),
    ]
