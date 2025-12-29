#!/usr/bin/env python3
"""
Main crawler loop that runs the AI-powered app crawling process.
This module implements the core decision-execution cycle.
"""

import io
import logging
import os
import sys
import time
import base64
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from config.app_config import Config
    from domain.agent_assistant import AgentAssistant
    from core.controller import FlagController
    from domain.app_context_manager import AppContextManager
    from utils.paths import SessionPathManager
    from domain.traffic_capture_manager import TrafficCaptureManager
    from domain.video_recording_manager import VideoRecordingManager
    from core.stuck_detector import StuckDetector
    from core.crawl_context_builder import CrawlContextBuilder
    from core.crawl_logger import CrawlLogger
except ImportError as e:
    print(f"FATAL: Import error: {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

logger = logging.getLogger(__name__)

# Constants for flag file paths
DEFAULT_SHUTDOWN_FLAG = 'crawler_shutdown.flag'
DEFAULT_PAUSE_FLAG = 'crawler_pause.flag'


class CrawlerLoop:
    """Main crawler loop that orchestrates AI decision-making and action execution."""
    
    def __init__(self, config: Config):
        """Initialize the crawler loop.
        
        Args:
            config: Configuration object
        """
        try:
            self.config = config
            
            self.agent_assistant: Optional[AgentAssistant] = None
            self.app_context_manager: Optional[AppContextManager] = None
            self.traffic_capture_manager: Optional[TrafficCaptureManager] = None
            self.video_recording_manager: Optional[VideoRecordingManager] = None
            self.step_count = 0
            self.current_screen_visit_count = 0
            self.current_composite_hash = ""
            self.last_action_feedback: Optional[str] = None
            self.current_run_id: Optional[int] = None
            self.current_from_screen_id: Optional[int] = None
            
            # Specialized components
            self.stuck_detector = StuckDetector(config)
            self.context_builder: Optional[CrawlContextBuilder] = None
            self.crawl_logger: Optional[CrawlLogger] = None
            
            # Database and screen state (initialized in initialize() method)
            self.db_manager = None
            self.screen_state_manager = None
            
            # Runtime stats for thesis metrics (tracked during crawl, saved at end)
            self.runtime_stats: Dict[str, Any] = {
                'stuck_detection_count': 0,
                'ai_retry_count': 0,
                'element_not_found_count': 0,
                'app_crash_count': 0,
                'context_loss_count': 0,
                'image_context_enabled': config.get('ENABLE_IMAGE_CONTEXT', False),
                'ai_provider': config.get('AI_PROVIDER', 'unknown'),
                'model_type': config.get('DEFAULT_MODEL_TYPE', 'unknown'),
            }
            
            # Set up flag controller
            # Prefer properties from Config object if available (to match UI usage)
            shutdown_flag_path = getattr(config, 'SHUTDOWN_FLAG_PATH', None)
            if not shutdown_flag_path:
                shutdown_flag_path = config.get('SHUTDOWN_FLAG_PATH') or os.path.join(
                    config.BASE_DIR or '.', DEFAULT_SHUTDOWN_FLAG
                )
            
            pause_flag_path = getattr(config, 'PAUSE_FLAG_PATH', None)
            if not pause_flag_path:
                pause_flag_path = config.get('PAUSE_FLAG_PATH') or os.path.join(
                    config.BASE_DIR or '.', DEFAULT_PAUSE_FLAG
                )
            
            self.flag_controller = FlagController(shutdown_flag_path, pause_flag_path)
            
            # Wait time between actions
            wait_after_action = config.get('WAIT_AFTER_ACTION')
            if wait_after_action is None:
                raise ValueError("WAIT_AFTER_ACTION must be set in configuration")
            self.wait_after_action = float(wait_after_action)
        except SystemExit as e:
            print(f"SystemExit in CrawlerLoop.__init__: {e}", file=sys.stderr, flush=True)
            raise
        except Exception as e:
            print(f"Exception in CrawlerLoop.__init__: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            logger.error(f"Error in CrawlerLoop.__init__: {e}", exc_info=True)
            raise
        
    def initialize(self) -> bool:
        """Initialize the agent assistant and driver connection.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            
            # Initialize AgentAssistant
            self.agent_assistant = AgentAssistant(self.config)
            
            # Ensure driver is connected
            if not self.agent_assistant._ensure_driver_connected():
                error_msg = "Failed to connect driver - check MCP server is running"
                logger.error(error_msg)
                print(f"STATUS: {error_msg}", flush=True)
                return False
            
            
            # Now that device is initialized, set up file logging if it was delayed
            # This ensures the log directory is created with the correct device name
            try:
                # Use the property which automatically resolves the template
                log_dir = self.config.LOG_DIR
            except Exception:
                # Fallback: try to resolve manually
                log_dir = self.config.get('LOG_DIR')
                if log_dir and '{' in log_dir:
                    try:
                        # Force path regeneration to get the correct path with device name
                        path_manager = self.config._path_manager
                        # Force regeneration to ensure we get the path with device name, not unknown_device
                        log_dir_path = path_manager.get_log_dir(force_regenerate=True)
                        log_dir = str(log_dir_path)
                    except Exception as e:
                        logger.warning(f"Could not resolve log directory template: {e}")
                        log_dir = None
            
            # Verify the path doesn't contain unknown_device and set up logging
            if log_dir:
                if 'unknown_device' in log_dir:
                    logger.warning(f"Log directory still contains unknown_device: {log_dir}, skipping file logging setup")
                else:
                    try:
                        os.makedirs(log_dir, exist_ok=True)
                        log_file_name = self.config.get('LOG_FILE_NAME')
                        if not log_file_name:
                            log_file_name = 'crawler.log'  # Unified log file
                        log_file = os.path.join(log_dir, log_file_name)
                        
                        # Add file handler to root logger if not already present
                        root_logger = logging.getLogger()
                        has_file_handler = any(isinstance(h, logging.FileHandler) for h in root_logger.handlers)
                        if not has_file_handler:
                            file_handler = logging.FileHandler(log_file, encoding='utf-8')
                            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
                            root_logger.addHandler(file_handler)
                    except Exception as e:
                        logger.warning(f"Could not set up delayed file logging: {e}")
            
            # Recreate AI interaction logger with correct path after device initialization
            # This ensures log files are created in the correct directory (with device name, not unknown_device)
            if self.agent_assistant and hasattr(self.agent_assistant, '_setup_ai_interaction_logger'):
                try:
                    self.agent_assistant._setup_ai_interaction_logger(force_recreate=True)
                except Exception as e:
                    logger.warning(f"Could not recreate AI interaction logger: {e}")
            
            # Initialize AppContextManager for app context checking
            self.app_context_manager = AppContextManager(
                self.agent_assistant.tools.driver,
                self.config
            )
            
            # Initialize TrafficCaptureManager if traffic capture is enabled
            if self.config.get('ENABLE_TRAFFIC_CAPTURE', False):
                try:
                    self.traffic_capture_manager = TrafficCaptureManager(
                        self.agent_assistant.tools.driver,
                        self.config
                    )
                except Exception as e:
                    logger.warning(f"Failed to initialize TrafficCaptureManager: {e}. Traffic capture will be disabled.")
                    self.traffic_capture_manager = None
            
            # Initialize VideoRecordingManager if video recording is enabled
            if self.config.get('ENABLE_VIDEO_RECORDING', False):
                try:
                    self.video_recording_manager = VideoRecordingManager(
                        self.agent_assistant.tools.driver,
                        self.config
                    )
                except Exception as e:
                    logger.warning(f"Failed to initialize VideoRecordingManager: {e}. Video recording will be disabled.")
                    self.video_recording_manager = None
            
            # Launch the app at the start of crawl loop
            if self.app_context_manager:
                if not self.app_context_manager.launch_and_verify_app():
                    logger.warning("Failed to launch app at start, but continuing...")
            else:
                logger.warning("AppContextManager not initialized - cannot launch app")
            
            # Initialize database to ensure it exists even if no screens are saved
            # This is important for post-run tasks like PDF generation
            # IMPORTANT: This must be done AFTER all managers are initialized and device name is resolved
            # to ensure the database is created in the correct session directory (not unknown_device)
            try:
                from infrastructure.database import DatabaseManager
                
                # Ensure the database path is resolved (not a template string)
                # The DB_NAME property uses path_manager.get_db_path() which resolves the template
                db_path = self.config.DB_NAME
                
                # Verify the path is resolved (not a template)
                if '{' in db_path or '}' in db_path:
                    logger.error(f"Database path contains unresolved template: {db_path}. Device info may not be available yet.")
                    raise ValueError(f"Database path template not resolved: {db_path}")
                
                # Verify the path doesn't contain "unknown_device" (device name should be resolved by now)
                if 'unknown_device' in db_path:
                    logger.error(f"Database path still contains 'unknown_device': {db_path}. Device info not resolved yet.")
                    raise ValueError(f"Database path contains 'unknown_device': device info must be resolved before database initialization.")
                
                db_manager = DatabaseManager(self.config)
                
                # Verify DatabaseManager got the resolved path
                if db_manager.db_path != db_path:
                    logger.warning(f"DatabaseManager path mismatch. Expected: {db_path}, Got: {db_manager.db_path}")
                
                # The connect() method should be responsible for
                # creating the database and its schema if it doesn't exist.
                # connect() will call _create_tables() automatically
                self.db_manager = db_manager
                if self.db_manager.connect():
                    
                    # Initialize ScreenStateManager
                    from domain.screen_state_manager import ScreenStateManager
                    self.screen_state_manager = ScreenStateManager(
                        self.db_manager,
                        self.agent_assistant.tools.driver,
                        self.config
                    )
                    
                    # Initialize specialized components after DB and Screen state are ready
                    self.context_builder = CrawlContextBuilder(self.db_manager, self.config)
                    self.crawl_logger = CrawlLogger(self.db_manager, self.config)
                    
                    # Get or create run_id
                    app_package = self.config.get('APP_PACKAGE')
                    app_activity = self.config.get('APP_ACTIVITY')
                    if app_package and app_activity:
                        self.current_run_id = self.db_manager.get_or_create_run_info(app_package, app_activity)
                        if self.current_run_id:
                            # Initialize ScreenStateManager for this run
                            self.screen_state_manager.initialize_for_run(
                                self.current_run_id,
                                app_package,
                                app_activity
                            )
                        else:
                            logger.warning("Failed to get or create run_id")
                    
                    # Keep connection open for step logging during execution
                    # Don't close it here - we'll use it during execution
                    
                    # Final verification
                    if os.path.exists(db_path):
                        pass
                    else:
                        logger.error(f"Database file STILL missing after init: {db_path}")
                else:
                    # This is a critical failure - db_manager, screen_state_manager, and context_builder are required
                    logger.error("Failed to initialize database. Crawler cannot proceed without database.")
                    print("STATUS: Database initialization failed", flush=True)
                    return False
            except Exception as e:
                # This is also critical - cannot run without database
                logger.error(f"Could not initialize database: {e}. Crawler cannot proceed.", exc_info=True)
                print(f"STATUS: Database error - {e}", flush=True)
                return False
            
            # Note: App launch verification is now handled by the MCP server during session initialization
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize crawler loop: {e}"
            logger.error(error_msg, exc_info=True)
            print(f"STATUS: Initialization failed - {str(e)}", flush=True)
            return False
    
    def check_shutdown_flag(self) -> bool:
        """Check if shutdown flag exists.
        
        Returns:
            True if shutdown requested, False otherwise
        """
        return self.flag_controller.is_shutdown_flag_present()
    
    def check_pause_flag(self) -> bool:
        """Check if pause flag exists.
        
        Returns:
            True if paused, False otherwise
        """
        return self.flag_controller.is_pause_flag_present()
    
    def wait_while_paused(self):
        """Wait while pause flag is present."""
        while self.check_pause_flag() and not self.check_shutdown_flag():
            time.sleep(0.5)

    def wait_with_check(self, seconds: float) -> bool:
        """
        Wait for a specified duration while checking for shutdown and pause flags.
        
        Args:
            seconds: Number of seconds to wait
            
        Returns:
            True if completed without shutdown request, False if shutdown requested
        """
        start_time = time.time()
        while (time.time() - start_time) < seconds:
            if self.check_shutdown_flag():
                return False
            
            if self.check_pause_flag():
                self.wait_while_paused()
                # Check shutdown again after pause (in case stop was pressed while paused)
                if self.check_shutdown_flag():
                    return False
            
            # Sleep in small chunks
            time.sleep(0.1)
        return True
    
    
    def run_step(self) -> bool:
        """Run a single crawler step: get screen -> decide action -> execute.
        
        Returns:
            True if step completed successfully, False if should stop
        """
        try:
            # 1. Check for shutdown and pause
            if self.check_shutdown_flag():
                return False
            
            if self.check_pause_flag():
                self.wait_while_paused()
                if self.check_shutdown_flag():
                    return False
            
            # 2. Increment step and log progress
            self.step_count += 1
            if self.crawl_logger:
                self.crawl_logger.log_ui_step(self.step_count)
            else:
                # Fallback UI step logging when crawl_logger is not available
                print(f"UI_STEP:{self.step_count}", flush=True)
            
            # 3. Verify app context
            if self.app_context_manager:
                if not self.app_context_manager.ensure_in_app():
                    logger.warning("Failed to ensure app context after retry - skipping step")
                    self.last_action_feedback = "App context check failed"
                    # Track context loss for thesis metrics
                    self.runtime_stats['context_loss_count'] += 1
                    return True
                
                # Check if we escaped from a browser - add feedback for AI
                browser_feedback = self.app_context_manager.get_and_clear_browser_escape_feedback()
                if browser_feedback:
                    # Prepend browser feedback to existing feedback
                    if self.last_action_feedback:
                        self.last_action_feedback = f"{browser_feedback} | {self.last_action_feedback}"
                    else:
                        self.last_action_feedback = browser_feedback
            
            # 4. Get current screen representation
            candidate_screen = self.screen_state_manager.get_current_screen_representation(
                self.current_run_id, self.step_count
            )
            if not candidate_screen:
                logger.error("Failed to get current screen state")
                return True
            
            # Save and define UI screenshot immediately to ensure UI is up to date (live view)
            if candidate_screen.screenshot_path and candidate_screen.screenshot_bytes:
                try:
                    os.makedirs(os.path.dirname(candidate_screen.screenshot_path), exist_ok=True)
                    with open(candidate_screen.screenshot_path, "wb") as f:
                        f.write(candidate_screen.screenshot_bytes)
                    print(f"UI_SCREENSHOT:{candidate_screen.screenshot_path}", flush=True)
                except Exception as e:
                    logger.warning(f"Failed to save UI screenshot: {e}")
            
            # 5. Process and record state
            final_screen, visit_info = self.screen_state_manager.process_and_record_state(
                candidate_screen, self.current_run_id, self.step_count, increment_visit_count=False
            )
            from_screen_id = final_screen.id
            self.current_composite_hash = final_screen.composite_hash
            current_screen_visit_count = visit_info.get("visit_count_this_run", 0)
            self.current_screen_visit_count = current_screen_visit_count
            
            # UI_SCREENSHOT print removed (handled above with fresh candidate)
            
            # 6. Load exploration journal from DB
            exploration_journal = ""
            if self.db_manager and self.current_run_id:
                exploration_journal = self.db_manager.get_exploration_journal(self.current_run_id) or ""
            
            # 7. Detect if stuck (still uses internal tracking for now)
            action_history, visited_screens, current_screen_actions = self.context_builder.get_crawl_context(
                self.current_run_id, from_screen_id
            )
            is_stuck, stuck_reason = self.stuck_detector.check_if_stuck(
                from_screen_id, current_screen_visit_count, action_history, current_screen_actions
            )
            
            # Track stuck detection for thesis metrics
            if is_stuck:
                self.runtime_stats['stuck_detection_count'] += 1
            
            # 8. Log context
            self.crawl_logger.log_ai_context(
                self.step_count, is_stuck, stuck_reason, action_history, 
                visited_screens, from_screen_id, current_screen_visit_count, current_screen_actions
            )
            
            # 9. Get next action from AI
            
            # Check for shutdown/pause before expensive AI call
            if self.check_shutdown_flag():
                return False
            
            if self.check_pause_flag():
                self.wait_while_paused()
                if self.check_shutdown_flag():
                    return False
            
            ai_decision_start = time.time()
            action_result = self.agent_assistant._get_next_action_langchain(
                screenshot_bytes=final_screen.screenshot_bytes,
                xml_context=final_screen.xml_content or "",
                current_screen_actions=current_screen_actions,
                current_screen_id=from_screen_id,
                current_screen_visit_count=current_screen_visit_count,
                current_composite_hash=self.current_composite_hash,
                last_action_feedback=self.last_action_feedback,
                is_stuck=is_stuck,
                stuck_reason=stuck_reason if is_stuck else None,
                ocr_results=candidate_screen.ocr_results if candidate_screen else None,
                exploration_journal=exploration_journal
            )
            ai_decision_time = time.time() - ai_decision_start
            
            if not action_result:
                self.crawl_logger.log_step_to_db(
                    self.current_run_id, self.step_count, from_screen_id, None, None,
                    "AI decision failed", False, ai_decision_time * 1000.0, None, None, None,
                    "AI did not return a valid action"
                )
                self.last_action_feedback = "AI decision failed"
                # Track AI retry/failure for thesis metrics
                self.runtime_stats['ai_retry_count'] += 1
                return True
            
            action_data, confidence, token_count, ai_input_prompt, new_exploration_journal = action_result
            
            # Save the updated exploration journal to DB
            if self.db_manager and self.current_run_id and new_exploration_journal:
                self.db_manager.update_exploration_journal(self.current_run_id, new_exploration_journal)
            
            # Check if AI signaled signup completion - store credentials for future logins
            if action_data.get("signup_completed"):
                try:
                    from infrastructure.credential_store import get_credential_store
                    app_package = self.config.get("APP_PACKAGE")
                    test_email = self.config.get("TEST_EMAIL")
                    test_password = self.config.get("TEST_PASSWORD")
                    test_name = self.config.get("TEST_NAME")
                    
                    if app_package and test_email and test_password:
                        cred_store = get_credential_store()
                        success = cred_store.store_credentials(
                            package_name=app_package,
                            email=test_email,
                            password=test_password,
                            name=test_name,
                            signup_completed=True
                        )
                        if success:
                            logger.info(f"✅ Stored credentials for {app_package} after successful signup")
                            self.last_action_feedback = f"Signup completed! Credentials saved for future logins."
                        else:
                            logger.warning(f"Failed to store credentials for {app_package}")
                except Exception as e:
                    logger.error(f"Error storing credentials after signup: {e}")
            
            # Check for shutdown/pause after AI return but before action execution
            # This allows "pausing mid-thought"
            if self.check_shutdown_flag():
                return False
                
            if self.check_pause_flag():
                self.wait_while_paused()
                if self.check_shutdown_flag():
                    return False
                    
            # Pass OCR results so action descriptions use actual text instead of opaque IDs
            ocr_results = candidate_screen.ocr_results if candidate_screen else None
            action_str = self.crawl_logger.log_ai_decision(action_data, ai_decision_time, ai_input_prompt, ocr_results)
            
            # 10. Execute actions (supports multi-action batch)
            # Extract actions array from the batch response
            actions_list = action_data.get("actions", [])
            if not actions_list:
                # Legacy fallback: if no 'actions' key, treat action_data itself as single action
                actions_list = [action_data]
            
            # Add OCR results to each action for fallback element resolution
            if ocr_results:
                for act in actions_list:
                    act["ocr_results"] = ocr_results
            
            # Get multi-action config settings
            wait_between_actions = float(self.config.get('WAIT_BETWEEN_BATCH_ACTIONS', 0.5))
            stop_on_error = bool(self.config.get('MULTI_ACTION_STOP_ON_ERROR', True))
            
            element_find_start = time.time()
            
            # Use batch execution for multi-action support
            executed_count, success_list, batch_error = self.agent_assistant.action_executor.execute_action_batch(
                actions_list,
                wait_between_actions=wait_between_actions,
                stop_on_error=stop_on_error
            )
            
            element_find_time_ms = (time.time() - element_find_start) * 1000.0
            
            # Overall success: all actions succeeded
            success = all(success_list) if success_list else False
            
            # Track multi-action statistics
            if len(actions_list) > 1:
                self.runtime_stats['multi_action_batch_count'] = self.runtime_stats.get('multi_action_batch_count', 0) + 1
                self.runtime_stats['total_batch_actions'] = self.runtime_stats.get('total_batch_actions', 0) + len(actions_list)
            
            # Wait for actions to settle before capturing the result
            if not self.wait_with_check(self.wait_after_action):
                return False
            
            # 11. Capture post-action screenshot immediately for UI (regardless of success)
            # This ensures the UI shows the current device state right after action execution
            to_screen_id = None
            try:
                landing_candidate = self.screen_state_manager.get_current_screen_representation(
                    self.current_run_id, self.step_count
                )
                if landing_candidate:
                    # Save and send screenshot to UI immediately
                    if landing_candidate.screenshot_path and landing_candidate.screenshot_bytes:
                        try:
                            os.makedirs(os.path.dirname(landing_candidate.screenshot_path), exist_ok=True)
                            with open(landing_candidate.screenshot_path, "wb") as f:
                                f.write(landing_candidate.screenshot_bytes)
                            print(f"UI_SCREENSHOT:{landing_candidate.screenshot_path}", flush=True)
                        except Exception as e:
                            logger.warning(f"Failed to save UI screenshot (post-action): {e}")
                    
                    # Process and record the landing screen
                    if success:
                        final_landing, _ = self.screen_state_manager.process_and_record_state(
                            landing_candidate, self.current_run_id, self.step_count, increment_visit_count=True
                        )
                        to_screen_id = final_landing.id
            except Exception as e:
                logger.warning(f"Failed to capture post-action screenshot: {e}")
            
            # 12. Final logging and feedback
            self.crawl_logger.log_step_to_db(
                self.current_run_id, self.step_count, from_screen_id, to_screen_id, action_data,
                action_str, success, ai_decision_time * 1000.0, token_count, ai_input_prompt, 
                element_find_time_ms
            )
            
            # Build detailed feedback including batch execution results
            if len(actions_list) > 1:
                # Multi-action batch feedback
                succeeded = sum(success_list)
                total = len(actions_list)
                executed = executed_count
                
                if success:
                    if to_screen_id is not None and to_screen_id != from_screen_id:
                        self.last_action_feedback = f"Batch of {total} actions executed ({succeeded}/{executed} succeeded) -> NAVIGATED to #{to_screen_id}"
                    else:
                        self.last_action_feedback = f"Batch of {total} actions executed ({succeeded}/{executed} succeeded) -> STAYED on #{from_screen_id}"
                else:
                    self.last_action_feedback = f"Batch PARTIAL: {succeeded}/{executed} actions succeeded. {batch_error or ''}"
                    # Track element not found / execution failure for thesis metrics
                    self.runtime_stats['element_not_found_count'] += 1
            else:
                # Single action feedback (legacy format)
                if success:
                    if to_screen_id is not None:
                        if to_screen_id != from_screen_id:
                            self.last_action_feedback = f"Action '{action_str}' executed -> NAVIGATED to new screen #{to_screen_id}"
                        else:
                            self.last_action_feedback = f"Action '{action_str}' executed -> STAYED on same screen #{from_screen_id} (no effect)"
                    else:
                        self.last_action_feedback = f"Action '{action_str}' executed -> screen state unclear"
                else:
                    self.last_action_feedback = f"Action '{action_str}' FAILED to execute"
                    # Track element not found / execution failure for thesis metrics
                    self.runtime_stats['element_not_found_count'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error in crawler step: {e}", exc_info=True)
            self.last_action_feedback = f"Step error: {str(e)}"
            return True
    
    def run(self, max_steps: Optional[int] = None):
        """Run the main crawler loop.
        
        Args:
            max_steps: Maximum number of steps to run (None for unlimited)
        """
        try:
            
            # Initialize with better error handling
            try:
                init_success = self.initialize()
            except Exception as init_error:
                error_msg = f"Exception during initialization: {init_error}"
                logger.error(error_msg, exc_info=True)
                print(f"STATUS: {error_msg}", flush=True)
                # Give threads time to finish before exit
                import time
                time.sleep(0.5)
                return
            
            if not init_success:
                logger.error("Failed to initialize crawler loop")
                print("STATUS: Crawler initialization failed", flush=True)
                # Give threads time to finish before exit
                import time
                time.sleep(0.5)
                return
            
            
            # Start traffic capture if enabled
            if self.traffic_capture_manager:
                try:
                    # Get run_id from step_count (will be 0 initially, but that's okay)
                    run_id = getattr(self, '_run_id', 0)
                    # Use asyncio.run to handle async call
                    asyncio.run(self.traffic_capture_manager.start_capture_async(
                        run_id=run_id,
                        step_num=0
                    ))
                except Exception as e:
                    logger.error(f"Failed to start traffic capture: {e}", exc_info=True)
            
            # Start video recording if enabled
            if self.video_recording_manager:
                try:
                    run_id = getattr(self, '_run_id', 0)
                    success = self.video_recording_manager.start_recording(
                        run_id=run_id,
                        step_num=0
                    )
                    if success:
                        pass
                    else:
                        pass
                except Exception as e:
                    pass
            
            # Main loop
            while True:
                # Check for shutdown
                if self.check_shutdown_flag():
                    break
                
                # Check max steps
                if max_steps and self.step_count >= max_steps:
                    break
                
                # Run a step
                should_continue = self.run_step()
                if not should_continue:
                    break
            
            # Update run status to COMPLETED
            if self.db_manager and self.current_run_id:
                try:
                    from datetime import datetime
                    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.db_manager.update_run_status(self.current_run_id, "COMPLETED", end_time)
                    
                    # Save runtime stats for thesis metrics
                    import json
                    self.db_manager.update_run_meta(self.current_run_id, json.dumps(self.runtime_stats))
                    logger.info(f"Saved runtime stats: {self.runtime_stats}")
                except Exception as e:
                    logger.error(f"Error updating run status: {e}")
            
            # Close database connection
            if self.db_manager:
                try:
                    self.db_manager.close()
                except Exception as e:
                    logger.warning(f"Error closing database: {e}")
            
            # Cleanup
            print("STATUS: Crawler completed")
            
        except KeyboardInterrupt:
            # Update run status to INTERRUPTED
            if self.db_manager and self.current_run_id:
                try:
                    from datetime import datetime
                    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.db_manager.update_run_status(self.current_run_id, "INTERRUPTED", end_time)
                except Exception as e:
                    logger.error(f"Error updating run status: {e}")
            if self.db_manager:
                try:
                    self.db_manager.close()
                except Exception:
                    pass
            print("STATUS: Crawler interrupted", flush=True)
        except Exception as e:
            logger.error(f"Fatal error in crawler loop: {e}", exc_info=True)
            # Update run status to FAILED
            if self.db_manager and self.current_run_id:
                try:
                    from datetime import datetime
                    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.db_manager.update_run_status(self.current_run_id, "FAILED", end_time)
                except Exception as e:
                    logger.error(f"Error updating run status: {e}")
            if self.db_manager:
                try:
                    self.db_manager.close()
                except Exception:
                    pass
            print("STATUS: Crawler error", flush=True)
        finally:
            # Stop traffic capture if it was started
            if self.traffic_capture_manager and self.traffic_capture_manager.is_capturing():
                try:
                    run_id = getattr(self, '_run_id', 0)
                    pcap_path = asyncio.run(self.traffic_capture_manager.stop_capture_and_pull_async(
                        run_id=run_id,
                        step_num=self.step_count
                    ))
                    if pcap_path:
                        pass
                    else:
                        logger.warning("Traffic capture stopped but file was not saved")
                except Exception as e:
                    logger.error(f"Error stopping traffic capture: {e}", exc_info=True)
            
            # Stop video recording if it was started
            if self.video_recording_manager and self.video_recording_manager.is_recording():
                try:
                    video_path = self.video_recording_manager.stop_recording_and_save()
                    if video_path:
                        pass
                    else:
                        logger.warning("Video recording stopped but file was not saved")
                except Exception as e:
                    logger.error(f"Error stopping video recording: {e}", exc_info=True)
            
            # Run MobSF analysis if enabled
            mobsf_enabled = self.config.get('ENABLE_MOBSF_ANALYSIS', False)
            
            # Explicitly check for True boolean or "true" string
            if mobsf_enabled is True or str(mobsf_enabled).lower() == 'true':
                try:
                    from infrastructure.mobsf_manager import MobSFManager
                    package_name = self.config.get('APP_PACKAGE')
                    if package_name:
                        mobsf_manager = MobSFManager(self.config)
                        success, result = mobsf_manager.perform_complete_scan(package_name)
                        if success:
                            if isinstance(result, dict):
                                if result.get('pdf_report'):
                                    pass
                                if result.get('json_report'):
                                    pass
                        else:
                            error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else str(result)
                            logger.error(f"MobSF analysis failed: {error_msg}")
                    else:
                        logger.warning("APP_PACKAGE not configured, skipping MobSF analysis")
                except Exception as e:
                    logger.error(f"Error running MobSF analysis: {e}", exc_info=True)
            
            # Annotate screenshots with action coordinates
            try:
                from cli.services.screenshot_annotator import ScreenshotAnnotator
                if hasattr(self.config, '_path_manager') and self.config._path_manager:
                    session_dir = self.config._path_manager.get_session_path()
                    if session_dir and session_dir.exists():
                        annotator = ScreenshotAnnotator()
                        success, result = annotator.annotate_session(session_dir)
                        if success:
                            logger.info(f"Annotated {result.get('annotated_count', 0)} screenshots")
                        else:
                            errors = result.get('errors', [])
                            if errors:
                                logger.warning(f"Screenshot annotation issues: {errors[0]}")
            except Exception as e:
                logger.warning(f"Failed to annotate screenshots: {e}")
            
            # Close the app when crawl loop is done
            if self.app_context_manager:
                try:
                    target_pkg = self.config.get('APP_PACKAGE')
                    if target_pkg and self.agent_assistant and self.agent_assistant.tools.driver:
                        self.agent_assistant.tools.driver.terminate_app(target_pkg)
                except Exception as e:
                    logger.warning(f"Error terminating app at crawl loop end: {e}")
            
            # Disconnect driver
            if self.agent_assistant and self.agent_assistant.tools.driver:
                try:
                    self.agent_assistant.tools.driver.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting driver: {e}")
            
            # Give any daemon threads time to finish before exit
            import time
            import threading
            time.sleep(0.5)
            
            # Force flush all streams
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            except:
                pass


def run_crawler_loop(config: Optional[Config] = None):
    """Entry point for running the crawler loop.
    
    Args:
        config: Optional config object (creates new one if not provided)
    """
    try:
        if config is None:
            config = Config()
        
        
        # Set up logging - always log to stdout so parent process can see it
        # Also try to log to file if LOG_DIR is available
        # Wrap stdout/stderr with UTF-8 encoding to handle Unicode characters on Windows
        try:
            # Configure stdout/stderr to use UTF-8
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
                output_stream = sys.stdout
            else:
                # Fallback for systems/environments where reconfigure isn't available
                stdout_wrapper = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
                sys.stdout = stdout_wrapper
                stderr_wrapper = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
                sys.stderr = stderr_wrapper
                output_stream = stdout_wrapper
            
            handlers = [logging.StreamHandler(output_stream)]
        except Exception as e:
            # Fallback to regular stdout if wrapping fails
            print(f"Warning: Failed to set UTF-8 encoding for stdout: {e}", file=sys.stderr)
            handlers = [logging.StreamHandler(sys.stdout)]
        
        # Use the property which automatically resolves the template
        try:
            log_dir = config.LOG_DIR
        except Exception:
            # Fallback: try to resolve manually
            log_dir = config.get('LOG_DIR')
            if log_dir:
                # Resolve placeholders in log_dir if present
                if '{' in log_dir:
                    # Use the same SessionPathManager instance from config to ensure consistency
                    try:
                        # Use config's path manager instead of creating a new instance
                        path_manager = config._path_manager
                        log_dir_path = path_manager.get_log_dir()
                        log_dir = str(log_dir_path)
                    except Exception as e:
                        # Fallback: try to resolve placeholders manually
                        output_data_dir = config.get('OUTPUT_DATA_DIR') or 'output_data'
                        if '{OUTPUT_DATA_DIR}' in log_dir:
                            log_dir = log_dir.replace('{OUTPUT_DATA_DIR}', output_data_dir)
                        if '{session_dir}' in log_dir:
                            # Use proper sessions directory structure instead of crawler_session
                            try:
                                # Use config's path manager instead of creating a new instance
                                path_manager = config._path_manager
                                session_path = path_manager.get_session_path()
                                log_dir = log_dir.replace('{session_dir}', str(session_path))
                            except Exception:
                                # Last resort: use sessions directory with unknown_device
                                # But prefer device name if available
                                # Get device info from path_manager if available
                                if hasattr(config, '_path_manager'):
                                    path_manager = config._path_manager
                                    device_name = path_manager.get_device_name()
                                    device_udid = path_manager.get_device_udid()
                                    timestamp = path_manager.get_timestamp()
                                else:
                                    device_name = None
                                    device_udid = None
                                    timestamp = time.strftime('%Y-%m-%d_%H-%M')
                                device_id = device_name or device_udid or 'unknown_device'
                                app_package = config.get('APP_PACKAGE') or 'unknown.app'
                                app_package_safe = app_package.replace('.', '_')
                                session_dir = os.path.join(output_data_dir, 'sessions', f'{device_id}_{app_package_safe}_{timestamp}')
                                log_dir = log_dir.replace('{session_dir}', session_dir)
            
            # Only create log directory if we have a real device ID
            # This prevents creating directories with unknown_device
            # Get device info from path_manager if available
            if hasattr(config, '_path_manager'):
                path_manager = config._path_manager
                device_name = path_manager.get_device_name()
                device_udid = path_manager.get_device_udid()
            else:
                device_name = None
                device_udid = None
            has_real_device = device_name or device_udid
            
            if has_real_device or 'unknown_device' not in log_dir:
                try:
                    os.makedirs(log_dir, exist_ok=True)
                    log_file = os.path.join(log_dir, config.get('LOG_FILE_NAME', 'crawler.log'))
                    handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
                except Exception as e:
                    # If file logging fails, continue with stdout only
                    print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)
            else:
                # Delay file logging until device is initialized
                # Log to stdout only for now
                print("INFO: Delaying file logging until device is initialized (to avoid unknown_device directory)", file=sys.stderr)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers,
            force=True  # Force reconfiguration in case logging was already set up
        )
        
        # Silence noisy third-party loggers
        noisy_loggers = [
            "httpx", "httpcore", "urllib3",
            "openai", "openai._base_client",
            "google.api_core", "google.auth", "google.generativeai",
            "appium.webdriver.webdriver", "selenium.webdriver.remote.remote_connection",
            "asyncio", "PIL",
        ]
        for lib_name in noisy_loggers:
            logging.getLogger(lib_name).setLevel(logging.WARNING)
        
        # Create and run crawler loop - use minimal logging to avoid daemon thread issues
        try:
            # Use direct print to stderr instead of logger to avoid threading issues
            
            # Create crawler loop
            
            # Try to create the crawler loop with explicit error handling
            try:
                crawler = CrawlerLoop(config)
            except BaseException as be:
                # Catch ALL exceptions including SystemExit, KeyboardInterrupt, etc.
                logger.error(f"BaseException caught during CrawlerLoop creation: {type(be).__name__}: {be}", exc_info=True)
                # Don't re-raise immediately - give threads time
                import time
                time.sleep(1.0)
                raise
            
        except SystemExit as e:
            print(f"SystemExit caught in CrawlerLoop creation: {e}", file=sys.stderr, flush=True)
            # Give threads time to finish
            import time
            time.sleep(0.5)
            raise
        except Exception as e:
            print(f"Exception in CrawlerLoop creation: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            # Give threads time to finish
            import time
            time.sleep(0.5)
            raise
        
        # Get max steps from config
        max_steps = config.get('MAX_CRAWL_STEPS')
        if max_steps:
            try:
                max_steps = int(max_steps)
            except (ValueError, TypeError):
                max_steps = None
        
        try:
            crawler.run(max_steps=max_steps)
        except SystemExit:
            # Re-raise SystemExit to allow clean exit
            raise
        except Exception as e:
            error_msg = f"Fatal error in crawler.run(): {e}"
            logger.error(error_msg, exc_info=True)
            print(f"FATAL: {error_msg}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            # Give threads time to finish
            import time
            time.sleep(0.5)
            sys.exit(1)
        finally:
            # Final cleanup - ensure all streams are flushed
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            except:
                pass
    except KeyboardInterrupt:
        print("Crawler interrupted by user", file=sys.stderr, flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"FATAL ERROR in run_crawler_loop: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run_crawler_loop()

