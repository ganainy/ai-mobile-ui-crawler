"""Navigation action verification cases for device interaction testing."""

from typing import List

from tests.integration.device_verifier.models import (
    VerificationCase,
    ActionType,
)


def get_nav_cases() -> List[VerificationCase]:
    """Get all navigation-related verification cases.

    Returns:
        List of VerificationCase objects for navigation actions
    """
    return [
        # T012: Back navigation verification
        VerificationCase(
            name="test_back_navigation",
            description="Verify back navigation works correctly",
            action_type=ActionType.NAVIGATE,
            target_element={},
            expected_result={"element_found": True},
            test_data={"action": "back"},
        ),
    ]
