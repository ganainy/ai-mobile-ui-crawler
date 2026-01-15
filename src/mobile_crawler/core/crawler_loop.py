"""Main crawler loop orchestration."""

import time
import base64
import logging
from datetime import datetime
from typing import List, Optional
import threading

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.core.crawl_state_machine import CrawlState, CrawlStateMachine
from mobile_crawler.core.crawler_event_listener import CrawlerEventListener
from mobile_crawler.domain.action_executor import ActionExecutor
from mobile_crawler.domain.models import ActionResult
from mobile_crawler.domain.screen_tracker import ScreenTracker, ScreenState
from mobile_crawler.domain.overlay_renderer import OverlayRenderer
from mobile_crawler.infrastructure.ai_interaction_service import AIInteractionService
from mobile_crawler.infrastructure.appium_driver import AppiumDriver
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_exporter import RunExporter
from mobile_crawler.infrastructure.run_repository import RunRepository
from mobile_crawler.infrastructure.screenshot_capture import ScreenshotCapture
from mobile_crawler.infrastructure.step_log_repository import StepLog, StepLogRepository
from mobile_crawler.domain.grounding.manager import GroundingManager
from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager
from mobile_crawler.domain.traffic_capture_manager import TrafficCaptureManager
from mobile_crawler.domain.video_recording_manager import VideoRecordingManager
from mobile_crawler.infrastructure.mobsf_manager import MobSFManager
from mobile_crawler.infrastructure.adb_client import ADBClient

logger = logging.getLogger(__name__)


