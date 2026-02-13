"""Unit tests for CrawlerLoop configuration and timer behavior."""
import pytest
import time
from unittest.mock import Mock, patch
from mobile_crawler.core.crawler_loop import CrawlerLoop
from mobile_crawler.core.crawl_state_machine import CrawlState

class TestCrawlerLoopConfig:
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
        # Default config behavior
        deps["config_manager"].get.side_effect = lambda key, default=None: {
            "max_crawl_steps": 10,
            "max_crawl_duration_seconds": 300,
        }.get(key, default)
        
        deps["session_folder_manager"].create_session_folder.return_value = "/tmp/session"
        deps["session_folder_manager"].get_subfolder.return_value = "/tmp/session/sub"
        
        # Mock run repo to return a mock run
        mock_run = Mock()
        mock_run.app_package = "com.test.app"
        deps["run_repository"].get_run_by_id.return_value = mock_run
        
        return deps

    def test_config_read_at_run_time(self, mock_deps):
        """Test that max_steps and max_duration are read during run(), not just __init__."""
        crawler = CrawlerLoop(**mock_deps)
        
        # Initial values from __init__ (defaults I set in multi_replace_file_content)
        assert crawler.max_crawl_steps == 15
        assert crawler.max_crawl_duration_seconds == 600
        
        # Change config values before run
        mock_deps["config_manager"].get.side_effect = lambda key, default=None: {
            "max_crawl_steps": 25,
            "max_crawl_duration_seconds": 1200,
        }.get(key, default)
        
        # Patch methods to avoid full execution
        with patch.object(CrawlerLoop, "_ensure_app_foreground", return_value=True), \
             patch.object(CrawlerLoop, "_should_continue", return_value=False), \
             patch.object(CrawlerLoop, "_initialize_traffic_capture"), \
             patch.object(CrawlerLoop, "_initialize_video_recording"), \
             patch.object(CrawlerLoop, "_emit_event"):
            
            crawler.run(1)
            
            # Verify values were updated during run()
            assert crawler.max_crawl_steps == 25
            assert crawler.max_crawl_duration_seconds == 1200

    def test_pause_aware_timer(self, mock_deps):
        """Test that paused duration is correctly subtracted from elapsed time."""
        crawler = CrawlerLoop(**mock_deps)
        
        # Initial state
        start_time = 100.0
        crawler._paused_duration = 0.0
        crawler.max_crawl_duration_seconds = 60
        
        # 1. No pause: 30s elapsed -> Should continue
        with patch("time.time", return_value=130.0):
            assert crawler._should_continue(run_id=1, step_number=1, start_time=start_time) is True
            
        # 2. No pause: 70s elapsed -> Should stop
        with patch("time.time", return_value=170.0):
            assert crawler._should_continue(run_id=1, step_number=1, start_time=start_time) is False
            
        # 3. With 30s pause: 70s elapsed -> Should continue (active time = 40s)
        crawler._paused_duration = 30.0
        with patch("time.time", return_value=170.0):
            assert crawler._should_continue(run_id=1, step_number=1, start_time=start_time) is True
            
        # 4. With 30s pause: 100s elapsed -> Should stop (active time = 70s)
        with patch("time.time", return_value=200.0):
            assert crawler._should_continue(run_id=1, step_number=1, start_time=start_time) is False
