"""Verification test cases for device actions."""

from tests.integration.device_verifier.cases.tap_cases import get_tap_cases
from tests.integration.device_verifier.cases.input_cases import get_input_cases
from tests.integration.device_verifier.cases.swipe_cases import get_swipe_cases
from tests.integration.device_verifier.cases.drag_cases import get_drag_cases
from tests.integration.device_verifier.cases.nav_cases import get_nav_cases
from tests.integration.device_verifier.cases.test_app_cases import get_test_app_cases

__all__ = [
    'get_tap_cases',
    'get_input_cases',
    'get_swipe_cases',
    'get_drag_cases',
    'get_nav_cases',
    'get_test_app_cases',
]


def get_all_cases():
    """Get all verification test cases.

    Returns:
        List of all VerificationCase objects
    """
    all_cases = []
    all_cases.extend(get_tap_cases())
    all_cases.extend(get_input_cases())
    all_cases.extend(get_swipe_cases())
    all_cases.extend(get_drag_cases())
    all_cases.extend(get_nav_cases())
    all_cases.extend(get_test_app_cases())
    return all_cases
