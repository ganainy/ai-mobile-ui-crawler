#!/usr/bin/env python3
"""
Crawler Loop Module
==================

This module implements the core AI-powered mobile app exploration loop.

Architecture:
    ┌─────────────┐
    │CrawlerLoop  │ <─ (Injected Dependencies)
    ├─────────────┤
    │ • Manages   │
    │   lifecycle │
    │ • Uses      │
    │   managers  │
    └──────┬──────┘
           │
      ┌────┴────┬────────┬──────────┐
      ▼         ▼        ▼          ▼
  AgentAssist Database Screen  Traffic
              Manager  State   Capture
              
    (All managers are injected via constructor)

Flow:
    1. Factory (run_crawler_loop) creates components
    2. CrawlerLoop takes ownership
    3. Loop: capture → decide → execute via delegates
    4. Cleanup resources via Context Manager

Configuration:
    Required config keys:
    - APP_PACKAGE: Target app package name
    - APP_ACTIVITY: Launch activity
    - AI_PROVIDER: AI service (openai, anthropic, etc.)
    - MAX_CRAWL_STEPS: Step limit (optional)
"""

# Standard library imports
import asyncio
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union

# Local imports
try:
    from config.app_config import Config
    from domain.agent_assistant import AgentAssistant
    from core.controller import (
        FlagController, 
        DEFAULT_SHUTDOWN_FLAG, 
        DEFAULT_PAUSE_FLAG,
        DEFAULT_STEP_BY_STEP_FLAG,
        DEFAULT_CONTINUE_FLAG
    )
    from domain.app_context_manager import AppContextManager
    from domain.traffic_capture_manager import TrafficCaptureManager
    from domain.video_recording_manager import VideoRecordingManager
    from core.stuck_detector import StuckDetector
    from core.crawl_context_builder import CrawlContextBuilder
    from core.crawl_logger import CrawlLogger
    from infrastructure.database import DatabaseManager
    from domain.screen_state_manager import ScreenStateManager
