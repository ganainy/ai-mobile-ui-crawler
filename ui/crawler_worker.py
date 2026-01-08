#!/usr/bin/env python3
"""
Crawler Worker Module
=====================

QThread-based worker that runs the crawler loop in-process for easier debugging.
Replaces QProcess-based subprocess execution.

This allows:
- Setting breakpoints in crawler_loop.py, agent_assistant.py, etc.
- Single-process debugging
- Direct signal-based UI updates (no stdout JSON parsing)
"""

import logging
import os
import sys
import threading
from typing import Any, Dict, Optional

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class SignalEventListener:
    """
    Event listener that bridges CrawlerEventListener protocol to Qt signals.
    
    This adapter receives events from CrawlerLoop and emits them as Qt signals
    on the parent CrawlerWorker, enabling thread-safe UI updates.
    """
    
    def __init__(self, worker: 'CrawlerWorker'):
        self.worker = worker
    
    def on_step_start(self, step: int) -> None:
        """Called when a new step starts."""
        self.worker.step_started.emit(step)
    
    def on_screenshot_captured(self, path: str, blocked: bool = False) -> None:
        """Called when a screenshot is captured and saved."""
        self.worker.screenshot_captured.emit(path or "", blocked)
    
    def on_status_change(self, message: str) -> None:
        """Called when status message should be displayed."""
        self.worker.status_changed.emit(message)
    
    def on_error(self, message: str) -> None:
        """Called when a critical error occurs."""
        self.worker.error_occurred.emit(message)
    
    def on_action(self, action_desc: str) -> None:
        """Called when an action is executed."""
        self.worker.action_executed.emit(action_desc)


