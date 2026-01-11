"""Main crawler loop orchestration."""

import time
import logging
from datetime import datetime
from typing import List, Optional
import threading

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.core.crawl_state_machine import CrawlState, CrawlStateMachine
from mobile_crawler.core.crawler_event_listener import CrawlerEventListener
from mobile_crawler.domain.action_executor import ActionExecutor
from mobile_crawler.domain.models import ActionResult
from mobile_crawler.infrastructure.ai_interaction_service import AIInteractionService
from mobile_crawler.infrastructure.appium_driver import AppiumDriver
from mobile_crawler.infrastructure.run_repository import RunRepository
from mobile_crawler.infrastructure.screenshot_capture import ScreenshotCapture
from mobile_crawler.infrastructure.step_log_repository import StepLog, StepLogRepository

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
        event_listeners: Optional[List[CrawlerEventListener]] = None
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
        self.event_listeners = event_listeners or []
        
        # Threading support
        self._crawl_thread: Optional[threading.Thread] = None
        self._current_run_id: Optional[int] = None
        
        # Target app package (set when run starts)
        self._target_package: Optional[str] = None

        # Configuration
        self.max_crawl_steps = self.config_manager.get('max_crawl_steps', 15)
        self.max_crawl_duration_seconds = self.config_manager.get('max_crawl_duration_seconds', 600)

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

    def run(self, run_id: int) -> None:
        """Run the crawler loop for the given run.

        Args:
            run_id: The run ID to execute

        Raises:
            Exception: If the crawl fails
        """
        try:
            # Get run details
            run = self.run_repository.get_run(run_id)
            if not run:
                raise ValueError(f"Run {run_id} not found")

            # Store target package for app context validation
            self._target_package = run.app_package

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
                    if step_success:
                        step_number += 1
                    else:
                        # Step failed but don't exit - continue to next step unless stopping
                        step_number += 1
                except Exception as e:
                    # Fail the crawl
                    raise

            # Complete crawl
            total_duration_ms = (time.time() - start_time) * 1000
            reason = self._get_completion_reason(run_id, step_number, start_time)

            self.state_machine.transition_to(CrawlState.STOPPING)
            self._emit_event("on_state_changed", run_id, "running", "stopping")

            # Finalize run record with stats
            total_steps = step_number - 1  # steps are 1-indexed
            self.run_repository.update_run_stats(
                run_id=run_id,
                status='COMPLETED',
                end_time=datetime.now(),
                total_steps=total_steps,
                unique_screens=total_steps  # Simplified: assume each step is unique screen
            )

            self.state_machine.transition_to(CrawlState.STOPPED)
            self._emit_event("on_state_changed", run_id, "stopping", "stopped")

            self._emit_event("on_crawl_completed", run_id, step_number - 1, total_duration_ms, reason)

        except Exception as e:
            # Handle initialization or other critical errors
            if self.state_machine.state != CrawlState.ERROR:
                self.state_machine.transition_to(CrawlState.ERROR)
                self._emit_event("on_state_changed", run_id, self.state_machine.state.value, "error")
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
            # Capture screenshot (returns image, path, AI-optimized base64, and scale factor)
            screenshot_image, screenshot_path, screenshot_b64, scale_factor = self.screenshot_capture.capture_full()

            self._emit_event("on_screenshot_captured", run_id, step_number, screenshot_path)

            # Check if we're stuck (simplified - would need more complex logic)
            is_stuck = False
            stuck_reason = None
            # TODO: Implement stuck detection logic

            # Get AI actions
            ai_response = self.ai_interaction_service.get_next_actions(
                run_id=run_id,
                step_number=step_number,
                screenshot_b64=screenshot_b64,
                screenshot_path=screenshot_path,
                is_stuck=is_stuck,
                stuck_reason=stuck_reason
            )

            # Execute actions
            actions_executed = 0
            for i, ai_action in enumerate(ai_response.actions):
                # Convert bounding box to tuple format expected by action executor
                # IMPORTANT: Scale coordinates back to original screen dimensions
                # AI sees downscaled image, so its coordinates are smaller
                # screen_coord = ai_coord / scale_factor
                bounds = (
                    int(ai_action.target_bounding_box.top_left[0] / scale_factor),
                    int(ai_action.target_bounding_box.top_left[1] / scale_factor),
                    int(ai_action.target_bounding_box.bottom_right[0] / scale_factor),
                    int(ai_action.target_bounding_box.bottom_right[1] / scale_factor)
                )
                
                if scale_factor < 1.0:
                    logger.debug(f"Scaled coordinates from AI: {ai_action.target_bounding_box} -> screen: {bounds} (scale: {scale_factor})")

                # Execute action based on type
                if ai_action.action == "click":
                    result = self.action_executor.click(bounds)
                elif ai_action.action == "input":
                    result = self.action_executor.input(bounds, ai_action.input_text)
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
                else:
                    # Unknown action - skip
                    continue

                actions_executed += 1
                self._emit_event("on_action_executed", run_id, step_number, i, result)

                # Log step action
                step_log = StepLog(
                    id=None,
                    run_id=run_id,
                    step_number=step_number,
                    timestamp=datetime.now(),
                    from_screen_id=None,  # TODO: Implement screen tracking
                    to_screen_id=None,    # TODO: Implement screen tracking
                    action_type=ai_action.action,
                    action_description=ai_action.action_desc,
                    target_bbox_json=str({
                        "top_left": list(ai_action.target_bounding_box.top_left),
                        "bottom_right": list(ai_action.target_bounding_box.bottom_right)
                    }) if ai_action.action in ["click", "input", "long_press"] else None,
                    input_text=ai_action.input_text,
                    execution_success=result.success,
                    error_message=str(result.error_message) if result.error_message else None,
                    action_duration_ms=result.duration_ms,
                    ai_response_time_ms=None,  # TODO: Track AI response time
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