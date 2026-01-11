"""Drag action verification cases for device interaction testing."""

from typing import List

from tests.integration.device_verifier.models import (
    VerificationCase,
    ActionType,
)


def get_drag_cases() -> List[VerificationCase]:
    """Get all drag-related verification cases.

    Returns:
        List of VerificationCase objects for drag actions
    """
    return [
        # T011: Drag & Drop verification
        VerificationCase(
            name="test_drag_down",
            description="Verify drag down gesture works correctly",
            action_type=ActionType.DRAG,
            target_element={},
            expected_result={"element_found": True},
            test_data={
                "start_x": 540,
                "start_y": 500,
                "end_x": 540,
                "end_y": 1500,
                "duration": 1000,
            },
        ),
        VerificationCase(
            name="test_drag_up",
            description="Verify drag up gesture works correctly",
            action_type=ActionType.DRAG,
            target_element={},
            expected_result={"element_found": True},
            test_data={
                "start_x": 540,
                "start_y": 1500,
                "end_x": 540,
                "end_y": 500,
                "duration": 1000,
            },
        ),
        VerificationCase(
            name="test_drag_horizontal",
            description="Verify horizontal drag gesture works correctly",
            action_type=ActionType.DRAG,
            target_element={},
            expected_result={"element_found": True},
            test_data={
                "start_x": 200,
                "start_y": 1000,
                "end_x": 900,
                "end_y": 1000,
                "duration": 1000,
            },
        ),
    ]
