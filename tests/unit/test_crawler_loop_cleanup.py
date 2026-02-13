"""Unit tests for CrawlerLoop graceful cleanup behavior."""
import pytest
from unittest.mock import Mock, patch, ANY
from mobile_crawler.core.crawler_loop import CrawlerLoop
from mobile_crawler.core.crawl_state_machine import CrawlState

class TestCrawlerLoopCleanup:
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
        deps["session_folder_manager"].create_session_folder.return_value = "/tmp/session"
        deps["session_folder_manager"].get_subfolder.return_value = "/tmp/session/sub"
        
        mock_run = Mock()
        mock_run.app_package = "com.test.app"
        deps["run_repository"].get_run_by_id.return_value = mock_run
        
        return deps

    def test_cleanup_called_in_finally_block(self, mock_deps):
        """Test that _cleanup_crawl_session is called even if run() raises an exception."""
        crawler = CrawlerLoop(**mock_deps)
        
        with patch.object(CrawlerLoop, "_ensure_app_foreground", side_effect=Exception("Crash!")), \
             patch.object(CrawlerLoop, "_cleanup_crawl_session") as mock_cleanup:
            
            with pytest.raises(Exception):
                crawler.run(1)
            
            # Verify cleanup was called exactly once
            mock_cleanup.assert_called_once()

    def test_cleanup_methods_executed(self, mock_deps):
        """Test that specific cleanup actions are performed in _cleanup_crawl_session."""
        crawler = CrawlerLoop(**mock_deps)
        
        # Setup for cleanup
        crawler._mobsf_manager = Mock()
        crawler._recovery_failed = False
        
        with patch.object(CrawlerLoop, "_stop_traffic_capture") as mock_stop_traffic, \
             patch.object(CrawlerLoop, "_stop_video_recording") as mock_stop_video, \
             patch.object(CrawlerLoop, "_run_mobsf_analysis") as mock_mobsf, \
             patch.object(CrawlerLoop, "_emit_event") as mock_emit:
            
            crawler._cleanup_crawl_session(run_id=1, step_number=5, start_time=100.0, session_path="/tmp")
            
            # Verify stops called
            mock_stop_traffic.assert_called_once_with(1, 5)
            mock_stop_video.assert_called_once()
            
            # Verify MobSF called
            mock_mobsf.assert_called_once_with(1, "/tmp")
            
            # Verify final states
            mock_deps["crawl_state_machine"].transition_to.assert_any_call(CrawlState.STOPPED)
            
            # Verify completion event
            mock_emit.assert_any_call("on_crawl_completed", 1, 4, ANY, ANY, ANY)

    def test_cleanup_skips_mobsf_on_manual_stop(self, mock_deps):
        """Test that MobSF analysis is skipped if crawler was stopped early."""
        crawler = CrawlerLoop(**mock_deps)
        
        # Simulate manual stop
        crawler._mobsf_manager = Mock()
        crawler.stop()
        
        with patch.object(CrawlerLoop, "_stop_traffic_capture"), \
             patch.object(CrawlerLoop, "_stop_video_recording"), \
             patch.object(CrawlerLoop, "_run_mobsf_analysis") as mock_mobsf:
            
            crawler._cleanup_crawl_session(run_id=1, step_number=5, start_time=100.0, session_path="/tmp")
            
            # Verify MobSF was NOT called
            mock_mobsf.assert_not_called()
