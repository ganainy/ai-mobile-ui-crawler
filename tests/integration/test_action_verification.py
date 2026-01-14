"""Integration tests for verifying Appium actions using a dedicated test app.

Updated to use:
- Deep links for direct navigation to action screens (no hub tile clicking)
- Accessibility ID (success_indicator) for reliable success detection (no OCR)
"""

import pytest
import time
import logging
from typing import Tuple

from mobile_crawler.infrastructure.gesture_handler import GestureHandler
from tests.integration.device_verifier.session import DeviceSession
from tests.integration.device_verifier.deep_link_navigator import DeepLinkNavigator
from tests.integration.device_verifier.success_verifier import SuccessVerifier
from tests.integration.device_verifier.action_configs import ACTION_CONFIGS, ActionTestConfig

logger = logging.getLogger(__name__)

# Constants
APP_PACKAGE = "com.example.appium_action_test_app"
MAIN_ACTIVITY = "com.example.appium_action_test_app.MainActivity"


@pytest.fixture(scope="module")
def device_session(android_device):
    """Fixture to manage the DeviceSession."""
    session = DeviceSession(
        device_id=android_device,
        app_package=APP_PACKAGE
    )
    session.connect()
    yield session
    session.disconnect()


@pytest.fixture(scope="module")
def deep_link_navigator(android_device):
    """Fixture for DeepLinkNavigator."""
    return DeepLinkNavigator(
        device_id=android_device,
        app_package=APP_PACKAGE
    )


@pytest.fixture(scope="module")
def success_verifier(device_session):
    """Fixture for SuccessVerifier."""
    return SuccessVerifier(driver=device_session.get_driver())


@pytest.fixture(scope="module")
def gesture_handler(device_session):
    """Fixture for GestureHandler."""
    class DriverWrapper:
        def __init__(self, driver):
            self.driver = driver
        def get_driver(self):
            return self.driver
            
    wrapper = DriverWrapper(device_session.get_driver())
    return GestureHandler(wrapper)


@pytest.fixture(scope="module")
def screen_dims(device_session):
    """Get screen dimensions once per session."""
    return device_session.get_screen_dimensions()


@pytest.fixture(autouse=True)
def setup_before_test():
    """Setup hook before each test - currently just a placeholder."""
    # Note: We don't force-stop the app here because it can break the Appium session
    # Deep link navigation already provides clean navigation to each screen
    pass


