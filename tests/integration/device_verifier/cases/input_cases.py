"""Input action verification cases for device interaction testing."""

from typing import List

from tests.integration.device_verifier.models import (
    VerificationCase,
    ActionType,
)


def get_input_cases() -> List[VerificationCase]:
    """Get all input-related verification cases.

    Returns:
        List of VerificationCase objects for input actions
    """
    return [
        # T009: Input text verification
        VerificationCase(
            name="test_input_full_name",
            description="Verify text input in Full Name field using coordinates",
            action_type=ActionType.INPUT,
            target_element={},
            expected_result={"element_found": True},
            coordinates=(540, 600),
            test_data={"text": "Test User"},
        ),
        VerificationCase(
            name="test_input_email",
            description="Verify text input in Email Address field using coordinates",
            action_type=ActionType.INPUT,
            target_element={},
            expected_result={"element_found": True},
            coordinates=(540, 800),
            test_data={"text": "test@example.com"},
        ),
        VerificationCase(
            name="test_input_password",
            description="Verify text input in Password field using coordinates",
            action_type=ActionType.INPUT,
            target_element={},
            expected_result={"element_found": True},
            coordinates=(540, 1000),
            test_data={"text": "password123"},
        ),
    ]
