import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
from mobile_crawler.core.crawler_loop import CrawlerLoop
from mobile_crawler.domain.models import AIAction, AIResponse, BoundingBox
from mobile_crawler.domain.grounding.dtos import GroundingOverlay

class TestCrawlerLoopAnnotation:
    """Test the annotation logic in CrawlerLoop."""

    @pytest.fixture
    def crawler_dependencies(self):
        """Setup mock dependencies for CrawlerLoop."""
        deps = {
            'crawl_state_machine': Mock(),
            'screenshot_capture': Mock(),
            'ai_interaction_service': Mock(),
            'action_executor': Mock(),
            'step_log_repository': Mock(),
            'run_repository': Mock(),
            'config_manager': Mock(),
            'appium_driver': Mock(),
            'screen_tracker': Mock(),
            'session_folder_manager': Mock(),
            'top_bar_height': 0
        }
        # Config manager defaults: return 0 for top_bar_height to avoid unexpected cropping logic
        deps['config_manager'].get.side_effect = lambda key, default=None: 0 if key == 'top_bar_height' else 10
        return deps

    def test_annotation_resolves_label_id(self, crawler_dependencies):
        """Test that label_id is resolved to bounding box for annotation."""
        # 1. Setup Crawler
        crawler = CrawlerLoop(**crawler_dependencies)
        crawler.overlay_renderer = Mock()
        crawler.grounding_manager = Mock()
        
        # 2. Mock state and environment
        run_id = 1
        step_number = 1
        crawler._target_package = "com.test"
        
        # Mock screenshot capture
        mock_image = Image.new('RGB', (1000, 2000))
        crawler.screenshot_capture.capture_full.return_value = (mock_image, "/tmp/test.png", "b64", 1.0)
        crawler.screenshot_capture.capture_screenshot.return_value = mock_image
        
        # Mock screen tracker
        crawler.screen_tracker.process_screen.return_value = Mock(screen_id=1, is_new=True, visit_count=1, total_screens_discovered=1)
        crawler.screen_tracker.is_stuck.return_value = (False, None)
        
        # 3. Mock Grounding Data (Label [5] -> [10, 20, 110, 120])
        mock_grounding = MagicMock(spec=GroundingOverlay)
        mock_grounding.ocr_elements = [
            {"label": 5, "text": "Login", "bounds": [10, 20, 110, 120]},
            {"label": 10, "text": "Cancel", "bounds": [200, 300, 250, 350]}
        ]
        mock_grounding.label_map = {5: (60, 70), 10: (225, 325)}
        mock_grounding.marked_image_path = "/tmp/marked.png"
        crawler.grounding_manager.process_screenshot.return_value = mock_grounding
        
        # Mock open() for grounded image base64 conversion
        with patch("builtins.open", MagicMock()):
            with patch("base64.b64encode", return_value=b"grounded_b64"):
                
                # 4. Mock AI Response with ONLY label_id
                ai_response = AIResponse(
                    actions=[
                        AIAction(
                            action="click",
                            action_desc="Click Login",
                            label_id=5,
                            target_bounding_box=None,
                            reasoning="Need to login"
                        )
                    ],
                    signup_completed=False
                )
                crawler.ai_interaction_service.get_next_actions.return_value = ai_response
                
                # 5. Mock app foreground check
                with patch.object(CrawlerLoop, "_ensure_app_foreground", return_value=True):
                    # 6. Execute step
                    crawler._execute_step(run_id, step_number)
                    
                    # 7. Verify overlay_renderer.save_annotated call
                    # It should be called with actions containing the resolved bounding box
                    args, kwargs = crawler.overlay_renderer.save_annotated.call_args
                    actions_passed = kwargs['actions']
                    
                    assert len(actions_passed) == 1
                    action = actions_passed[0]
                    assert action["label_id"] == 5
                    assert "target_bounding_box" in action
                    assert action["target_bounding_box"]["top_left"] == [10, 20]
                    assert action["target_bounding_box"]["bottom_right"] == [110, 120]

    def test_annotation_prioritizes_ai_bounding_box(self, crawler_dependencies):
        """Test that explicit AI bounding box is prioritized over label resolution."""
        crawler = CrawlerLoop(**crawler_dependencies)
        crawler.overlay_renderer = Mock()
        crawler.grounding_manager = Mock()
        
        run_id = 1
        step_number = 1
        crawler._target_package = "com.test"
        
        mock_image = Image.new('RGB', (1000, 2000))
        crawler.screenshot_capture.capture_full.return_value = (mock_image, "/tmp/test.png", "b64", 1.0)
        crawler.screen_tracker.process_screen.return_value = Mock(screen_id=1, is_new=True, visit_count=1, total_screens_discovered=1)
        crawler.screen_tracker.is_stuck.return_value = (False, None)
        
        # Grounding has label 5 at [10, 20, 110, 120]
        mock_grounding = MagicMock(spec=GroundingOverlay)
        mock_grounding.ocr_elements = [{"label": 5, "text": "Login", "bounds": [10, 20, 110, 120]}]
        mock_grounding.label_map = {5: (60, 70)}
        mock_grounding.marked_image_path = "/tmp/marked.png"
        crawler.grounding_manager.process_screenshot.return_value = mock_grounding
        
        with patch("builtins.open", MagicMock()):
            with patch("base64.b64encode", return_value=b"grounded_b64"):
                
                # AI provides BOTH label 5 AND explicit coords [50, 50, 60, 60]
                ai_response = AIResponse(
                    actions=[
                        AIAction(
                            action="click",
                            action_desc="Click Login",
                            label_id=5,
                            target_bounding_box=BoundingBox(top_left=(50, 50), bottom_right=(60, 60)),
                            reasoning="Need to login"
                        )
                    ],
                    signup_completed=False
                )
                crawler.ai_interaction_service.get_next_actions.return_value = ai_response
                
                with patch.object(CrawlerLoop, "_ensure_app_foreground", return_value=True):
                    crawler._execute_step(run_id, step_number)
                    
                    args, kwargs = crawler.overlay_renderer.save_annotated.call_args
                    actions_passed = kwargs['actions']
                    
                    # Should use AI's explicit box [50, 50, 60, 60], NOT grounded box [10, 20, 110, 120]
                    assert actions_passed[0]["target_bounding_box"]["top_left"] == [50, 50]
                    assert actions_passed[0]["target_bounding_box"]["bottom_right"] == [60, 60]