class CrawlerLoop:
    """Main crawler loop that orchestrates the exploration workflow."""

    def __init__(
        self,
        crawl_state_machine: CrawlStateMachine,
        screenshot_capture: ScreenshotCapture,
        ai_interaction_service: AIInteractionService,
        action_executor: ActionExecutor,
        step_log_repository: StepLogRepository,
        run_repository: RunRepository,
        config_manager: ConfigManager,
        appium_driver: AppiumDriver,
        screen_tracker: ScreenTracker,
        session_folder_manager: SessionFolderManager,
        event_listeners: Optional[List[CrawlerEventListener]] = None,
        top_bar_height: int = 0
    ):
        """Initialize crawler loop.

        Args:
            crawl_state_machine: State machine for crawl lifecycle
            screenshot_capture: Service for capturing screenshots
            ai_interaction_service: Service for AI interactions
            action_executor: Service for executing actions
            step_log_repository: Repository for step logs
            run_repository: Repository for runs
            config_manager: Configuration manager
            appium_driver: Appium driver for device control
            screen_tracker: ScreenTracker for deduplication and novelty detection
            session_folder_manager: SessionFolderManager for artifact organization
            event_listeners: List of event listeners
        """
        self.state_machine = crawl_state_machine
        self.screenshot_capture = screenshot_capture
        self.ai_interaction_service = ai_interaction_service
        self.action_executor = action_executor
        self.step_log_repository = step_log_repository
        self.run_repository = run_repository
        self.config_manager = config_manager
        self.appium_driver = appium_driver
        self.screen_tracker = screen_tracker
        self.session_folder_manager = session_folder_manager
        self.event_listeners = event_listeners or []
        self.overlay_renderer = OverlayRenderer()
        self.grounding_manager = GroundingManager()
        
        # Threading support
        self._crawl_thread: Optional[threading.Thread] = None
        self._current_run_id: Optional[int] = None
        
        # Target app package (set when run starts)
        self._target_package: Optional[str] = None
        
        # Current screen state (updated after each step)
        self._current_screen_state: Optional[ScreenState] = None

        # Step-by-step debug mode (Phase 5)
        self._step_by_step_enabled = False
        self._step_advance_event = threading.Event()

        # Feature managers (initialized on demand)
        self._traffic_capture_manager: Optional[TrafficCaptureManager] = None
        self._video_recording_manager: Optional[VideoRecordingManager] = None
        self._mobsf_manager: Optional[MobSFManager] = None

        # Configuration
        self.max_crawl_steps = self.config_manager.get('max_crawl_steps', 15)
        self.max_crawl_duration_seconds = self.config_manager.get('max_crawl_duration_seconds', 600)
        # Use passed value or fallback to config
        self.top_bar_height = top_bar_height or self.config_manager.get('top_bar_height', 0)

    def add_event_listener(self, listener: CrawlerEventListener) -> None:
        """Add an event listener."""
        self.event_listeners.append(listener)

    def remove_event_listener(self, listener: CrawlerEventListener) -> None:
        """Remove an event listener."""
        if listener in self.event_listeners:
            self.event_listeners.remove(listener)

    def start(self, run_id: int) -> None:
        """Start the crawler loop in a background thread.
        
        Args:
            run_id: The run ID to execute
        """
        if self._crawl_thread and self._crawl_thread.is_alive():
            raise RuntimeError("Crawler is already running")
        
        self._current_run_id = run_id
        self._crawl_thread = threading.Thread(target=self.run, args=(run_id,), daemon=True)
        self._crawl_thread.start()

    def pause(self) -> None:
        """Pause the crawler."""
        if self.state_machine.state == CrawlState.RUNNING:
            self.state_machine.transition_to(CrawlState.PAUSED_MANUAL)

    def resume(self) -> None:
        """Resume the crawler."""
        if self.state_machine.state == CrawlState.PAUSED_MANUAL:
            self.state_machine.transition_to(CrawlState.RUNNING)

    def stop(self) -> None:
        """Stop the crawler."""
        if self.state_machine.state in [CrawlState.RUNNING, CrawlState.PAUSED_MANUAL]:
            self.state_machine.transition_to(CrawlState.STOPPING)

    def is_running(self) -> bool:
        """Check if the crawler is currently running.
        
        Returns:
            True if crawler thread is active
        """
        return self._crawl_thread is not None and self._crawl_thread.is_alive()

    def set_step_by_step_enabled(self, enabled: bool) -> None:
        """Enable or disable step-by-step mode."""
        self._step_by_step_enabled = enabled
        logger.info(f"Step-by-step mode {'enabled' if enabled else 'disabled'}")

    def is_step_by_step_enabled(self) -> bool:
        """Check if step-by-step mode is enabled."""
        return self._step_by_step_enabled

    def advance_step(self) -> None:
        """Advance to the next step when paused in step-by-step mode."""
        if self.state_machine.state == CrawlState.PAUSED_STEP:
            logger.info("Advancing to next step")
            self._step_advance_event.set()
        else:
            logger.warning(f"Advance step requested but crawler is in state {self.state_machine.state}")

    def run(self, run_id: int) -> None:
        """Run the crawler loop for the given run.

        Args:
            run_id: The run ID to execute

        Raises:
            Exception: If the crawl fails
        """
        try:
            # Get run details
            run = self.run_repository.get_run_by_id(run_id)
            if not run:
                raise ValueError(f"Run {run_id} not found")

            # Create session folder and persist path
            session_path = self.session_folder_manager.create_session_folder(run_id)
            self.run_repository.update_session_path(run_id, session_path)
            run.session_path = session_path  # Update local object

            # Update screenshot capture with the new session-specific path
            from pathlib import Path
            screenshots_dir = Path(self.session_folder_manager.get_subfolder(run, "screenshots"))
            self.screenshot_capture.set_output_dir(screenshots_dir)

            # Store target package for app context validation
            self._target_package = run.app_package

            # Initialize and start feature managers if enabled
            self._initialize_traffic_capture(run_id, session_path)
            self._initialize_video_recording(run_id, session_path)

            # Emit crawl started event
            self._emit_event("on_crawl_started", run_id, run.app_package)

            # Transition to initializing
            self.state_machine.transition_to(CrawlState.INITIALIZING)
            self._emit_event("on_state_changed", run_id, "uninitialized", "initializing")

            # Ensure we're in the target app before starting
            if not self._ensure_app_foreground():
                raise RuntimeError(f"Failed to bring target app {self._target_package} to foreground")

            # Initialize crawl
            start_time = time.time()
            step_number = 1
            
            # Start screen tracking for this run
            self.screen_tracker.start_run(run_id)

            # Transition to running
            self.state_machine.transition_to(CrawlState.RUNNING)
            self._emit_event("on_state_changed", run_id, "initializing", "running")

            # Main crawl loop
            while self._should_continue(run_id, step_number, start_time):
                # Check if paused - wait in a loop until resumed or stopped
                while self.state_machine.state == CrawlState.PAUSED_MANUAL:
                    time.sleep(0.1)  # Wait for resume or stop
                    # Check if stop was requested while paused
                    if self.state_machine.state == CrawlState.STOPPING:
                        break
                
                # Check if stopping
                if self.state_machine.state == CrawlState.STOPPING:
                    break
                    
                try:
                    step_success = self._execute_step(run_id, step_number)
                    
                    # Handle step-by-step pause (Phase 5)
                    if self._step_by_step_enabled and self.state_machine.state != CrawlState.STOPPING:
                        self.state_machine.transition_to(CrawlState.PAUSED_STEP)
                        self._emit_event("on_state_changed", run_id, "running", "paused_step")
                        self._emit_event("on_step_paused", run_id, step_number)
                        
                        self._step_advance_event.clear()
                        # Wait for UI to signal advance
                        while not self._step_advance_event.is_set():
                            if self.state_machine.state == CrawlState.STOPPING:
                                break
                            time.sleep(0.1)
                            
                        # If we were resumed, go back to running state
                        if self.state_machine.state == CrawlState.PAUSED_STEP:
                            self.state_machine.transition_to(CrawlState.RUNNING)
                            self._emit_event("on_state_changed", run_id, "paused_step", "running")

                    if step_success:
                        step_number += 1
                    else:
                        # Step failed or signup completed - exit the loop
                        break
                except Exception as e:
                    # Fail the crawl
                    raise

            # Stop feature managers before completing crawl
            self._stop_traffic_capture(run_id, step_number)
            self._stop_video_recording()

            # Run MobSF analysis after crawl completion (if enabled)
            self._run_mobsf_analysis(run_id, session_path)

            # Complete crawl
            total_duration_ms = (time.time() - start_time) * 1000
            reason = self._get_completion_reason(run_id, step_number, start_time)

            self.state_machine.transition_to(CrawlState.STOPPING)
            self._emit_event("on_state_changed", run_id, "running", "stopping")

            # End screen tracking and get final stats
            screen_stats = self.screen_tracker.get_run_stats()
            self.screen_tracker.end_run()
            
            # Finalize run record with actual screen stats
            total_steps = step_number - 1  # steps are 1-indexed
            self.run_repository.update_run_stats(
                run_id=run_id,
                status='COMPLETED',
                end_time=datetime.now(),
                total_steps=total_steps,
                unique_screens=screen_stats.get('unique_screens', total_steps)
            )
            
            # Export run data to JSON
            try:
                db_manager = DatabaseManager()
                run_exporter = RunExporter(db_manager)
                export_path = run_exporter.export_run(run_id)
                logger.info(f"Run data exported to: {export_path}")
            except Exception as export_error:
                logger.warning(f"Failed to export run data: {export_error}")

            self.state_machine.transition_to(CrawlState.STOPPED)
            self._emit_event("on_state_changed", run_id, "stopping", "stopped")

            self._emit_event("on_crawl_completed", run_id, step_number - 1, total_duration_ms, reason)

        except Exception as e:
            # Handle initialization or other critical errors
            if self.state_machine.state != CrawlState.ERROR:
                old_state = self.state_machine.state.value
                self.state_machine.transition_to(CrawlState.ERROR)
                self._emit_event("on_state_changed", run_id, old_state, "error")
            self._emit_event("on_error", run_id, None, e)
            raise

    def _should_continue(self, run_id: int, step_number: int, start_time: float) -> bool:
        """Check if the crawl should continue.

        Args:
            run_id: Current run ID
            step_number: Next step number
            start_time: Crawl start time

        Returns:
            True if crawl should continue
        """
        # Check step limit
        if step_number > self.max_crawl_steps:
            return False

        # Check duration limit
        elapsed_seconds = time.time() - start_time
        if elapsed_seconds >= self.max_crawl_duration_seconds:
            return False

        # Don't check state here - handled in main loop
        return True

    def _ensure_app_foreground(self) -> bool:
        """Ensure the target app is in the foreground.

        Checks if the current foreground app matches the target package.
        If not, attempts to bring the target app to foreground using:
        1. activate_app() - brings app to foreground
        2. If that fails, launches the app via ADB

        Returns:
            True if target app is now in foreground, False otherwise
        """
        if not self._target_package:
            logger.warning("No target package set, skipping app foreground check")
            return True

        try:
            driver = self.appium_driver.get_driver()
            current_package = driver.current_package

            if current_package == self._target_package:
                logger.debug(f"Already in target app: {self._target_package}")
                return True

            logger.warning(f"Not in target app. Current: {current_package}, Target: {self._target_package}")

            # Try to activate the app (brings it to foreground)
            try:
                driver.activate_app(self._target_package)
                time.sleep(1.0)  # Wait for app to come to foreground
                
                # Verify we're now in the right app
                if driver.current_package == self._target_package:
                    logger.info(f"Successfully activated target app: {self._target_package}")
                    return True
            except Exception as e:
                logger.warning(f"activate_app failed: {e}")

            # Fallback: try ADB to launch the app
            try:
                import subprocess
                device_id = self.appium_driver.device_id
                
                # Use monkey to start the app
                result = subprocess.run(
                    ['adb', '-s', device_id, 'shell', 'monkey', '-p', 
                     self._target_package, '-c', 'android.intent.category.LAUNCHER', '1'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    time.sleep(2.0)  # Wait for app to launch
                    if driver.current_package == self._target_package:
                        logger.info(f"Successfully launched target app via ADB: {self._target_package}")
                        return True
            except Exception as e:
                logger.warning(f"ADB app launch failed: {e}")

            logger.error(f"Failed to bring target app to foreground: {self._target_package}")
            return False

        except Exception as e:
            logger.error(f"Error checking app foreground: {e}")
            return False

    def _execute_step(self, run_id: int, step_number: int) -> bool:
        """Execute a single step of the crawl.

        Args:
            run_id: Current run ID
            step_number: Current step number
            
        Returns:
            True if step executed successfully, False if any action failed
        """
        step_start_time = time.time()
        step_success = True

        # Ensure we're in the target app before each step
        if not self._ensure_app_foreground():
            logger.error(f"Cannot execute step {step_number}: target app not in foreground")
            return False

        # Emit step started event
        self._emit_event("on_step_started", run_id, step_number)

        try:
            # Ensure keyboard is hidden before taking screenshot
            self.appium_driver.hide_keyboard()
            time.sleep(0.5)  # Wait for keyboard animation

            # Capture screenshot (returns image, path, AI-optimized base64, and scale factor)
            screenshot_image, screenshot_path, screenshot_b64, scale_factor = self.screenshot_capture.capture_full()

            # Handle top bar exclusion if configured
            self._emit_event("on_debug_log", run_id, step_number, 
                f"Debug: top_bar_height configuration is {self.top_bar_height}px")
            
            if self.top_bar_height > 0:
                w, h = screenshot_image.size
                self._emit_event("on_debug_log", run_id, step_number, 
                    f"Debug: Original screenshot size: {w}x{h}")
                
                if self.top_bar_height < h:
                    # Crop the top bar from the image
                    screenshot_image = screenshot_image.crop((0, self.top_bar_height, w, h))
                    # Overwrite the saved screenshot with the cropped version
                    screenshot_image.save(screenshot_path)
                    # Update AI base64 and scale factor for the cropped version
                    screenshot_b64, scale_factor = self.screenshot_capture._compress_for_ai(screenshot_image)
                    self._emit_event("on_debug_log", run_id, step_number, 
                        f"Top bar exclusion SUCCESS: cropped {self.top_bar_height}px from top. New size: {screenshot_image.size}")
                else:
                    self._emit_event("on_debug_log", run_id, step_number, 
                        f"Warning: top_bar_height ({self.top_bar_height}) >= image height ({h})")

            self._emit_event("on_screenshot_captured", run_id, step_number, screenshot_path)
            
            # Track this screen for deduplication and novelty detection
            # Store previous screen ID for transition tracking in step logs
            previous_screen_id = self._current_screen_state.screen_id if self._current_screen_state else None
            
            self._current_screen_state = self.screen_tracker.process_screen(
                image=screenshot_image,
                step_number=step_number,
                screenshot_path=screenshot_path,
                activity_name=None  # TODO: Get current activity from Appium
            )
            
            # Grounding: Detect text and overlay markers
            try:
                ocr_start = time.time()
                self._emit_event("on_debug_log", run_id, step_number, "Grounding: Running OCR text detection...")
                
                grounding_overlay = self.grounding_manager.process_screenshot(screenshot_path)
                
                ocr_duration = time.time() - ocr_start
                self._emit_event("on_debug_log", run_id, step_number, 
                    f"Grounding: Completed in {ocr_duration:.2f}s ({len(grounding_overlay.ocr_elements)} elements)")
                
                # Use the grounded screenshot for AI analysis
                # We need to re-encode it as base64 if it changed, 
                # but usually we want to send the one with markers to the VLM.
                with open(grounding_overlay.marked_image_path, "rb") as image_file:
                    screenshot_b64_grounded = base64.b64encode(image_file.read()).decode('utf-8')
                
                # Update loop variables to use grounded version
                screenshot_b64 = screenshot_b64_grounded
                # Keep original screenshot_path for reference, but AI gets grounded one
            except Exception as e:
                logger.warning(f"Grounding failed, falling back to raw screenshot: {e}")
                grounding_overlay = None

            logger.info(
                f"Step {step_number}: Screen {self._current_screen_state.screen_id} "
                f"({'NEW' if self._current_screen_state.is_new else 'revisited'}, "
                f"visit #{self._current_screen_state.visit_count}, "
                f"total unique: {self._current_screen_state.total_screens_discovered})"
            )

            
            # Emit screen processed event for UI updates
            self._emit_event(
                "on_screen_processed",
                run_id,
                step_number,
                self._current_screen_state.screen_id,
                self._current_screen_state.is_new,
                self._current_screen_state.visit_count,
                self._current_screen_state.total_screens_discovered
            )

            # Check if we're stuck using screen tracker
            is_stuck, stuck_reason = self.screen_tracker.is_stuck(threshold=3)
            if is_stuck:
                logger.warning(f"Stuck detected: {stuck_reason}")

            # Get screen dimensions (AI receives same size - no scaling)
            original_width, original_height = screenshot_image.size
            screen_dimensions = {"width": original_width, "height": original_height}

            # NOTE: on_ai_request_sent is emitted by AIInteractionService (not here)
            # to avoid duplicate events

            # Get AI actions with screen context for novelty signals
            ai_response = self.ai_interaction_service.get_next_actions(
                run_id=run_id,
                step_number=step_number,
                screenshot_b64=screenshot_b64,
                screenshot_path=screenshot_path,
                is_stuck=is_stuck,
                stuck_reason=stuck_reason,
                current_screen_id=self._current_screen_state.screen_id,
                current_screen_is_new=self._current_screen_state.is_new,
                total_unique_screens=self._current_screen_state.total_screens_discovered,
                screen_dimensions=screen_dimensions,
                ocr_grounding=grounding_overlay.ocr_elements if grounding_overlay else None
            )

            # Emit AI response event
            self._emit_event("on_ai_response_received", run_id, step_number, {
                "actions_count": len(ai_response.actions),
                "signup_completed": ai_response.signup_completed,
                "latency_ms": ai_response.latency_ms
            })
            
            # Save annotated screenshot for debugging (Phase 4)
            try:
                # AI receives full-size image - coordinates are used directly (no scaling)
                actions_dicts = []
                
                # Emit debug log to UI
                self._emit_event("on_debug_log", run_id, step_number, 
                    f"Screen: {original_width}x{original_height} (no scaling)")
                
                for idx, action in enumerate(ai_response.actions):
                    action_data = {}
                    msg = f"Action {idx+1}: {action.action}"
                    
                    # 1. Priority: Use explicit bounding box from AI if provided
                    if action.target_bounding_box:
                        tl = action.target_bounding_box.top_left
                        br = action.target_bounding_box.bottom_right
                        action_data["target_bounding_box"] = {
                            "top_left": list(tl),
                            "bottom_right": list(br)
                        }
                        msg += f" coords [{tl[0]},{tl[1]}]->[{br[0]},{br[1]}]"
                    
                    # 2. Use label_id if provided
                    if action.label_id is not None:
                        action_data["label_id"] = action.label_id
                        msg += f" label [{action.label_id}]"
                        
                        # Resolve label to bounding box for annotation if AI didn't provide coords
                        if "target_bounding_box" not in action_data and grounding_overlay:
                            for element in grounding_overlay.ocr_elements:
                                if element["label"] == action.label_id:
                                    b = element["bounds"] # [x1, y1, x2, y2]
                                    action_data["target_bounding_box"] = {
                                        "top_left": [b[0], b[1]],
                                        "bottom_right": [b[2], b[3]]
                                    }
                                    msg += " (resolved from grounding)"
                                    break
                    
                    self._emit_event("on_debug_log", run_id, step_number, msg)
                    actions_dicts.append(action_data)

                
                self.overlay_renderer.save_annotated(
                    image=screenshot_image,
                    actions=actions_dicts,
                    original_path=screenshot_path
                )
            except Exception as e:
                logger.warning(f"Failed to save annotated screenshot for step {step_number}: {e}")

            # Execute actions
            actions_executed = 0
            
            for i, ai_action in enumerate(ai_response.actions):
                # Resolve coordinates: from label_id OR target_bounding_box
                bounds = None
                
                if ai_action.label_id is not None and grounding_overlay:
                    if ai_action.label_id in grounding_overlay.label_map:
                        center = grounding_overlay.label_map[ai_action.label_id]
                        # Create a tiny bounding box around the center for consistency
                        bounds = (center[0]-5, center[1]-5, center[0]+5, center[1]+5)
                        self._emit_event("on_debug_log", run_id, step_number,
                            f"Resolved Label {ai_action.label_id} to center {center}")
                    else:
                        logger.warning(f"AI provided unknown label_id: {ai_action.label_id}")

                if not bounds and ai_action.target_bounding_box:
                    ai_tl = ai_action.target_bounding_box.top_left
                    ai_br = ai_action.target_bounding_box.bottom_right
                    bounds = (int(ai_tl[0]), int(ai_tl[1]), int(ai_br[0]), int(ai_br[1]))
                
                # Apply top bar offset back to coordinates for device execution
                if bounds and self.top_bar_height > 0:
                    bounds = (
                        bounds[0], 
                        bounds[1] + self.top_bar_height, 
                        bounds[2], 
                        bounds[3] + self.top_bar_height
                    )
                
                if bounds:
                    # Calculate tap center point
                    tap_x = (bounds[0] + bounds[2]) // 2
                    tap_y = (bounds[1] + bounds[3]) // 2
                    self._emit_event("on_debug_log", run_id, step_number,
                        f"EXECUTE {ai_action.action}: tap at ({tap_x}, {tap_y}) [bounds: {bounds}]")
                else:
                    self._emit_event("on_debug_log", run_id, step_number,
                        f"EXECUTE {ai_action.action} (no coordinates required)")

                # Execute action based on type
                if ai_action.action == "click":
                    result = self.action_executor.click(bounds)
                elif ai_action.action == "input":
                    result = self.action_executor.input(bounds, ai_action.input_text)
                    # Hide keyboard after input
                    if result.success:
                        self.appium_driver.hide_keyboard()
                        time.sleep(0.5)  # Wait for keyboard animation
                elif ai_action.action == "long_press":
                    result = self.action_executor.long_press(bounds)
                elif ai_action.action == "scroll_up":
                    result = self.action_executor.scroll_up()
                elif ai_action.action == "scroll_down":
                    result = self.action_executor.scroll_down()
                elif ai_action.action == "scroll_left":
                    result = self.action_executor.swipe_left()
                elif ai_action.action == "scroll_right":
                    result = self.action_executor.swipe_right()
                elif ai_action.action == "back":
                    result = self.action_executor.back()
                elif ai_action.action == "extract_otp":
                    # AI can provide email or hint in input_text
                    result = self.action_executor.extract_otp(email=ai_action.input_text)
                elif ai_action.action == "click_verification_link":
                    # AI can provide link text hint in input_text
                    result = self.action_executor.click_verification_link(link_text=ai_action.input_text)
                else:
                    # Unknown action - skip
                    continue

                actions_executed += 1
                self._emit_event("on_action_executed", run_id, step_number, i, result)

                # Log step action with screen tracking
                # from_screen_id is the screen before action, to_screen_id will be updated after action
                current_screen_id = self._current_screen_state.screen_id if self._current_screen_state else None
                step_log = StepLog(
                    id=None,
                    run_id=run_id,
                    step_number=step_number,
                    timestamp=datetime.now(),
                    from_screen_id=previous_screen_id,
                    to_screen_id=current_screen_id,
                    action_type=ai_action.action,
                    action_description=ai_action.action_desc,
                    target_bbox_json=json.dumps({
                        "top_left": list(ai_action.target_bounding_box.top_left) if ai_action.target_bounding_box else [bounds[0], bounds[1]],
                        "bottom_right": list(ai_action.target_bounding_box.bottom_right) if ai_action.target_bounding_box else [bounds[2], bounds[3]]
                    }) if ai_action.action in ["click", "input", "long_press"] else None,
                    input_text=ai_action.input_text,
                    execution_success=result.success,
                    error_message=str(result.error_message) if result.error_message else None,
                    action_duration_ms=result.duration_ms,
                    ai_response_time_ms=ai_response.latency_ms,  # Use AI response time from response
                    ai_reasoning=ai_action.reasoning
                )
                self.step_log_repository.create_step_log(step_log)

                # Stop executing actions if one fails
                if not result.success:
                    step_success = False
                    break

            # Emit step completed event
            step_duration_ms = (time.time() - step_start_time) * 1000
            self._emit_event("on_step_completed", run_id, step_number, actions_executed, step_duration_ms)

            # Check if signup is completed - if so, stop the crawl
            if ai_response.signup_completed:
                step_success = False

            return step_success

        except Exception as e:
            # Emit step completed with error
            step_duration_ms = (time.time() - step_start_time) * 1000
            self._emit_event("on_step_completed", run_id, step_number, 0, step_duration_ms)
            raise

    def _get_completion_reason(self, run_id: int, step_number: int, start_time: float) -> str:
        """Get the reason for crawl completion.

        Args:
            run_id: Run ID
            step_number: Final step number
            start_time: Start time

        Returns:
            Completion reason string
        """
        if step_number > self.max_crawl_steps:
            return f"Reached maximum steps ({self.max_crawl_steps})"
        
        elapsed_seconds = time.time() - start_time
        if elapsed_seconds >= self.max_crawl_duration_seconds:
            return f"Reached maximum duration ({self.max_crawl_duration_seconds}s)"
        
        return "Completed successfully"

    def _initialize_traffic_capture(self, run_id: int, session_path: str) -> None:
        """Initialize and start traffic capture if enabled.

        Args:
            run_id: Run ID
            session_path: Session directory path
        """
        # Debug: Log the config value being checked
        enable_traffic_capture = self.config_manager.get("enable_traffic_capture", False)
        logger.info(f"Traffic capture enabled in config: {enable_traffic_capture}")
        self._emit_event("on_debug_log", run_id, 0, f"Traffic capture enabled in config: {enable_traffic_capture}")
        
        if not enable_traffic_capture:
            logger.info("Traffic capture is disabled, skipping initialization")
            self._emit_event("on_debug_log", run_id, 0, "Traffic capture is DISABLED, skipping")
            return

        try:
            import asyncio

            # Log additional config values
            app_package = self.config_manager.get("app_package", "")
            pcapdroid_package = self.config_manager.get("pcapdroid_package", "")
            pcapdroid_api_key = self.config_manager.get("pcapdroid_api_key", "")
            logger.info(f"Traffic capture config - app_package: {app_package}, pcapdroid_package: {pcapdroid_package}, api_key_set: {bool(pcapdroid_api_key)}")
            self._emit_event("on_debug_log", run_id, 0, f"Traffic capture config - app_package: {app_package}, pcapdroid: {pcapdroid_package}")

            # Initialize ADB client
            adb_client = ADBClient(
                adb_executable=self.config_manager.get("adb_executable_path", "adb")
            )

            # Initialize traffic capture manager
            self._traffic_capture_manager = TrafficCaptureManager(
                config_manager=self.config_manager,
                adb_client=adb_client,
                session_folder_manager=self.session_folder_manager,
            )
            
            # Verify the manager's enabled state
            logger.info(f"TrafficCaptureManager created, traffic_capture_enabled: {self._traffic_capture_manager.traffic_capture_enabled}")
            self._emit_event("on_debug_log", run_id, 0, f"TrafficCaptureManager created, enabled: {self._traffic_capture_manager.traffic_capture_enabled}")

            # Start capture asynchronously
            async def start_capture():
                return await self._traffic_capture_manager.start_capture_async(
                    run_id=run_id, step_num=1, session_path=session_path
                )

            success, message = asyncio.run(start_capture())
            if success:
                logger.info(f"Traffic capture started for run {run_id}: {message}")
                self._emit_event("on_debug_log", run_id, 0, f"Traffic capture STARTED: {message}")
            else:
                logger.warning(f"Failed to start traffic capture for run {run_id}: {message}")
                self._emit_event("on_debug_log", run_id, 0, f"Traffic capture FAILED: {message}")
        except Exception as e:
            logger.error(f"Error initializing traffic capture: {e}", exc_info=True)
            # Don't fail the crawl if traffic capture fails
            self._traffic_capture_manager = None

    def _initialize_video_recording(self, run_id: int, session_path: str) -> None:
        """Initialize and start video recording if enabled.

        Args:
            run_id: Run ID
            session_path: Session directory path
        """
        # Debug: Log the config value being checked
        enable_video_recording = self.config_manager.get("enable_video_recording", False)
        logger.info(f"Video recording enabled in config: {enable_video_recording}")
        self._emit_event("on_debug_log", run_id, 0, f"Video recording enabled in config: {enable_video_recording}")
        
        if not enable_video_recording:
            logger.info("Video recording is disabled, skipping initialization")
            self._emit_event("on_debug_log", run_id, 0, "Video recording is DISABLED, skipping")
            return

        try:
            # Log additional config values
            app_package = self.config_manager.get("app_package", "")
            logger.info(f"Video recording config - app_package: {app_package}")
            logger.debug(f"[DEBUG] Video recording initialization - app_package: {app_package}")
            self._emit_event("on_debug_log", run_id, 0, f"[DEBUG] Video recording config - app_package: {app_package}")

            # Check AppiumDriver availability
            if not self.appium_driver:
                logger.error("[DEBUG] AppiumDriver is None - cannot initialize video recording")
                self._emit_event("on_debug_log", run_id, 0, "[DEBUG] Video recording FAILED: AppiumDriver is None")
                return
            
            logger.debug(f"[DEBUG] AppiumDriver available: {self.appium_driver is not None}")
            logger.debug(f"[DEBUG] AppiumDriver device_id: {getattr(self.appium_driver, 'device_id', 'N/A')}")
            
            # Check if driver is connected
            driver = getattr(self.appium_driver, '_driver', None)
            if driver is None:
                logger.error("[DEBUG] Appium WebDriver not connected - cannot start video recording")
                self._emit_event("on_debug_log", run_id, 0, "[DEBUG] Video recording FAILED: Appium WebDriver not connected")
                return
            
            logger.debug(f"[DEBUG] Appium WebDriver connected: {driver is not None}")
            logger.debug(f"[DEBUG] Appium WebDriver session_id: {getattr(driver, 'session_id', 'N/A')}")

            # Initialize video recording manager
            logger.debug("[DEBUG] Creating VideoRecordingManager...")
            self._video_recording_manager = VideoRecordingManager(
                appium_driver=self.appium_driver,
                config_manager=self.config_manager,
                session_folder_manager=self.session_folder_manager,
            )
            
            # Verify the manager's enabled state
            logger.info(f"VideoRecordingManager created, video_recording_enabled: {self._video_recording_manager.video_recording_enabled}")
            logger.debug(f"[DEBUG] VideoRecordingManager.video_recording_enabled: {self._video_recording_manager.video_recording_enabled}")
            self._emit_event("on_debug_log", run_id, 0, f"VideoRecordingManager created, enabled: {self._video_recording_manager.video_recording_enabled}")

            # Start recording
            logger.debug(f"[DEBUG] Calling start_recording(run_id={run_id}, step_num=1, session_path={session_path})...")
            success = self._video_recording_manager.start_recording(
                run_id=run_id, step_num=1, session_path=session_path
            )
            logger.debug(f"[DEBUG] start_recording() returned: {success}")
            
            if success:
                logger.info(f"Video recording started for run {run_id}")
                self._emit_event("on_debug_log", run_id, 0, "Video recording STARTED successfully")
            else:
                logger.warning(f"Failed to start video recording for run {run_id}")
                logger.debug("[DEBUG] Video recording start failed - check logs above for details")
                self._emit_event("on_debug_log", run_id, 0, "Video recording FAILED to start")
                self._emit_event("on_debug_log", run_id, 0, "[DEBUG] Check Appium driver connection and device capabilities")
        except Exception as e:
            error_msg = f"Error initializing video recording: {e}"
            logger.error(error_msg, exc_info=True)
            logger.debug(f"[DEBUG] Exception in _initialize_video_recording: {type(e).__name__}: {str(e)}")
            self._emit_event("on_debug_log", run_id, 0, f"[DEBUG] Video recording EXCEPTION: {error_msg}")
            # Don't fail the crawl if video recording fails
            self._video_recording_manager = None

    def _stop_video_recording(self) -> None:
        """Stop video recording and save video file."""
        if not self._video_recording_manager:
            return

        try:
            video_path = self._video_recording_manager.stop_recording_and_save()
            if video_path:
                logger.info(f"Video recording completed. Video file saved: {video_path}")
            else:
                logger.warning("Video recording stopped but video file not saved")
        except Exception as e:
            logger.error(f"Error stopping video recording: {e}", exc_info=True)
            # Don't fail the crawl if video recording stop fails
            # Try to save partial recording
            try:
                partial_path = self._video_recording_manager.save_partial_on_crash()
                if partial_path:
                    logger.info(f"Partial video recording saved: {partial_path}")
            except Exception:
                pass

    def _run_mobsf_analysis(self, run_id: int, session_path: str) -> None:
        """Run MobSF analysis after crawl completion if enabled.

        Args:
            run_id: Run ID
            session_path: Session directory path
        """
        # Debug: Log the config value being checked
        enable_mobsf_analysis = self.config_manager.get("enable_mobsf_analysis", False)
        logger.info(f"MobSF analysis enabled in config: {enable_mobsf_analysis}")
        self._emit_event("on_debug_log", run_id, 0, f"MobSF analysis enabled in config: {enable_mobsf_analysis}")
        
        if not enable_mobsf_analysis:
            logger.info("MobSF analysis is disabled, skipping")
            self._emit_event("on_debug_log", run_id, 0, "MobSF analysis is DISABLED, skipping")
            return

        try:
            # Check MobSF server connectivity before starting
            mobsf_api_url = self.config_manager.get("mobsf_api_url", "http://localhost:8000")
            logger.debug(f"MobSF API URL: {mobsf_api_url}")
            self._emit_event("on_debug_log", run_id, 0, f"[DEBUG] MobSF API URL: {mobsf_api_url}")
            
            # Try to verify server is reachable
            import requests
            try:
                test_url = mobsf_api_url.rstrip("/") + "/api/v1/"
                response = requests.get(test_url, timeout=5)
                logger.debug(f"MobSF server connectivity check: {response.status_code}")
                self._emit_event("on_debug_log", run_id, 0, f"[DEBUG] MobSF server reachable (status: {response.status_code})")
            except requests.exceptions.ConnectionError as e:
                logger.error(f"MobSF server not reachable at {mobsf_api_url}: {e}")
                self._emit_event("on_debug_log", run_id, 0, f"[DEBUG] MobSF server NOT reachable: {e}")
                self._emit_event("on_debug_log", run_id, 0, "[DEBUG] MobSF analysis will fail - server not running or unreachable")
            except Exception as e:
                logger.warning(f"Could not verify MobSF server connectivity: {e}")
                self._emit_event("on_debug_log", run_id, 0, f"[DEBUG] MobSF server connectivity check failed: {e}")

            # Initialize ADB client
            adb_client = ADBClient(
                adb_executable=self.config_manager.get("adb_executable_path", "adb")
            )

            # Initialize MobSF manager
            logger.debug("Initializing MobSFManager...")
            self._emit_event("on_debug_log", run_id, 0, "[DEBUG] Initializing MobSFManager...")
            self._mobsf_manager = MobSFManager(
                config_manager=self.config_manager,
                adb_client=adb_client,
                session_folder_manager=self.session_folder_manager,
            )
            logger.debug("MobSFManager initialized successfully")
            self._emit_event("on_debug_log", run_id, 0, "[DEBUG] MobSFManager initialized successfully")

            # Get package name from run
            run = self.run_repository.get_run_by_id(run_id)
            if not run:
                logger.error(f"Run {run_id} not found for MobSF analysis")
                self._emit_event("on_debug_log", run_id, 0, f"[DEBUG] MobSF analysis FAILED: Run {run_id} not found")
                return

            package_name = run.app_package
            logger.debug(f"Starting MobSF analysis for package: {package_name}")
            self._emit_event("on_debug_log", run_id, 0, f"[DEBUG] Starting MobSF analysis for package: {package_name}")

            # Define log callback for CLI output
            def log_callback(message: str, color: Optional[str] = None):
                logger.info(message)
                # Also emit to event listeners if needed
                self._emit_event("on_mobsf_log", run_id, message)

            # Perform complete scan
            logger.debug("Calling perform_complete_scan...")
            self._emit_event("on_debug_log", run_id, 0, "[DEBUG] Calling MobSF perform_complete_scan...")
            success, summary = self._mobsf_manager.perform_complete_scan(
                package_name=package_name,
                run_id=run_id,
                session_path=session_path,
                log_callback=log_callback,
            )
            
            logger.debug(f"MobSF analysis result: success={success}")
            self._emit_event("on_debug_log", run_id, 0, f"[DEBUG] MobSF analysis result: success={success}")

            if success:
                logger.info(f"MobSF analysis completed successfully for run {run_id}")
                self._emit_event("on_debug_log", run_id, 0, f"[DEBUG] MobSF analysis completed successfully for run {run_id}")
                # Store security score in run_stats if available
                if "security_score" in summary and isinstance(
                    summary["security_score"], dict
                ):
                    score = summary["security_score"].get("score")
                    if score:
                        try:
                            # Update run_stats with security score
                            from mobile_crawler.infrastructure.database import DatabaseManager
                            db_manager = DatabaseManager()
                            conn = db_manager.get_connection()
                            cursor = conn.cursor()
                            cursor.execute(
                                """
                                INSERT OR REPLACE INTO run_stats (run_id, mobsf_security_score)
                                VALUES (?, ?)
                                """,
                                (run_id, float(score) if isinstance(score, (int, float)) else None),
                            )
                            conn.commit()
                            logger.info(f"MobSF security score stored: {score}")
                        except Exception as e:
                            logger.warning(f"Failed to store MobSF score: {e}")
            else:
                error_summary = summary.get('error', 'Unknown error')
                logger.warning(f"MobSF analysis failed for run {run_id}: {error_summary}")
                self._emit_event("on_debug_log", run_id, 0, f"[DEBUG] MobSF analysis FAILED: {error_summary}")
        except Exception as e:
            error_msg = f"Error running MobSF analysis: {e}"
            logger.error(error_msg, exc_info=True)
            self._emit_event("on_debug_log", run_id, 0, f"[DEBUG] MobSF analysis EXCEPTION: {error_msg}")
            self._emit_event("on_debug_log", run_id, 0, "[DEBUG] MobSF analysis FAILED - check server status and logs")
            # Don't fail the crawl if MobSF analysis fails
            self._mobsf_manager = None

    def _stop_traffic_capture(self, run_id: int, step_num: int) -> None:
        """Stop traffic capture and pull PCAP file.

        Args:
            run_id: Run ID
            step_num: Final step number
        """
        if not self._traffic_capture_manager:
            return

        try:
            import asyncio

            async def stop_capture():
                return await self._traffic_capture_manager.stop_capture_and_pull_async(
                    run_id, step_num
                )

            pcap_path = asyncio.run(stop_capture())
            if pcap_path:
                logger.info(f"Traffic capture completed. PCAP file saved: {pcap_path}")
            else:
                logger.warning(f"Traffic capture stopped but PCAP file not saved")
        except Exception as e:
            logger.error(f"Error stopping traffic capture: {e}", exc_info=True)
            # Don't fail the crawl if traffic capture stop fails

    def _emit_event(self, event_method: str, *args, **kwargs) -> None:
        """Emit an event to all listeners.

        Args:
            event_method: Name of the event method to call
            *args: Positional arguments for the event
            **kwargs: Keyword arguments for the event
        """
        for listener in self.event_listeners:
            try:
                method = getattr(listener, event_method)
                method(*args, **kwargs)
            except Exception as e:
                # Don't let listener exceptions break the crawler
                # In a real implementation, you might want to log this
                pass