class CrawlerWorker(QThread):
    """
    Worker thread that runs the crawler loop in-process.
    
    This replaces the QProcess-based subprocess execution with an in-process
    QThread, enabling:
    - Direct debugging with breakpoints
    - Signal-based UI communication
    - Shared memory access
    
    Signals:
        step_started: Emitted when a new step begins (step number)
        screenshot_captured: Emitted when screenshot is saved (path, blocked)
        status_changed: Emitted for status updates (message)
        error_occurred: Emitted on errors (error message)
        action_executed: Emitted when AI executes an action (description)
        finished_with_status: Emitted when crawler finishes (status string)
        log_message: Emitted for log messages (message)
    """
    
    # Qt Signals for thread-safe UI communication
    step_started = Signal(int)
    screenshot_captured = Signal(str, bool)  # path, blocked
    status_changed = Signal(str)
    error_occurred = Signal(str)
    action_executed = Signal(str)
    finished_with_status = Signal(str)
    log_message = Signal(str)
    
    def __init__(self, config, parent=None):
        """
        Initialize the crawler worker.
        
        Args:
            config: Application configuration object
            parent: Parent QObject (optional)
        """
        super().__init__(parent)
        self.config = config
        self._stop_requested = threading.Event()
        self._crawler_loop = None
        
        # Optional feature flags
        self.enable_traffic_capture = False
        self.enable_mobsf_analysis = False
        self.enable_video_recording = False
        self.enable_ai_run_report = False
    
    def request_stop(self) -> None:
        """Request the crawler to stop gracefully."""
        logger.info("Stop requested for crawler worker")
        self._stop_requested.set()
        
        # Also create the shutdown flag file for the flag controller
        if hasattr(self, '_flag_controller') and self._flag_controller:
            try:
                self._flag_controller.create_shutdown_flag()
            except Exception as e:
                logger.warning(f"Could not create shutdown flag: {e}")
    
    def is_stop_requested(self) -> bool:
        """Check if stop has been requested."""
        return self._stop_requested.is_set()
    
    def run(self) -> None:
        """
        Main thread execution - runs the crawler loop.
        
        This method is called when QThread.start() is invoked.
        """
        try:
            self._run_crawler()
        except Exception as e:
            logger.error(f"Fatal error in crawler worker: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
            self.finished_with_status.emit("FAILED")
    
    def _run_crawler(self) -> None:
        """Internal method that sets up and runs the crawler loop."""
        # Import here to avoid circular imports and ensure fresh imports
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
            from infrastructure.database import DatabaseManager
            from domain.screen_state_manager import ScreenStateManager
            from core.crawler_loop import CrawlerLoop, RunStatus
        except ImportError as e:
            self.error_occurred.emit(f"Import error: {e}")
            self.finished_with_status.emit("FAILED")
            return
        
        # Setup logging to capture and emit log messages
        self._setup_logging()
        
        self.status_changed.emit("Initializing crawler components...")
        
        try:
            # 1. Create Event Listener (UI Output via signals)
            listener = SignalEventListener(self)
            
            # 2. Setup Flag Controller
            base_dir = self.config.BASE_DIR or '.'
            shutdown = getattr(self.config, 'SHUTDOWN_FLAG_PATH', None) or os.path.join(base_dir, DEFAULT_SHUTDOWN_FLAG)
            pause = getattr(self.config, 'PAUSE_FLAG_PATH', None) or os.path.join(base_dir, DEFAULT_PAUSE_FLAG)
            step_by_step = getattr(self.config, 'STEP_BY_STEP_FLAG_PATH', None) or os.path.join(base_dir, DEFAULT_STEP_BY_STEP_FLAG)
            continue_flag = getattr(self.config, 'CONTINUE_FLAG_PATH', None) or os.path.join(base_dir, DEFAULT_CONTINUE_FLAG)
            
            self._flag_controller = FlagController(shutdown, pause, step_by_step, continue_flag)
            
            # 3. Create Agent Assistant & Driver
            self.status_changed.emit("Creating AI agent...")
            try:
                agent_assistant = AgentAssistant(self.config)
                if not agent_assistant._ensure_driver_connected():
                    raise ConnectionError("Failed to connect driver (MCP server ok?)")
            except Exception as e:
                self.error_occurred.emit(f"Agent init failed: {e}")
                self.finished_with_status.emit("FAILED")
                return
            
            # 4. Create Database & Screen Manager
            self.status_changed.emit("Initializing database...")
            try:
                db_manager = DatabaseManager(self.config)
                if not db_manager.connect():
                    raise ConnectionError("Database connection failed")
                
                screen_state_manager = ScreenStateManager(
                    db_manager, 
                    agent_assistant.tools.driver, 
                    self.config
                )
                
                # Setup Run ID
                app_pkg = self.config.get('APP_PACKAGE')
                app_act = self.config.get('APP_ACTIVITY')
                run_id = None
                if app_pkg and app_act:
                    run_id = db_manager.get_or_create_run_info(app_pkg, app_act)
                    if run_id:
                        db_manager.update_run_start_time(run_id)
                        screen_state_manager.initialize_for_run(run_id, app_pkg, app_act)
            except Exception as e:
                self.error_occurred.emit(f"Database init failed: {e}")
                self.finished_with_status.emit("FAILED")
                return
            
            # 5. Optional Managers
            app_context = AppContextManager(agent_assistant.tools.driver, self.config)
            
            traffic = None
            if self.enable_traffic_capture:
                traffic = TrafficCaptureManager(agent_assistant.tools.driver, self.config)
            
            video = None
            if self.enable_video_recording:
                video = VideoRecordingManager(agent_assistant.tools.driver, self.config)
            
            # 6. Assemble Crawler
            self.status_changed.emit("Starting crawler loop...")
            crawler = CrawlerLoop(
                config=self.config,
                listener=listener,
                flag_controller=self._flag_controller,
                agent_assistant=agent_assistant,
                db_manager=db_manager,
                screen_state_manager=screen_state_manager,
                app_context_manager=app_context,
                traffic_capture_manager=traffic,
                video_recording_manager=video,
                run_id=run_id
            )
            
            self._crawler_loop = crawler
            
            # 7. Run based on crawl mode
            crawl_mode = self.config.get('CRAWL_MODE', 'steps')
            max_steps = None
            max_duration_seconds = None
            
            if crawl_mode == 'time':
                max_duration_seconds = self.config.get('MAX_CRAWL_DURATION_SECONDS')
                if max_duration_seconds:
                    max_duration_seconds = int(max_duration_seconds)
            else:
                max_steps = self.config.get('MAX_CRAWL_STEPS')
                if max_steps:
                    max_steps = int(max_steps)
            
            with crawler:
                if crawler.initialize():
                    crawler.run(max_steps=max_steps, max_duration_seconds=max_duration_seconds)
            
            # Determine final status
            final_status = "COMPLETED"
            if self._stop_requested.is_set():
                final_status = "INTERRUPTED"
            elif crawler.state.name == "ERROR":
                final_status = "FAILED"
            
            self.finished_with_status.emit(final_status)
            
        except KeyboardInterrupt:
            logger.info("Crawler interrupted by keyboard")
            self.finished_with_status.emit("INTERRUPTED")
        except Exception as e:
            logger.error(f"Fatal error in crawler: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
            self.finished_with_status.emit("FAILED")
    
    def _setup_logging(self) -> None:
        """Setup logging to capture messages and emit via signal."""
        # Create a handler that emits log messages as signals
        class SignalHandler(logging.Handler):
            def __init__(self, worker):
                super().__init__()
                self.worker = worker
            
            def emit(self, record):
                try:
                    msg = self.format(record)
                    self.worker.log_message.emit(msg)
                except Exception:
                    pass
        
        # Add handler to root logger
        handler = SignalHandler(self)
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        handler.setLevel(logging.INFO)
        
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
