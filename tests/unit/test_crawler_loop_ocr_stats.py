"""Unit tests for CrawlerLoop OCR statistics accumulation."""
import pytest
from unittest.mock import Mock, patch, ANY, mock_open
from mobile_crawler.core.crawler_loop import CrawlerLoop
from mobile_crawler.core.crawl_state_machine import CrawlState

class TestCrawlerLoopOCRStats:
    @pytest.fixture
    def mock_deps(self):
        deps = {
            "crawl_state_machine": Mock(),
            "screenshot_capture": Mock(),
            "ai_interaction_service": Mock(),
            "action_executor": Mock(),
            "step_log_repository": Mock(),
            "run_repository": Mock(),
            "config_manager": Mock(),
            "appium_driver": Mock(),
            "screen_tracker": Mock(),
            "session_folder_manager": Mock(),
        }
        deps["crawl_state_machine"].state = CrawlState.RUNNING
        return deps

    def test_ocr_stats_accumulation(self, mock_deps):
        """Test that OCR timing is correctly accumulated and averaged."""
        
        # Mock GroundingManager to prevent actual OCR
        with patch('mobile_crawler.core.crawler_loop.GroundingManager') as mock_grounding_class:
            mock_grounding_manager = Mock()
            mock_grounding_class.return_value = mock_grounding_manager
            
            crawler = CrawlerLoop(**mock_deps)
            
            # Setup mocks for internal attributes
            crawler.overlay_renderer = Mock()
            crawler.top_bar_height = 0
            crawler._current_screen_state = Mock(screen_id=1, is_new=True, visit_count=1, total_screens_discovered=1)
            
            # Setup already-mocked dependencies
            mock_img = Mock()
            mock_img.size = (100, 200)
            crawler.screenshot_capture.capture_full.return_value = (mock_img, "/path", "b64", 1.0)
            crawler.screen_tracker.process_screen.return_value = crawler._current_screen_state
            crawler.screen_tracker.is_stuck.return_value = (False, "")
            crawler.ai_interaction_service.get_next_actions.return_value = Mock(actions=[], signup_completed=False, latency_ms=100)
            
            # We need to mock _ensure_app_foreground as it's a method of the class being tested
            with patch.object(CrawlerLoop, "_ensure_app_foreground", return_value=True), \
                 patch.object(CrawlerLoop, "_emit_event"), \
                 patch("builtins.open", mock_open(read_data=b"dummy")), \
                 patch("time.time") as mock_time:
                
                # Step 1 timing sequence:
                # 1. step_start_time = time.time() -> 100.0
                # 2. ocr_start = time.time() -> 100.0
                # 3. ocr_end = time.time() -> 100.1 (Duration 100ms)
                # 4. step_end = time.time() -> 100.2
                
                # Step 2 timing sequence:
                # 5. step_start_time = time.time() -> 200.0
                # 6. ocr_start = time.time() -> 200.0
                # 7. ocr_end = time.time() -> 200.2 (Duration 200ms)
                # 8. step_end = time.time() -> 200.3
                
                mock_time.side_effect = [
                    # Step 1
                    100.0,  # step_start_time
                    100.0,  # screenshot_start
                    100.0,  # screenshot_end (0ms duration)
                    100.0,  # ocr_start
                    100.1,  # ocr_end (100ms duration)
                    100.2,  # step_end
                    # Step 2
                    200.0,  # step_start_time
                    200.0,  # screenshot_start
                    200.0,  # screenshot_end (0ms duration)
                    200.0,  # ocr_start
                    200.2,  # ocr_end (200ms duration)
                    200.3,  # step_end
                ]
                
                mock_grounding = Mock(ocr_elements=[], label_map={}, marked_image_path="/path/marked.png")
                mock_grounding_manager.process_screenshot.return_value = mock_grounding
                
                # Run Step 1
                crawler._execute_step(run_id=1, step_number=1)
                assert crawler._ocr_operation_count == 1
                assert crawler._ocr_total_time_ms == pytest.approx(100.0)
                
                # Run Step 2
                crawler._execute_step(run_id=1, step_number=2)
                assert crawler._ocr_operation_count == 2
                assert crawler._ocr_total_time_ms == pytest.approx(300.0)

    def test_ocr_avg_emitted_in_cleanup(self, mock_deps):
        """Test that average OCR time is correctly calculated and emitted in cleanup."""
        crawler = CrawlerLoop(**mock_deps)
        crawler._ocr_total_time_ms = 500.0
        crawler._ocr_operation_count = 2 # Avg = 250.0
        
        # Patch internal methods that do cleanup
        with patch.object(CrawlerLoop, "_stop_traffic_capture"), \
             patch.object(CrawlerLoop, "_stop_video_recording"), \
             patch.object(CrawlerLoop, "_run_mobsf_analysis"), \
             patch.object(CrawlerLoop, "_update_run_recovery_stats"), \
             patch.object(CrawlerLoop, "_get_completion_reason", return_value="test_reason"), \
             patch.object(crawler, "_emit_event") as mock_emit, \
             patch("time.time", return_value=1000.0):
            
            crawler._recovery_failed = False
            # step_number is 3, so total_steps will be 2
            crawler._cleanup_crawl_session(run_id=1, step_number=3, start_time=0.0, session_path="/tmp")
            
            # Verify average passed to on_crawl_completed
            # Event name + 5 args = 6 total
            # run_id=1, total_steps=2, duration=1000.0*1000, reason="test_reason", ocr_avg=250.0
            mock_emit.assert_any_call("on_crawl_completed", 1, 2, 1000000.0, "test_reason", 250.0)
