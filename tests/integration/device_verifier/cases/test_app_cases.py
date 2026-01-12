"""Verification test cases for the dedicated test app."""

from typing import List

from tests.integration.device_verifier.models import (
    VerificationCase,
    ActionType,
)


def get_test_app_cases() -> List[VerificationCase]:
    """Get all verification cases for the test app.

    Returns:
        List of VerificationCase objects
    """
    cases = []
    # US1: Basic Gestures
    cases.extend([
        VerificationCase(
            name="test_app_tap",
            description="Verify single tap on the test app",
            action_type=ActionType.TAP,
            target_element={},  # Global tap
            expected_result={"text_visible": "Success"},
            test_data={"url": "myapp://tap"},
            coordinates=(540, 1200),
        ),
        VerificationCase(
            name="test_app_double_tap",
            description="Verify double tap on the test app",
            action_type=ActionType.TAP,
            target_element={},
            expected_result={"text_visible": "Success"},
            test_data={"url": "myapp://double_tap", "tap_count": 2},
            coordinates=(540, 1200),
        ),
        VerificationCase(
            name="test_app_long_press",
            description="Verify long press on the test app",
            action_type=ActionType.TAP,
            target_element={},
            expected_result={"text_visible": "Success"},
            test_data={"url": "myapp://long_press", "press_duration": 1000},
            coordinates=(540, 1200),
        ),
    ])
    
    # US2: Movement Gestures
    cases.extend([
        VerificationCase(
            name="test_app_drag_drop",
            description="Verify drag and drop on the test app",
            action_type=ActionType.DRAG,
            target_element={},
            expected_result={"text_visible": "Success"},
            test_data={
                "url": "myapp://drag_drop",
                "end_coordinates": (540, 1600)
            },
            coordinates=(540, 800),
        ),
        VerificationCase(
            name="test_app_swipe",
            description="Verify swipe on the test app",
            action_type=ActionType.SWIPE,
            target_element={},
            expected_result={"text_visible": "Success"},
            test_data={
                "url": "myapp://swipe",
                "end_coordinates": (100, 1200)
            },
            coordinates=(900, 1200),
        ),
        VerificationCase(
            name="test_app_scroll",
            description="Verify scroll on the test app",
            action_type=ActionType.SWIPE,
            target_element={},
            expected_result={"text_visible": "Success"},
            test_data={
                "url": "myapp://scroll",
                "direction": "down",
                "distance": 800
            },
            coordinates=(540, 1500),
        ),
    ])
    
    # US3: Form Interactions
    cases.extend([
        VerificationCase(
            name="test_app_input",
            description="Verify text input on the test app",
            action_type=ActionType.INPUT,
            target_element={},
            expected_result={"text_visible": "Success"},
            test_data={"url": "myapp://input_test", "text": "Appium Test"},
        ),
        VerificationCase(
            name="test_app_slider",
            description="Verify slider interaction on the test app",
            action_type=ActionType.SWIPE,
            target_element={},
            expected_result={"text_visible": "Success"},
            test_data={"url": "myapp://slider", "value": 0.8, "end_coordinates": (900, 1000)},
            coordinates=(200, 1000),
        ),
        VerificationCase(
            name="test_app_switch",
            description="Verify switch interaction on the test app",
            action_type=ActionType.TAP,
            target_element={},
            expected_result={"text_visible": "Success"},
            test_data={"url": "myapp://switch"},
            coordinates=(540, 1000),
        ),
        VerificationCase(
            name="test_app_checkbox",
            description="Verify checkbox interaction on the test app",
            action_type=ActionType.TAP,
            target_element={},
            expected_result={"text_visible": "Success"},
            test_data={"url": "myapp://checkbox"},
            coordinates=(540, 1000),
        ),
        VerificationCase(
            name="test_app_radio",
            description="Verify radio button interaction on the test app",
            action_type=ActionType.TAP,
            target_element={},
            expected_result={"text_visible": "Success"},
            test_data={"url": "myapp://radio"},
            coordinates=(540, 1000),
        ),
        VerificationCase(
            name="test_app_dropdown",
            description="Verify dropdown interaction on the test app",
            action_type=ActionType.TAP,
            target_element={},
            expected_result={"text_visible": "Success"},
            test_data={"url": "myapp://dropdown"},
            coordinates=(540, 1000),
        ),
        VerificationCase(
            name="test_app_stepper",
            description="Verify stepper interaction on the test app",
            action_type=ActionType.TAP,
            target_element={},
            expected_result={"text_visible": "Success"},
            test_data={"url": "myapp://stepper"},
            coordinates=(800, 1000), # Tap the '+' button
        ),
    ])
    
    # US4: Dialog Interactions
    cases.extend([
        VerificationCase(
            name="test_app_alert",
            description="Verify alert interaction on the test app",
            action_type=ActionType.TAP,
            target_element={},
            expected_result={"text_visible": "Success"},
            test_data={"url": "myapp://alert"},
            coordinates=(540, 1000), # Tap button to trigger alert
        ),
    ])
    
    return cases
