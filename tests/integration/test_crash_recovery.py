import pytest
import time
from unittest.mock import MagicMock, patch
from selenium.common.exceptions import WebDriverException

from mobile_crawler.core.crawler_loop import CrawlerLoop
from mobile_crawler.domain.models import AIAction, AIResponse, ActionResult, BoundingBox
from mobile_crawler.core.uiautomator_recovery import RecoveryConfig

class MockError(WebDriverException):
    def __init__(self, msg):
        super().__init__(msg)

def test_recovery_from_single_crash():
    """Verify that CrawlerLoop recovers from a single crash and retries the action."""
    
    # Setup mocks
    mock_state_machine = MagicMock()
    mock_screenshot_capture = MagicMock()
    mock_ai_service = MagicMock()
    mock_action_executor = MagicMock()
    mock_step_repo = MagicMock()
    mock_run_repo = MagicMock()
    mock_config = MagicMock()
    mock_driver = MagicMock()
    mock_screen_tracker = MagicMock()
    mock_session_manager = MagicMock()
    
    # Mock config values
    mock_config.get.side_effect = lambda key, default: default
    
    # Mock capture_full
    mock_image = MagicMock()
    mock_image.size = (1080, 1920)
    mock_screenshot_capture.capture_full.return_value = (mock_image, "fake_path", "fake_b64", 1.0)
    
    # Mock AI response with one click action
    ai_action = AIAction(
        action="click", 
        action_desc="Click button", 
        reasoning="test",
        target_bounding_box=BoundingBox(top_left=(100, 100), bottom_right=(200, 200))
    )
    ai_response = AIResponse(actions=[ai_action], signup_completed=False, latency_ms=100)
    mock_ai_service.get_next_actions.return_value = ai_response

    # Mock ScreenTracker methods
    mock_screen_state = MagicMock()
    mock_screen_state.screen_id = "screen_1"
    mock_screen_state.is_new = True
    mock_screen_state.visit_count = 1
    mock_screen_state.total_screens_discovered = 1
    mock_screen_tracker.process_screen.return_value = mock_screen_state
    mock_screen_tracker.is_stuck.return_value = (False, "")
    
    # Create CrawlerLoop
    loop = CrawlerLoop(
        mock_state_machine,
        mock_screenshot_capture,
        mock_ai_service,
        mock_action_executor,
        mock_step_repo,
        mock_run_repo,
        mock_config,
        mock_driver,
        mock_screen_tracker,
        mock_session_manager
    )
    
    # Mock grounding manager
    mock_grounding_overlay = MagicMock()
    mock_grounding_overlay.ocr_elements = []
    mock_grounding_overlay.marked_image_path = "fake_path"
    mock_grounding_overlay.label_map = {}
    loop.grounding_manager = MagicMock()
    loop.grounding_manager.process_screenshot.return_value = mock_grounding_overlay
    
    # Force target package for activation test
    loop._target_package = "com.test.app"
    
    # Setup action executor to fail once with crash then succeed
    crash_error = MockError("instrumentation process is not running")
    success_result = ActionResult(success=True, action_type="click", target="[100, 100, 200, 200]")
    
    mock_action_executor.click.side_effect = [crash_error, success_result]
    
    # Mock open and base64 for grounding screenshot
    with patch("builtins.open", MagicMock()):
        with patch("base64.b64encode", return_value=b"fake_b64_grounded"):
            # Execute step 1
            with patch.object(loop, '_ensure_app_foreground', return_value=True):
                with patch.object(loop, '_emit_event') as mock_emit:
                    success = loop._execute_step(run_id=1, step_number=1)
                    
                    # Assertions
                    assert success is True
                    assert mock_action_executor.click.call_count == 2
                    assert mock_driver.restart_uiautomator2.call_count == 1
                    
                    # Verify events
                    event_names = [call[0][0] for call in mock_emit.call_args_list]
                    assert "on_recovery_started" in event_names
                    assert "on_recovery_completed" in event_names
                    assert "on_action_executed" in event_names
                    
                    # Verify app activation after recovery
                    mock_driver.get_driver().activate_app.assert_called_with("com.test.app")

def test_recovery_exhausted():
    """Verify that CrawlerLoop stops after max recovery attempts are exhausted."""
    
    # Setup mocks
    mock_state_machine = MagicMock()
    mock_screenshot_capture = MagicMock()
    mock_ai_service = MagicMock()
    mock_action_executor = MagicMock()
    mock_step_repo = MagicMock()
    mock_run_repo = MagicMock()
    mock_config = MagicMock()
    mock_driver = MagicMock()
    mock_screen_tracker = MagicMock()
    mock_session_manager = MagicMock()
    
    # Mock config values (max 2 attempts)
    mock_config.get.side_effect = lambda key, default: 2 if key == 'uiautomator2_max_recovery_attempts' else default
    
    # Mock capture_full
    mock_image = MagicMock()
    mock_image.size = (1080, 1920)
    mock_screenshot_capture.capture_full.return_value = (mock_image, "fake_path", "fake_b64", 1.0)
    
    # Mock AI response with one click action
    ai_action = AIAction(
        action="click", 
        action_desc="Click button", 
        reasoning="test",
        target_bounding_box=BoundingBox(top_left=(100, 100), bottom_right=(200, 200))
    )
    ai_response = AIResponse(actions=[ai_action], signup_completed=False, latency_ms=100)
    mock_ai_service.get_next_actions.return_value = ai_response

    # Mock ScreenTracker methods
    mock_screen_state = MagicMock()
    mock_screen_state.screen_id = "screen_1"
    mock_screen_tracker.process_screen.return_value = mock_screen_state
    mock_screen_tracker.is_stuck.return_value = (False, "")
    
    # Create CrawlerLoop
    loop = CrawlerLoop(
        mock_state_machine,
        mock_screenshot_capture,
        mock_ai_service,
        mock_action_executor,
        mock_step_repo,
        mock_run_repo,
        mock_config,
        mock_driver,
        mock_screen_tracker,
        mock_session_manager
    )
    
    # Setup action executor to ALWAYS fail with crash
    crash_error = MockError("instrumentation process is not running")
    mock_action_executor.click.side_effect = crash_error
    
    # Mock recovery to fail or just record attempts
    # Restart returns driver again
    mock_driver.restart_uiautomator2.return_value = mock_driver
    
    # Mock grounding manager
    loop.grounding_manager = MagicMock()
    loop.grounding_manager.process_screenshot.return_value = MagicMock()
    
    # Execute step 1
    with patch.object(loop, '_ensure_app_foreground', return_value=True):
        with patch.object(loop, '_emit_event') as mock_emit:
            with patch("builtins.open", MagicMock()):
                with patch("base64.b64encode", return_value=b"fake_b64"):
                    success = loop._execute_step(run_id=1, step_number=1)
                    
                    # Assertions
                    assert success is False
                    assert mock_driver.restart_uiautomator2.call_count == 2
                    assert loop._recovery_failed is True
                    
                    # Verify exhaustion event
                    event_names = [call[0][0] for call in mock_emit.call_args_list]
                    assert "on_recovery_exhausted" in event_names
