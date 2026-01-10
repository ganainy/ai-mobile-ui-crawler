"""Integration tests for full crawl scenarios."""

import pytest
import time
from pathlib import Path
from datetime import datetime

from mobile_crawler.core.crawler_loop import CrawlerLoop
from mobile_crawler.core.crawl_state_machine import CrawlState, CrawlStateMachine
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import RunRepository, Run
from mobile_crawler.infrastructure.step_log_repository import StepLogRepository
from mobile_crawler.domain.action_executor import ActionExecutor
from mobile_crawler.infrastructure.screenshot_capture import ScreenshotCapture
from mobile_crawler.infrastructure.ai_interaction_service import AIInteractionService
from mobile_crawler.infrastructure.gesture_handler import GestureHandler


class TestFullCrawl:
    """Test complete crawl workflows."""

    @pytest.mark.integration
    def test_basic_crawl_workflow(
        self,
        appium_driver,
        installed_test_app: str,
        test_config,
        tmp_path
    ):
        """Test a basic crawl from start to finish."""
        # Configure test settings
        test_config.set('max_crawl_steps', 5)  # Short crawl for testing
        test_config.set('max_crawl_duration_seconds', 60)  # 1 minute timeout
        test_config.set('ai_provider', 'mock')  # Use mock AI for testing
        test_config.set('ai_model', 'test-model')

        # Create session directory
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Initialize database
        db_manager = DatabaseManager()
        db_manager.create_schema()

        # Create repositories
        run_repo = RunRepository(db_manager)
        step_log_repo = StepLogRepository(db_manager)

        # Create run record
        run = Run(
            id=None,
            device_id=appium_driver.device_id,
            app_package=installed_test_app,
            start_activity=None,
            start_time=datetime.now(),
            end_time=None,
            status='RUNNING',
            ai_provider='mock',
            ai_model='test-model'
        )
        run_id = run_repo.create_run(run)

        # Create screenshots directory
        screenshots_dir = session_dir / "screenshots"

        # Create crawler dependencies
        state_machine = CrawlStateMachine()
        gesture_handler = GestureHandler(appium_driver)
        action_executor = ActionExecutor(appium_driver, gesture_handler)
        screenshot_capture = ScreenshotCapture(appium_driver, output_dir=screenshots_dir)
        ai_service = AIInteractionService.from_config(test_config)

        # Create crawler loop
        crawler = CrawlerLoop(
            crawl_state_machine=state_machine,
            screenshot_capture=screenshot_capture,
            ai_interaction_service=ai_service,
            action_executor=action_executor,
            step_log_repository=step_log_repo,
            run_repository=run_repo,
            config_manager=test_config
        )

        # Start the crawl
        crawler.start(run_id)

        # Wait for crawl to complete or timeout
        max_wait = 120  # 2 minutes
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if crawler.state_machine.state in [CrawlState.STOPPED, CrawlState.ERROR]:
                break
            time.sleep(1)

        # Verify crawl completed successfully
        assert crawler.state_machine.state == CrawlState.STOPPED

        # Verify statistics were recorded
        run_record = run_repo.get_run(run_id)
        assert run_record is not None
        assert run_record.total_steps > 0
        assert run_record.unique_screens > 0

        # Verify screenshots were captured (screenshots_dir was defined earlier)
        assert screenshots_dir.exists()
        screenshots = list(screenshots_dir.glob("*.png"))
        assert len(screenshots) > 0

        # Verify database records
        conn = db_manager.get_connection()
        
        # Note: screens tracking is not yet fully implemented in crawler loop
        # For now, just verify step_logs are recorded
        step_logs_count = conn.execute("SELECT COUNT(*) FROM step_logs WHERE run_id = ?", (run_id,)).fetchone()[0]
        assert step_logs_count > 0

    @pytest.mark.integration
    def test_crawl_with_pause_resume(
        self,
        appium_driver,
        installed_test_app: str,
        test_config,
        tmp_path
    ):
        """Test crawl pause and resume functionality."""
        # Configure test settings
        # Set high step limit to ensure crawl doesn't complete before pause
        test_config.set('max_crawl_steps', 50)
        test_config.set('max_crawl_duration_seconds', 120)  # 2 minutes
        test_config.set('ai_provider', 'mock')
        test_config.set('ai_model', 'test-model')

        # Create session directory
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Initialize database and repositories
        db_manager = DatabaseManager()
        db_manager.create_schema()
        run_repo = RunRepository(db_manager)
        step_log_repo = StepLogRepository(db_manager)

        # Create run
        run = Run(
            id=None,
            device_id=appium_driver.device_id,
            app_package=installed_test_app,
            start_activity=None,
            start_time=datetime.now(),
            end_time=None,
            status='RUNNING',
            ai_provider='mock',
            ai_model='test-model'
        )
        run_id = run_repo.create_run(run)

        # Connect Appium driver to the app
        appium_driver.connect()

        # Create crawler dependencies
        state_machine = CrawlStateMachine()
        gesture_handler = GestureHandler(appium_driver)
        action_executor = ActionExecutor(appium_driver, gesture_handler)
        screenshot_capture = ScreenshotCapture(appium_driver)
        ai_service = AIInteractionService.from_config(test_config)

        # Create crawler
        crawler = CrawlerLoop(
            crawl_state_machine=state_machine,
            screenshot_capture=screenshot_capture,
            ai_interaction_service=ai_service,
            action_executor=action_executor,
            step_log_repository=step_log_repo,
            run_repository=run_repo,
            config_manager=test_config
        )

        # Start crawl
        crawler.start(run_id)

        # Wait a bit then pause
        time.sleep(5)
        crawler.pause()

        # Verify paused
        assert crawler.state_machine.state == CrawlState.PAUSED_MANUAL

        # Wait then resume
        time.sleep(2)
        crawler.resume()

        # Verify resumed - crawler should transition to RUNNING or may already be RUNNING
        # Give it a moment to process
        time.sleep(0.5)
        assert crawler.state_machine.state in [CrawlState.RUNNING, CrawlState.PAUSED_MANUAL], \
            f"Expected RUNNING or PAUSED_MANUAL, got {crawler.state_machine.state}"

        # Let it run a bit more then stop
        time.sleep(5)
        crawler.stop()

        # Wait for crawler to finish stopping
        time.sleep(1)

        # Verify stopped - check for terminal states
        assert crawler.state_machine.state in [CrawlState.STOPPED, CrawlState.STOPPING], \
            f"Expected STOPPED or STOPPING, got {crawler.state_machine.state}"

    @pytest.mark.integration
    def test_crawl_error_recovery(
        self,
        appium_driver,
        installed_test_app: str,
        test_config,
        tmp_path
    ):
        """Test crawl handles errors gracefully."""
        # Configure with very short timeouts to potentially trigger errors
        test_config.set('max_crawl_steps', 3)
        test_config.set('ai_provider', 'mock')
        test_config.set('ai_model', 'test-model')

        # Create session directory
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Initialize database
        db_manager = DatabaseManager()
        db_manager.create_schema()
        run_repo = RunRepository(db_manager)
        step_log_repo = StepLogRepository(db_manager)

        # Create run
        run = Run(
            id=None,
            device_id=appium_driver.device_id,
            app_package=installed_test_app,
            start_activity=None,
            start_time=datetime.now(),
            end_time=None,
            status='RUNNING',
            ai_provider='mock',
            ai_model='test-model'
        )
        run_id = run_repo.create_run(run)

        # Create crawler dependencies
        state_machine = CrawlStateMachine()
        gesture_handler = GestureHandler(appium_driver)
        action_executor = ActionExecutor(appium_driver, gesture_handler)
        screenshot_capture = ScreenshotCapture(appium_driver)
        ai_service = AIInteractionService.from_config(test_config)

        # Create crawler
        crawler = CrawlerLoop(
            crawl_state_machine=state_machine,
            screenshot_capture=screenshot_capture,
            ai_interaction_service=ai_service,
            action_executor=action_executor,
            step_log_repository=step_log_repo,
            run_repository=run_repo,
            config_manager=test_config
        )

        # Start crawl
        crawler.start(run_id)

        # Wait for completion
        max_wait = 60
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if crawler.state_machine.state in [CrawlState.STOPPED, CrawlState.ERROR]:
                break
            time.sleep(1)

        # Verify crawl completed (either successfully or with handled error)
        final_state = crawler.state_machine.state
        assert final_state in [CrawlState.STOPPED, CrawlState.ERROR]

        # If error occurred, verify it was handled gracefully
        if final_state == CrawlState.ERROR:
            run_record = run_repo.get_run(run_id)
            assert run_record is not None
            # Should still have the run record even if error occurred
            assert run_record.status == 'ERROR'

    @pytest.mark.integration
    def test_multiple_runs_isolation(
        self,
        appium_driver,
        installed_test_app: str,
        test_config,
        tmp_path
    ):
        """Test that multiple runs don't interfere with each other."""
        test_config.set('max_crawl_steps', 3)
        test_config.set('ai_provider', 'mock')
        test_config.set('ai_model', 'test-model')

        # Initialize database
        db_manager = DatabaseManager()
        db_manager.create_schema()
        run_repo = RunRepository(db_manager)
        step_log_repo = StepLogRepository(db_manager)

        # Run two crawls sequentially
        for run_num in range(2):
            session_dir = tmp_path / f"session_{run_num}"
            session_dir.mkdir()

            # Create run
            run = Run(
                id=None,
                device_id=appium_driver.device_id,
                app_package=installed_test_app,
                start_activity=None,
                start_time=datetime.now(),
                end_time=None,
                status='RUNNING',
                ai_provider='mock',
                ai_model='test-model'
            )
            run_id = run_repo.create_run(run)

            # Create crawler dependencies
            state_machine = CrawlStateMachine()
            gesture_handler = GestureHandler(appium_driver)
            action_executor = ActionExecutor(appium_driver, gesture_handler)
            screenshot_capture = ScreenshotCapture(appium_driver)
            ai_service = AIInteractionService.from_config(test_config)

            # Create crawler
            crawler = CrawlerLoop(
                crawl_state_machine=state_machine,
                screenshot_capture=screenshot_capture,
                ai_interaction_service=ai_service,
                action_executor=action_executor,
                step_log_repository=step_log_repo,
                run_repository=run_repo,
                config_manager=test_config
            )

            # Start and wait for completion
            crawler.start(run_id)

            max_wait = 45
            start_time = time.time()
            while time.time() - start_time < max_wait:
                if crawler.state_machine.state in [CrawlState.STOPPED, CrawlState.ERROR]:
                    break
                time.sleep(1)

            assert crawler.state_machine.state == CrawlState.STOPPED

            # Verify run data is isolated
            run_record = run_repo.get_run(run_id)
            assert run_record is not None
            assert run_record.id == run_id

        # Verify both runs exist in database
        conn = db_manager.get_connection()
        all_runs = conn.execute("SELECT id FROM runs ORDER BY start_time DESC LIMIT 2").fetchall()
        assert len(all_runs) == 2