except ImportError as e:
    print(f"FATAL: Import error: {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

logger = logging.getLogger(__name__)

# ============================================================================
# Constants and Enums
# ============================================================================

class PauseMode(Enum):
    """Pause mode enumeration."""
    CONTINUOUS = "continuous"  # Run without pausing
    STEP_BY_STEP = "step_by_step"  # Pause after each step
    MANUAL_PAUSE = "manual_pause"  # Paused via pause flag


class CrawlerState(Enum):
    """Represents the current state of the crawler."""
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPING = auto()
    STOPPED = auto()
    ERROR = auto()


class RunStatus:
    """Status values for crawler run completion."""
    COMPLETED = "COMPLETED"
    INTERRUPTED = "INTERRUPTED"
    FAILED = "FAILED"
    RUNNING = "RUNNING"





# ============================================================================
# Interfaces / Protocols
# ============================================================================

class CrawlerEventListener(Protocol):
    """Protocol for listening to crawler events."""
    
    def on_step_start(self, step: int) -> None:
        """Called when a new step starts."""
        ...

    def on_screenshot_captured(self, path: str, blocked: bool = False) -> None:
        """Called when a screenshot is captured and saved."""
        ...

    def on_status_change(self, message: str) -> None:
        """Called when status message should be displayed."""
        ...

    def on_error(self, message: str) -> None:
        """Called when a critical error occurs."""
        ...


class StdoutEventListener:
    """Default listener that prints UI protocol messages to stdout via JSON IPC."""
    
    def _emit_json(self, kind: str, data: Any) -> None:
        """Helper to emit structured JSON event for IPC."""
        try:
            payload = {
                "type": "ui_event",
                "kind": kind,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            print(f"JSON_IPC:{json.dumps(payload)}", flush=True)
        except Exception:
            pass

    def on_step_start(self, step: int) -> None:
        self._emit_json('step', step)

    def on_screenshot_captured(self, path: str, blocked: bool = False) -> None:
        self._emit_json('screenshot', {'path': path, 'blocked': blocked})

    def on_status_change(self, message: str) -> None:
        self._emit_json('status', message)

    def on_error(self, message: str) -> None:
        self._emit_json('status', f"ERROR: {message}")
        # Keep stderr for fatal errors as they might not be captured by stdout pipe if app crashes hard
        print(f"FATAL ERROR: {message}", file=sys.stderr, flush=True)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class RuntimeStats:
    """Runtime statistics tracked during crawl execution."""
    stuck_detection_count: int = 0
    ai_retry_count: int = 0
    element_not_found_count: int = 0
    app_crash_count: int = 0
    context_loss_count: int = 0
    multi_action_batch_count: int = 0
    total_batch_actions: int = 0
    image_context_enabled: bool = False
    ai_provider: str = "unknown"
    model_type: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'stuck_detection_count': self.stuck_detection_count,
            'ai_retry_count': self.ai_retry_count,
            'element_not_found_count': self.element_not_found_count,
            'app_crash_count': self.app_crash_count,
            'context_loss_count': self.context_loss_count,
            'multi_action_batch_count': self.multi_action_batch_count,
            'total_batch_actions': self.total_batch_actions,
            'image_context_enabled': self.image_context_enabled,
            'ai_provider': self.ai_provider,
            'model_type': self.model_type,
        }


# ============================================================================
# Main Crawler Loop Class
# ============================================================================

class CrawlerLoop:
    """
    Main crawler loop that orchestrates AI decision-making and action execution.
    
    Features:
    - Dependency Injection: All managers injected via constructor
    - Observer Pattern: UI updates via Listener interface
    - Context Manager: Guaranteed cleanup
    - State Machine: Strict state tracking
    """
    
    def __init__(
        self,
        config: Config,
        listener: CrawlerEventListener,
        flag_controller: FlagController,
        agent_assistant: AgentAssistant,
        db_manager: DatabaseManager,
        screen_state_manager: ScreenStateManager,
        app_context_manager: Optional[AppContextManager] = None,
        traffic_capture_manager: Optional[TrafficCaptureManager] = None,
        video_recording_manager: Optional[VideoRecordingManager] = None,
        run_id: Optional[int] = None
    ):
        """
        Initialize the crawler loop with injected dependencies.
        
        Args:
            config: Application configuration
            listener: Event listener for UI updates
            flag_controller: Controller for pause/shutdown flags
            agent_assistant: AI decision maker
            db_manager: Database persistence manager
            screen_state_manager: Screen state processor
            app_context_manager: App lifecycle manager (optional)
            traffic_capture_manager: Network capture manager (optional)
            video_recording_manager: Screen recorder (optional)
            run_id: DB ID for the current run (optional)
        """
        self.config = config
        self.listener = listener
        self.flag_controller = flag_controller
        self.agent_assistant = agent_assistant
        self.db_manager = db_manager
        self.screen_state_manager = screen_state_manager
        self.app_context_manager = app_context_manager
        self.traffic_capture_manager = traffic_capture_manager
        self.video_recording_manager = video_recording_manager
        self.current_run_id = run_id
        
        self.state = CrawlerState.UNINITIALIZED
        self.pause_mode = PauseMode.CONTINUOUS
        self.waiting_for_continue = False
        
        # Specialized components (internally managed for now, could be injected)
        self.stuck_detector = StuckDetector(config)
        self.context_builder = CrawlContextBuilder(db_manager, config)
        self.crawl_logger = CrawlLogger(db_manager, config)
        
        # Crawler state variables
        self.step_count = 0
        self.current_screen_visit_count = 0
        self.current_composite_hash = ""
        self.last_action_feedback: Optional[str] = None
        self.current_from_screen_id: Optional[int] = None
        
        # Runtime statistics
        self.runtime_stats = RuntimeStats(
            image_context_enabled=config.get('ENABLE_IMAGE_CONTEXT', False),
            ai_provider=config.get('AI_PROVIDER', 'unknown'),
            model_type=config.get('DEFAULT_MODEL_TYPE', 'unknown'),
        )
        
        # Threading events
        self._shutdown_event = threading.Event()
        self._pause_event = threading.Event()
        
        # Configuration validity check
        wait_after_action = config.get('WAIT_AFTER_ACTION')
        if wait_after_action is None:
            raise ValueError("WAIT_AFTER_ACTION must be set in configuration")
        self.wait_after_action = float(wait_after_action)

    # ========================================================================
    # Context Manager Support
    # ========================================================================
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup_resources()
        return False
    
    # ========================================================================
    # Lifecycle Methods
    # ========================================================================
    
    def initialize(self) -> bool:
        """
        Perform final initialization steps (e.g. app launch).
        Most components are already initialized via DI.
        """
        try:
            self.state = CrawlerState.INITIALIZING
            self.listener.on_status_change("Initializing crawler components...")
            
            # Launch App
            if self.app_context_manager:
                if not self.app_context_manager.launch_and_verify_app():
                    logger.warning("Failed to launch app at start, but continuing...")
                else:
                    logger.info("Target app launched successfully")
            
            self.state = CrawlerState.RUNNING
            return True
            
        except Exception as e:
            logger.error(f"Initialization error: {e}", exc_info=True)
            self.state = CrawlerState.ERROR
            self.listener.on_error(str(e))
            return False

    def run(self, max_steps: Optional[int] = None, max_duration_seconds: Optional[int] = None):
        """
        Execute the main crawler loop.
        
        Args:
            max_steps: Maximum number of steps to execute (for step-based crawl mode)
            max_duration_seconds: Maximum duration in seconds (for time-based crawl mode)
        """
        if self.state != CrawlerState.RUNNING:
            logger.warning(f"Run called but state is {self.state}, attempting re-init")
            if not self.initialize():
                return

        # Check initial pause mode
        self._update_pause_mode()
        if self.pause_mode == PauseMode.STEP_BY_STEP:
            logger.info("Starting in STEP-BY-STEP mode")
            self.listener.on_status_change("Status: Starting in step-by-step mode")

        # Determine crawl mode
        crawl_mode = self.config.get('CRAWL_MODE', 'steps')
        if crawl_mode == 'time' and max_duration_seconds:
            logger.info(f"Starting crawl loop. Mode: time, Duration: {max_duration_seconds}s")
        else:
            logger.info(f"Starting crawl loop. Mode: steps, Max steps: {max_steps}")
        self.listener.on_status_change("Crawler started")
        
        # Start background tasks
        self._start_traffic_capture()
        self._start_video_recording()
        self._update_run_status(RunStatus.RUNNING)
        
        # Track start time for time-based crawl mode
        crawl_start_time = time.time()
        
        try:
            while True:
                # Check time-based termination condition
                if crawl_mode == 'time' and max_duration_seconds:
                    elapsed_time = time.time() - crawl_start_time
                    if elapsed_time >= max_duration_seconds:
                        logger.info(f"Max duration reached: {max_duration_seconds}s (elapsed: {elapsed_time:.1f}s)")
                        self._update_run_status(RunStatus.COMPLETED)
                        self.listener.on_status_change(f"Max duration reached ({max_duration_seconds}s)")
                        break
                # Check step-based termination condition (only for step mode)
                elif crawl_mode == 'steps' and max_steps and self.step_count >= max_steps:
                    logger.info(f"Max steps reached: {max_steps}")
                    self._update_run_status(RunStatus.COMPLETED)
                    self.listener.on_status_change("Max steps reached")
                    break
                
                if not self.run_step():
                    logger.info("Crawler stopped (run_step returned False)")
                    status = RunStatus.INTERRUPTED if self._check_shutdown_flag() else RunStatus.FAILED
                    self._update_run_status(status)
                    self.listener.on_status_change("Crawler stopped")
                    break
                
                # Wait between steps
                if not self._wait_with_check(self.wait_after_action):
                    logger.info("Shutdown requested during wait")
                    self._update_run_status(RunStatus.INTERRUPTED)
                    break
                    
        except KeyboardInterrupt:
            logger.info("Crawler interrupted by user")
            self._update_run_status(RunStatus.INTERRUPTED)
            self.listener.on_status_change("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error in crawler loop: {e}", exc_info=True)
            self._update_run_status(RunStatus.FAILED)
            self.listener.on_error(str(e))
            self.state = CrawlerState.ERROR
        finally:
            self.state = CrawlerState.STOPPED
            self._cleanup_resources()

    def run_step(self) -> bool:
        """
        Execute a single crawler exploration step.
        """
        try:
            # 0. Update Pause Mode
            self._update_pause_mode()

            # 1. Check Flags (Shutdown / Manual Pause)
            if not self._check_continue_conditions():
                return False
            
            # 2. Increment Step
            self._increment_step()
            
            # 3. Verify App Context
            if not self._verify_app_context():
                return self._handle_step_completion()
            
            # 4. Capture Screen
            screen_state = self._capture_and_record_screen()
            if not screen_state:
                return self._handle_step_completion()
            
            # 5. AI Decision
            ai_result = self._get_ai_decision(screen_state)
            if not ai_result:
                return self._handle_step_completion()
                
            action_data, ai_decision_time, token_count, ai_input_prompt, _ = ai_result
            
            # 6. Execute Actions
            success, success_list, exec_count, error_msg, find_time = self._execute_actions(
                action_data, screen_state
            )
            
            # Determine outcome string
            if success:
                outcome = "Action executed successfully"
                # If it was a batch execution
                if exec_count > 1:
                     outcome = f"Executed {sum(success_list)}/{exec_count} actions successfully"
            else:
                outcome = f"Failed: {error_msg}" if error_msg else "Action execution failed"
                
            self.last_action_feedback = outcome
            
            # Update journal with execution results
            self._update_journal_after_step(action_data, outcome, screen_state=screen_state)
            
            # 7. Record Results
            self._record_step_results(
                screen_state.id, 
                action_data, 
                success, 
                success_list,
                ai_decision_time, 
                find_time,
                error_msg,
                token_count,
                ai_input_prompt
            )
            
            # 8. Step-by-Step Pause Check
            return self._handle_step_completion()
            
        except Exception as e:
            logger.error(f"Error in run_step: {e}", exc_info=True)
            self.last_action_feedback = f"System error: {str(e)}"
            self.runtime_stats.app_crash_count += 1 
            self.listener.on_status_change(f"Step error: {str(e)}")
            return self._handle_step_completion()

    # ========================================================================
    # Internal Helpers
    # ========================================================================

    def _handle_step_completion(self) -> bool:
        """
        Handle end-of-step logic (pausing if needed).
        Returns True if execution should continue, False if shutdown requested.
        """
        if self.pause_mode == PauseMode.STEP_BY_STEP:
             return self._wait_for_step_continue()
        return True

    def _check_shutdown_flag(self) -> bool:
        return self.flag_controller.is_shutdown_flag_present()

    def _check_pause_flag(self) -> bool:
        return self.flag_controller.is_pause_flag_present()
    
    def _check_step_by_step_flag(self) -> bool:
        return self.flag_controller.is_step_by_step_flag_present()
    
    def _check_continue_flag(self) -> bool:
        return self.flag_controller.is_continue_flag_present()

    def _clear_continue_flag(self) -> None:
        self.flag_controller.remove_continue_flag()

    def _update_pause_mode(self) -> None:
        """Update pause mode logic based on flags."""
        if self._check_step_by_step_flag():
            if self.pause_mode != PauseMode.STEP_BY_STEP:
                self.pause_mode = PauseMode.STEP_BY_STEP
                logger.info("Switched to STEP-BY-STEP mode")
                self.listener.on_status_change("Status: Step-by-step mode ENABLED")
        elif self._check_pause_flag():
            self.pause_mode = PauseMode.MANUAL_PAUSE
        else:
            if self.pause_mode != PauseMode.CONTINUOUS:
                self.pause_mode = PauseMode.CONTINUOUS
                logger.info("Switched to CONTINUOUS mode")
                self.listener.on_status_change("Status: Step-by-step mode DISABLED")

    def _wait_for_step_continue(self) -> bool:
        """
        Wait until continue flag is set, or shutdown/mode change.
        Returns True to continue, False to stop (shutdown).
        """
        if not self.waiting_for_continue:
            self.waiting_for_continue = True
            logger.info(f"Step {self.step_count} completed. Waiting for continue signal...")
            self.listener.on_status_change(f"Paused at step {self.step_count} - Waiting (Step-By-Step)")
        
        while True:
            # Check shutdown
            if self._check_shutdown_flag():
                return False
            
            # Check if mode changed to continuous (flag removed)
            if not self._check_step_by_step_flag():
                self.waiting_for_continue = False
                self._update_pause_mode()
                return True
                
            # Check continue signal
            if self._check_continue_flag():
                self._clear_continue_flag()
                self.waiting_for_continue = False
                self.listener.on_status_change("Resuming execution...")
                return True
                
            time.sleep(0.2)

    def _wait_while_paused(self) -> None:
        if self._check_pause_flag():
            self.listener.on_status_change("Paused")
            self.state = CrawlerState.PAUSED
            while self._check_pause_flag() and not self._check_shutdown_flag():
                # Allow stepping through manual pause
                if self._check_continue_flag():
                     self._clear_continue_flag()
                     break
                time.sleep(0.5)
            self.state = CrawlerState.RUNNING
            self.listener.on_status_change("Resuming")

    def _check_continue_conditions(self) -> bool:
        if self._check_shutdown_flag():
            return False
        if self._check_pause_flag():
            self._wait_while_paused()
            if self._check_shutdown_flag():
                return False
        return True

    def _wait_with_check(self, seconds: float) -> bool:
        start_time = time.time()
        while (time.time() - start_time) < seconds:
            if not self._check_continue_conditions():
                return False
            time.sleep(0.1)
        return True

    def _increment_step(self) -> None:
        self.step_count += 1
        self.listener.on_step_start(self.step_count)

    def _verify_app_context(self) -> bool:
        if not self.app_context_manager:
            return True
        
        if not self.app_context_manager.ensure_in_app():
            logger.warning("Failed to ensure app context - skipping step")
            self.last_action_feedback = "App context check failed"
            self.runtime_stats.context_loss_count += 1
            return False
            
        return True

    def _capture_and_record_screen(self) -> Optional[Any]:
        candidate_screen = self.screen_state_manager.get_current_screen_representation(
            self.current_run_id, self.step_count
        )
        
        if not candidate_screen:
            logger.error("Failed to get current screen state")
            return None
        
        # Save screenshot for UI (if available)
        if candidate_screen.screenshot_path and candidate_screen.screenshot_bytes:
            try:
                os.makedirs(os.path.dirname(candidate_screen.screenshot_path), exist_ok=True)
                with open(candidate_screen.screenshot_path, "wb") as f:
                    f.write(candidate_screen.screenshot_bytes)
                
                self.listener.on_screenshot_captured(
                    candidate_screen.screenshot_path,
                    candidate_screen.is_screenshot_blocked
                )
            except Exception as e:
                logger.warning(f"Failed to save UI screenshot: {e}")
        elif candidate_screen.is_screenshot_blocked:
            # No screenshot but FLAG_SECURE is active - notify UI to show the blocked message
            self.listener.on_screenshot_captured(None, True)
        
        # Record state
        final_screen, visit_info = self.screen_state_manager.process_and_record_state(
            candidate_screen, 
            self.current_run_id, 
            self.step_count, 
            increment_visit_count=False
        )
        
        self.current_from_screen_id = final_screen.id
        self.current_composite_hash = final_screen.composite_hash
        self.current_screen_visit_count = visit_info.get("visit_count_this_run", 0)
        
        return final_screen

    def _get_ai_decision(self, screen_state: Any) -> Optional[Tuple[Dict, float, Any, str, str]]:
        if not self._check_continue_conditions():
            return None
            
        from_screen_id = screen_state.id
        exploration_journal = []
        if self.db_manager and self.current_run_id:
            journal_str = self.db_manager.get_exploration_journal(self.current_run_id) or "[]"
            try:
                exploration_journal = json.loads(journal_str)
            except (json.JSONDecodeError, TypeError):
                exploration_journal = []
            
        # Stuck detection
        action_history, visited_screens, current_screen_actions = (
            self.context_builder.get_crawl_context(self.current_run_id, from_screen_id)
        )
        is_stuck, stuck_reason = self.stuck_detector.check_if_stuck(
            from_screen_id, self.current_screen_visit_count, action_history, current_screen_actions
        )
        if is_stuck:
            self.runtime_stats.stuck_detection_count += 1
            
        self.crawl_logger.log_ai_context(
            self.step_count, is_stuck, stuck_reason, action_history,
            visited_screens, from_screen_id, self.current_screen_visit_count, 
            current_screen_actions
        )
        
        # Call AI
        start_time = time.time()
        action_result = self.agent_assistant._get_next_action_langchain(
            screenshot_bytes=screen_state.screenshot_bytes,
            xml_context=screen_state.xml_content or "",
            current_screen_actions=current_screen_actions,
            current_screen_id=from_screen_id,
            current_screen_visit_count=self.current_screen_visit_count,
            current_composite_hash=self.current_composite_hash,
            last_action_feedback=self.last_action_feedback,
            is_stuck=is_stuck,
            stuck_reason=stuck_reason if is_stuck else None,
            ocr_results=screen_state.ocr_results if screen_state else None,
            exploration_journal=exploration_journal,
            is_synthetic_screenshot=getattr(screen_state, 'is_synthetic_screenshot', False)
        )
        decision_time = time.time() - start_time
        
        if not action_result:
            self.crawl_logger.log_step_to_db(
                self.current_run_id, self.step_count, from_screen_id, None, None,
                "AI decision failed", False, decision_time * 1000.0, None, None, None,
                "AI did not return a valid action"
            )
            self.last_action_feedback = "AI decision failed"
            self.runtime_stats.ai_retry_count += 1
            return None
            
        action_data, _, token_count, input_prompt = action_result
            
        self._handle_signup_completion(action_data)
        
        if not self._check_continue_conditions():
            return None
            
        return (action_data, decision_time, token_count, input_prompt, screen_state)

    def _handle_signup_completion(self, action_data: Dict[str, Any]) -> None:
        if not action_data.get("signup_completed"):
            return
        
        try:
            from infrastructure.credential_store import get_credential_store
            app = self.config.get("APP_PACKAGE")
            email = self.config.get("TEST_EMAIL")
            pwd = self.config.get("TEST_PASSWORD")
            name = self.config.get("TEST_NAME")
            
            if app and email and pwd:
                store = get_credential_store()
                if store.store_credentials(app, email, pwd, name, True):
                    logger.info("Stored credentials after signup")
                    self.last_action_feedback = "Signup completed! Credentials saved."
        except Exception as e:
            logger.error(f"Error storing credentials: {e}")

    def _update_journal_after_step(self, action_data: Dict[str, Any], outcome: str, screen_state: Any = None) -> None:
        """Update exploration journal with completed action and outcome.
        
        Enhanced format includes:
        - step: Step number for temporal context
        - screen: Activity name for screen context
        - action: Description of action (prefers AI's action_desc if provided)
        - reasoning: AI's reasoning for the action
        - outcome: Execution result (success/failure)
        """
        if not self.db_manager or not self.current_run_id:
            return
            
        try:
            # Load existing journal
            journal_str = self.db_manager.get_exploration_journal(self.current_run_id) or "[]"
            journal = []
            try:
                journal = json.loads(journal_str)
            except (json.JSONDecodeError, TypeError):
                journal = []
            
            if not isinstance(journal, list):
                journal = []
                 
            # Helper to resolve OCR target IDs to actual text
            def resolve_target(tgt: Any) -> str:
                if not tgt:
                    return ""
                # Resolve OCR text from ocr_X format
                if screen_state and str(tgt).startswith("ocr_") and hasattr(screen_state, 'ocr_results') and screen_state.ocr_results:
                    try:
                        parts = str(tgt).split('_')
                        if len(parts) > 1:
                            idx = int(parts[1])
                            if 0 <= idx < len(screen_state.ocr_results):
                                text = screen_state.ocr_results[idx].get('text')
                                if text:
                                    return f"'{text}'"
                    except Exception:
                        pass
                return str(tgt)
            
            # Extract screen context
            screen_context = "Unknown"
            if screen_state and hasattr(screen_state, 'activity_name') and screen_state.activity_name:
                # Simplify activity name (remove package prefix if present)
                activity = screen_state.activity_name
                if '.' in activity:
                    activity = activity.split('.')[-1]
                screen_context = activity
            
            # Build action description and extract reasoning
            action_desc = None
            reasoning = None
            
            # Handle ActionBatch format (list of actions)
            if "actions" in action_data and isinstance(action_data["actions"], list) and action_data["actions"]:
                count = len(action_data["actions"])
                first = action_data["actions"][0]
                
                # Prefer AI's action_desc if provided
                action_desc = first.get("action_desc")
                reasoning = first.get("reasoning")
                
                # Fall back to system-generated description
                if not action_desc:
                    op = first.get("action", "unknown")
                    raw_target = first.get("target_identifier") or first.get("input_text") or ""
                    target = resolve_target(raw_target)
                    # Truncate long targets
                    if len(str(target)) > 25:
                        target = str(target)[:22] + "..."
                    
                    if count > 1:
                        action_desc = f"{op} {target} (+{count-1} more)"
                    else:
                        action_desc = f"{op} {target}"
                        
            # Handle legacy single action format
            elif "action" in action_data:
                action_desc = action_data.get("action_desc")
                reasoning = action_data.get("reasoning")
                
                if not action_desc:
                    op = action_data.get("action")
                    raw_target = action_data.get("target_identifier") or action_data.get("input_text") or ""
                    target = resolve_target(raw_target)
                    if len(str(target)) > 25:
                        target = str(target)[:22] + "..."
                    action_desc = f"{op} {target}"
            
            # Build enhanced journal entry
            entry = {
                "step": self.step_count,
                "screen": screen_context,
                "action": action_desc.strip() if action_desc else "Unknown action",
                "outcome": str(outcome) if outcome else "Completed"
            }
            
            # Include reasoning if available (full text for complete context)
            if reasoning:
                entry["reasoning"] = str(reasoning)
            
            journal.append(entry)
            
            # Keep last 15 entries to limit context size
            if len(journal) > 15:
                journal = journal[-15:]
                 
            # Persist to database
            self.db_manager.update_exploration_journal(self.current_run_id, json.dumps(journal))
             
        except Exception as e:
            logger.warning(f"Failed to update journal: {e}")

    def _execute_actions(self, action_data: Dict[str, Any], screen_state: Any) -> Tuple[bool, List[bool], int, Optional[str], float]:
        actions_list = action_data.get("actions", [])
        if not actions_list:
            actions_list = [action_data]
            
        if screen_state.ocr_results:
            for act in actions_list:
                act["ocr_results"] = screen_state.ocr_results
                
        wait = float(self.config.get('WAIT_BETWEEN_BATCH_ACTIONS', 0.5))
        stop_on_err = bool(self.config.get('MULTI_ACTION_STOP_ON_ERROR', True))
        
        find_start = time.time()
        exec_count, success_list, batch_error = self.agent_assistant.action_executor.execute_action_batch(
            actions_list, wait_between_actions=wait, stop_on_error=stop_on_err
        )
        find_time = (time.time() - find_start) * 1000.0
        
        overall_success = all(success_list) if success_list else False
        
        if len(actions_list) > 1:
            self.runtime_stats.multi_action_batch_count += 1
            self.runtime_stats.total_batch_actions += len(actions_list)
            
        return overall_success, success_list, exec_count, batch_error, find_time

    def _record_step_results(self, from_screen_id, action_data, success, success_list, decision_time, find_time, error_msg, token_count, prompt):
        self.crawl_logger.log_step_to_db(
            self.current_run_id, self.step_count, from_screen_id, action_data, success_list,
            self.last_action_feedback, success, find_time, decision_time, token_count, prompt, error_msg
        )
        
        action_str = action_data.get('action_type', 'unknown')
        if 'actions' in action_data and action_data['actions']:
            action_str = f"batch({len(action_data['actions'])})"
            
        if success:
            self.last_action_feedback = f"Action '{action_str}' executed successfully"
            self.listener.on_status_change(f"Executed: {action_str}")
        else:
            self.last_action_feedback = f"Action '{action_str}' failed: {error_msg}"
            self.listener.on_status_change(f"Failed: {action_str}")
            self.runtime_stats.element_not_found_count += 1

    def _cleanup_resources(self):
        self._stop_traffic_capture()
        self._stop_video_recording()
        if self.db_manager:
            try:
                self.db_manager.close()
            except Exception as e:
                logger.error(f"Error closing DB: {e}")

    def _start_traffic_capture(self):
        if self.traffic_capture_manager:
            try:
                logger.info("Starting traffic capture")
                if hasattr(self.traffic_capture_manager, 'start_capture'):
                    self.traffic_capture_manager.start_capture()
                else:
                    asyncio.run(self.traffic_capture_manager.start_capture_async())
            except Exception as e:
                logger.error(f"Failed to start traffic capture: {e}")

    def _stop_traffic_capture(self):
        if self.traffic_capture_manager and self.traffic_capture_manager.is_capturing():
            try:
                logger.info("Stopping traffic capture")
                if hasattr(self.traffic_capture_manager, 'stop_capture_and_pull'):
                    pcap = self.traffic_capture_manager.stop_capture_and_pull(self.current_run_id)
                else:
                    pcap = asyncio.run(self.traffic_capture_manager.stop_capture_and_pull_async(self.current_run_id))
                if pcap:
                    logger.info(f"PCAP saved: {pcap}")
            except Exception as e:
                logger.error(f"Error stopping traffic capture: {e}")

    def _start_video_recording(self):
        if self.video_recording_manager:
            try:
                logger.info("Starting video recording")
                if hasattr(self.video_recording_manager, 'start_recording'):
                    self.video_recording_manager.start_recording()
                else:
                    asyncio.run(self.video_recording_manager.start_recording_async())
            except Exception as e:
                logger.error(f"Error starting video: {e}")

    def _stop_video_recording(self):
        if self.video_recording_manager and self.video_recording_manager.is_recording():
            try:
                logger.info("Stopping video recording")
                if hasattr(self.video_recording_manager, 'stop_recording_and_save'):
                    video = self.video_recording_manager.stop_recording_and_save()
                elif hasattr(self.video_recording_manager, 'stop_recording_and_pull'):
                    video = self.video_recording_manager.stop_recording_and_pull(self.current_run_id)
                else:
                    video = asyncio.run(self.video_recording_manager.stop_recording_and_pull_async(self.current_run_id))
                if video:
                    logger.info(f"Video saved: {video}")
            except Exception as e:
                logger.error(f"Error stopping video: {e}")

    def _update_run_status(self, status: str):
        if self.db_manager and self.current_run_id:
            try:
                end_time = None
                if status in [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.INTERRUPTED]:
                    end_time = datetime.now()
                
                self.db_manager.update_run_status(self.current_run_id, status, end_time)
                if self.current_run_id and status != RunStatus.RUNNING:
                    self.db_manager.save_run_stats(self.current_run_id, self.runtime_stats.to_dict())
            except Exception as e:
                logger.error(f"Error updating run status: {e}")


# ============================================================================
# Composition Root (Factory)
# ============================================================================

def run_crawler_loop(config: Optional[Config] = None):
    """
    Composition Root: Entry point that assembles dependencies and runs the crawler.
    This replaces the old 'monolithic' entry point with a factory pattern.
    """
    try:
        if config is None:
            config = Config()
            
        # 0. Setup Logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)],
            force=True
        )
        
        # 1. Create Event Listener (UI Output)
        listener = StdoutEventListener()
        listener.on_status_change("Initializing dependency graph...")

        # 2. Setup Flag Controller
        base_dir = config.BASE_DIR or '.'
        shutdown = getattr(config, 'SHUTDOWN_FLAG_PATH', None) or os.path.join(base_dir, DEFAULT_SHUTDOWN_FLAG)
        pause = getattr(config, 'PAUSE_FLAG_PATH', None) or os.path.join(base_dir, DEFAULT_PAUSE_FLAG)
        step_by_step = getattr(config, 'STEP_BY_STEP_FLAG_PATH', None) or os.path.join(base_dir, DEFAULT_STEP_BY_STEP_FLAG)
        continue_flag = getattr(config, 'CONTINUE_FLAG_PATH', None) or os.path.join(base_dir, DEFAULT_CONTINUE_FLAG)
        
        flag_controller = FlagController(shutdown, pause, step_by_step, continue_flag)

        # 3. Create Agent Assistant & Driver
        try:
            agent_assistant = AgentAssistant(config)
            if not agent_assistant._ensure_driver_connected():
                raise ConnectionError("Failed to connect driver (MCP server ok?)")
        except Exception as e:
            listener.on_error(f"Agent init failed: {e}")
            return

        # 4. Create Database & Screen Manager
        try:
            db_path = config.DB_NAME
            if '{' in db_path or 'unknown_device' in db_path:
                 # Resolve path logic here if needed, or assume Config handled it
                 # For now, simplistic validation
                 pass
                 
            db_manager = DatabaseManager(config)
            if not db_manager.connect():
                raise ConnectionError("Database connection failed")
                
            screen_state_manager = ScreenStateManager(db_manager, agent_assistant.tools.driver, config)
            
            # Setup Run ID
            app_pkg = config.get('APP_PACKAGE')
            app_act = config.get('APP_ACTIVITY')
            run_id = None
            if app_pkg and app_act:
                 run_id = db_manager.get_or_create_run_info(app_pkg, app_act)
                 if run_id:
                     db_manager.update_run_start_time(run_id)
                     screen_state_manager.initialize_for_run(run_id, app_pkg, app_act)
        except Exception as e:
            listener.on_error(f"Database init failed: {e}")
            return

        # 5. Optional Managers
        app_context = AppContextManager(agent_assistant.tools.driver, config)
        
        traffic = None
        if config.get('ENABLE_TRAFFIC_CAPTURE', False):
             traffic = TrafficCaptureManager(agent_assistant.tools.driver, config)
             
        video = None
        if config.get('ENABLE_VIDEO_RECORDING', False):
             video = VideoRecordingManager(agent_assistant.tools.driver, config)

        # 6. Assemble Crawler
        crawler = CrawlerLoop(
            config=config,
            listener=listener,
            flag_controller=flag_controller,
            agent_assistant=agent_assistant,
            db_manager=db_manager,
            screen_state_manager=screen_state_manager,
            app_context_manager=app_context,
            traffic_capture_manager=traffic,
            video_recording_manager=video,
            run_id=run_id
        )
        
        # 7. Run based on crawl mode
        crawl_mode = config.get('CRAWL_MODE', 'steps')
        max_steps = None
        max_duration_seconds = None
        
        if crawl_mode == 'time':
            max_duration_seconds = config.get('MAX_CRAWL_DURATION_SECONDS')
            if max_duration_seconds:
                max_duration_seconds = int(max_duration_seconds)
        else:
            max_steps = config.get('MAX_CRAWL_STEPS')
            if max_steps:
                max_steps = int(max_steps)
            
        with crawler:
            if crawler.initialize():
                crawler.run(max_steps=max_steps, max_duration_seconds=max_duration_seconds)
            
    except KeyboardInterrupt:
        print("Interrupted by user", file=sys.stderr)
    except Exception as e:
        print(f"FATAL ERROR in run_crawler_loop: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_crawler_loop()