def run_action_test(
    config_name: str, 
    device_session, 
    deep_link_navigator: DeepLinkNavigator,
    gesture_handler, 
    success_verifier: SuccessVerifier, 
    screen_dims: Tuple[int, int]
):
    """Common runner logic for action tests using deep links and accessibility ID verification."""
    config: ActionTestConfig = ACTION_CONFIGS[config_name]
    width, height = screen_dims
    
    logger.info(f"Starting test for: {config.display_name}")
    print(f"\n[TEST] Running: {config.display_name}")
    
    # 1. Navigate directly to action screen via deep link
    print(f"[STEP 1] Navigating to {config.deep_link_route} via deep link")
    nav_success = deep_link_navigator.navigate_to(config.deep_link_route)
    assert nav_success, f"Failed to navigate to {config.deep_link_route}"
    
    print("[WAIT] Waiting 0.5s for screen to load...")
    time.sleep(0.5)
    
    # 2. Perform the primary action
    action_x, action_y = config.get_action_coords(width, height)
    print(f"[STEP 2] Performing action '{config.action_type}' at ({action_x}, {action_y}) [Relative: {config.action_position}]")
    
    if config.action_type == "tap":
        gesture_handler.tap_at(action_x, action_y)
    elif config.action_type == "double_tap":
        gesture_handler.double_tap_at(action_x, action_y)
    elif config.action_type == "long_press":
        duration = config.action_params.get("duration", 1.0)
        gesture_handler.long_press_at(action_x, action_y, duration=duration)
    elif config.action_type == "drag":
        end_coords = config.get_action_end_coords(width, height)
        if end_coords:
            print(f"[DRAG] Dragging to ({end_coords[0]}, {end_coords[1]})")
            gesture_handler.drag_from_to(action_x, action_y, end_coords[0], end_coords[1])
    elif config.action_type == "swipe":
        end_coords = config.get_action_end_coords(width, height)
        if end_coords:
            print(f"[SWIPE] Swiping to ({end_coords[0]}, {end_coords[1]})")
            gesture_handler.swipe(action_x, action_y, end_coords[0], end_coords[1])
    elif config.action_type == "scroll":
        direction = config.action_params.get("direction", "down")
        repeat = config.action_params.get("repeat", 1)
        for i in range(repeat):
            print(f"[SCROLL] Scroll {i+1}/{repeat} - {direction}")
            end_coords = config.get_action_end_coords(width, height)
            if end_coords:
                gesture_handler.swipe(action_x, action_y, end_coords[0], end_coords[1], duration=300)
            time.sleep(0.3)
    elif config.action_type == "input":
        text = config.action_params.get("text", "test")
        print(f"[INPUT] Tapping field, then typing '{text}'")
        gesture_handler.tap_at(action_x, action_y)
        time.sleep(0.5)
        # Use ADB input method which is more reliable
        import subprocess
        driver = device_session.get_driver()
        try:
            driver.execute_script('mobile: type', {'text': text})
        except Exception:
            # Fallback to ADB shell input
            device_id = device_session.device_id
            subprocess.run(['adb', '-s', device_id, 'shell', 'input', 'text', text], timeout=10)
    
    # Handle repeat parameter for stepper
    repeat = config.action_params.get("repeat", 1)
    if repeat > 1 and config.action_type == "tap":
        for i in range(1, repeat):  # Already did first tap
            print(f"[TAP] Repeat {i+1}/{repeat}")
            time.sleep(0.2)
            gesture_handler.tap_at(action_x, action_y)
    
    # 2b. Secondary action (e.g., dropdown selection)
    select_pos = config.action_params.get("select_position")
    if select_pos:
        print(f"[STEP 2b] Waiting for popup, tapping at {select_pos}")
        time.sleep(1.0)
        sel_x = int(width * select_pos[0])
        sel_y = int(height * select_pos[1])
        gesture_handler.tap_at(sel_x, sel_y)
    
    # 2c. Dismiss action (e.g., alert dismissal)
    dismiss_pos = config.action_params.get("dismiss_position")
    if dismiss_pos:
        print(f"[STEP 2c] Waiting for dialog, tapping dismiss at {dismiss_pos}")
        time.sleep(1.5)
        dis_x = int(width * dismiss_pos[0])
        dis_y = int(height * dismiss_pos[1])
        gesture_handler.tap_at(dis_x, dis_y)
    
    # 3. Verify success_indicator accessibility ID appears
    print("[STEP 3] Verifying success...")
    time.sleep(0.5)  # Brief wait for success state
    success = success_verifier.wait_for_success(timeout=config.timeout_seconds)
    
    if success:
        print("[RESULT] [SUCCESS] success_indicator found!")
    else:
        # Get status for debugging
        status = success_verifier.get_status_text()
        print(f"[RESULT] [FAILURE] success_indicator NOT found. Current status: {status}")
        
    assert success, f"success_indicator not found for {config_name}"


@pytest.mark.integration
def test_tap(device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify single tap action."""
    run_action_test("tap", device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims)


@pytest.mark.integration
def test_double_tap(device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify double tap action."""
    run_action_test("double_tap", device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims)


@pytest.mark.integration
def test_long_press(device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify long press action."""
    run_action_test("long_press", device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims)


@pytest.mark.integration
def test_drag_drop(device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify drag and drop action."""
    run_action_test("drag_drop", device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims)


@pytest.mark.integration
def test_swipe(device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify swipe action."""
    run_action_test("swipe", device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims)


@pytest.mark.integration
def test_scroll(device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify scroll action."""
    run_action_test("scroll", device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims)


@pytest.mark.integration
def test_input(device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify text input action."""
    run_action_test("input", device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims)


@pytest.mark.integration
def test_slider(device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify slider interaction."""
    run_action_test("slider", device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims)


@pytest.mark.integration
def test_switch(device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify switch interaction."""
    run_action_test("switch", device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims)


@pytest.mark.integration
def test_checkbox(device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify checkbox interaction."""
    run_action_test("checkbox", device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims)


@pytest.mark.integration
def test_radio(device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify radio button interaction."""
    run_action_test("radio", device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims)


@pytest.mark.integration
def test_dropdown(device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify dropdown selection."""
    run_action_test("dropdown", device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims)


@pytest.mark.integration
def test_stepper(device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify stepper interaction."""
    run_action_test("stepper", device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims)


@pytest.mark.integration
def test_alert(device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims):
    """Verify alert trigger and dismissal."""
    run_action_test("alert", device_session, deep_link_navigator, gesture_handler, success_verifier, screen_dims)
