#!/usr/bin/env python3
# ui/crawler_manager.py - Crawler process management for the UI controller

import logging
import os
import sys
import json
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QRunnable, QThread, QThreadPool, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication, QCheckBox

# Import shared orchestrator components
from core import get_process_backend, get_validation_service
from core.adapters import create_process_backend
from core.controller import CrawlerOrchestrator
from core.health_check import ValidationService
from cli.constants import keys as KEYS
from ui.crawler_worker import CrawlerWorker


class ValidationWorker(QRunnable):
    """Worker class to run validation checks asynchronously."""
    
    def __init__(self, crawler_manager):
        super().__init__()
        self.crawler_manager = crawler_manager
        self.signals = ValidationSignals()
    
    def run(self):
        """Run the validation checks in a background thread."""
        try:
            # Perform validation
            is_valid, messages = self.crawler_manager.validate_pre_crawl_requirements()
            
            # Get detailed status
            status_details = self.crawler_manager.get_service_status_details()
            
            # Emit results
            self.signals.validation_completed.emit(is_valid, messages, status_details)
            
        except Exception as e:
            logging.error(f"Error in validation worker: {e}")
            self.signals.validation_error.emit(str(e))


class ValidationSignals(QObject):
    """Signals for validation worker communication."""
    validation_completed = Signal(bool, list, dict)  # is_valid, messages, status_details
    validation_error = Signal(str)  # error_message


class CrawlerManager(QObject):
    """Manages the crawler process for the Appium Crawler Controller."""
    
    # Signals
    step_updated = Signal(int)
    action_updated = Signal(str)
    screenshot_updated = Signal(str)
    
    def __init__(self, main_controller):
        """
        Initialize the crawler manager.
        
        Args:
            main_controller: The main UI controller
        """
        super().__init__()
        self.main_controller = main_controller
        self.config = main_controller.config
        self.step_count = 0
        self.last_action = "None"
        self.current_screenshot = None
        
        # CrawlerWorker - in-process QThread for easier debugging
        self.crawler_worker: Optional[CrawlerWorker] = None
        
        self._shutdown_flag_file_path = self.config.SHUTDOWN_FLAG_PATH
        self.shutdown_timer = QTimer(self)
        self.shutdown_timer.setSingleShot(True)
        self.shutdown_timer.timeout.connect(self.force_stop_crawler_on_timeout)
        
        # Initialize shared orchestrator
        backend = create_process_backend(use_qt=True)  # UI uses Qt backend
        self.orchestrator = CrawlerOrchestrator(self.config, backend)
        
        # Initialize thread pool for async validation
        self.thread_pool = QThreadPool()
        self.validation_worker = None
        
        # Connect orchestrator signals to UI
        self._connect_orchestrator_signals()
    
    def is_crawler_running(self) -> bool:
        """Check if the crawler worker is currently running."""
        return self.crawler_worker is not None and self.crawler_worker.isRunning()

    def _connect_orchestrator_signals(self):
        """Connect orchestrator output callbacks to UI signals."""
        # Register callbacks with the orchestrator
        self.orchestrator.register_callback('step', self._on_step_callback)
        self.orchestrator.register_callback('action', self._on_action_callback)
        self.orchestrator.register_callback('screenshot', self._on_screenshot_callback)
        self.orchestrator.register_callback('status', self._on_status_callback)

        self.orchestrator.register_callback('end', self._on_end_callback)
        self.orchestrator.register_callback('log', self._on_log_callback)
    
    def _on_step_callback(self, step_num: int):
        """Handle step callback from orchestrator."""
        self.step_count = step_num
        self.step_updated.emit(step_num)
        self.main_controller.step_label.setText(f"Step: {step_num}")
        self.update_progress()
    
    def _on_action_callback(self, action: str):
        """Handle action callback from orchestrator."""
        self.last_action = action
        self.action_updated.emit(action)
        # Action history UI update removed as requested
    
    def _on_screenshot_callback(self, screenshot_path: str):
        """Handle screenshot callback from orchestrator."""
        if os.path.exists(screenshot_path):
            self.current_screenshot = screenshot_path
            self.screenshot_updated.emit(screenshot_path)
            self.main_controller.update_screenshot(screenshot_path)
    
    def _on_status_callback(self, status: str):
        """Handle status callback from orchestrator."""
        self.main_controller.status_label.setText(f"Status: {status}")
    
    
    def _on_end_callback(self, end_status: str):
        """Handle end callback from orchestrator."""
        # This callback is just for logging purposes, not for determining completion
        self.main_controller.log_message(f"Final status: {end_status}", "blue")
    
    def _on_log_callback(self, message: str):
        """Handle log callback from orchestrator."""
        # Parse log level and color
        color = 'white'
        log_message = message
        
        prefixes = {
            '[INFO]': 'blue',
            'INFO:': 'blue',
            '[WARNING]': 'orange',
            'WARNING:': 'orange',
            '[ERROR]': 'red',
            'ERROR:': 'red',
            '[CRITICAL]': 'red',
            'CRITICAL:': 'red',
            '[DEBUG]': 'gray',
            'DEBUG:': 'gray',
        }
        
        for prefix, p_color in prefixes.items():
            if message.startswith(prefix):
                log_message = message[len(prefix):].lstrip()
                color = p_color
                break
        
        if log_message == "None":
            return

        self.main_controller.log_message(log_message, color)
    
    def validate_pre_crawl_requirements(self) -> Tuple[bool, List[str]]:
        """
        Validate all pre-crawl requirements before starting the crawler.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        # Use ValidationService for validation
        health_service = ValidationService(self.config)
        services_status = health_service.check_all_services()
        
        issues = []
        warnings = []
        
        # Extract issues and warnings from service status
        for service_name, status in services_status.items():
            status_type = status.get(KEYS.STATUS_KEY_STATUS, '')
            message = status.get(KEYS.STATUS_KEY_MESSAGE, '')
            
            if status_type == KEYS.STATUS_ERROR:
                issues.append(f"❌ {service_name}: {message}")
            elif status_type == KEYS.STATUS_WARNING:
                warnings.append(f"⚠️ {service_name}: {message}")
        
        # Combine issues and warnings for display
        all_messages = issues + warnings
        
        return len(issues) == 0, all_messages
    
    # Removed duplicate health check methods - now using ValidationService
    # These methods were replaced by ValidationService to eliminate code duplication
    
    def get_service_status_details(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed status information about all services.
        
        Returns:
            Dictionary with service status details
        """
        # Use the shared validation service
        validation_service = get_validation_service(self.config)
        return validation_service.get_service_status_details()
    
    def update_progress(self):
        """Update the progress bar based on the current step count."""
        if self.main_controller.config_widgets['CRAWL_MODE'].currentText() == 'steps':
            max_steps = self.main_controller.config_widgets['MAX_CRAWL_STEPS'].value()
            self.main_controller.progress_bar.setRange(0, max_steps if max_steps > 0 else 0)
            if max_steps > 0:
                self.main_controller.progress_bar.setValue(min(self.step_count, max_steps))
        else:
            # For time-based crawl, use indeterminate progress bar
            self.main_controller.progress_bar.setRange(0, 0)
    
    @Slot()
    def start_crawler(self):
        """Start the crawler process without validation checks."""
        # Check if app package is selected
        app_package = self.config.get('APP_PACKAGE', None)
        if not app_package:
            self.main_controller.log_message(
                "ERROR: No target app selected. Please scan for and select a health app before starting the crawler.",
                'red'
            )
            return

        self._start_crawler_process()

    @Slot()
    def perform_pre_crawl_validation(self):
        """Perform pre-crawl validation checks asynchronously."""
        self.main_controller.log_message("Validating services and requirements...", 'blue')
        
        # Show loading overlay
        self.main_controller.show_busy("Validating services and requirements...")
        
        # Create and start validation worker
        self.validation_worker = ValidationWorker(self)
        self.validation_worker.signals.validation_completed.connect(self._on_validation_completed)
        self.validation_worker.signals.validation_error.connect(self._on_validation_error)
        
        # Start the worker in the thread pool
        self.thread_pool.start(self.validation_worker)
    
    @Slot(bool, list, dict)
    def _on_validation_completed(self, is_valid: bool, messages: List[str], status_details: Dict[str, Any]):
        """Handle validation completion."""
        # Hide loading overlay
        self.main_controller.hide_busy()
        
        # Separate blocking issues from warnings
        blocking_issues = [msg for msg in messages if msg.startswith("❌")]
        warnings = [msg for msg in messages if msg.startswith("⚠️")]

        # Show warnings if any
        if warnings:
            for warning in warnings:
                self.main_controller.log_message(f"   {warning}", 'orange')

        if blocking_issues:
            self.main_controller.log_message("", 'white')  # Empty line
            self.main_controller.log_message("⚠️ Some requirements are not met.", 'orange')
            self.main_controller.log_message("💡 You can still start the crawler, but it may fail if services are not available.", 'blue')
        elif warnings:
            self.main_controller.log_message("", 'white')  # Empty line
            self.main_controller.log_message("✅ Core requirements met. Warnings shown above.", 'green')
        else:
            # No issues at all
            pass

        # Show detailed status
        self._display_validation_details(status_details)
    
    @Slot(str)
    def _on_validation_error(self, error_message: str):
        """Handle validation error."""
        # Hide loading overlay
        self.main_controller.hide_busy()
        
        self.main_controller.log_message(f"❌ Validation error: {error_message}", 'red')
        logging.error(f"Validation error: {error_message}")
    
    def _display_validation_details(self, status_details: Dict[str, Any]):
        """Display detailed validation status."""
        try:
            self.main_controller.log_message("🔍 Validation Results:", 'blue')
            
            for service_name, details in status_details.items():
                if service_name in ['mobsf', 'mcp']:
                    # Special handling for optional services - use warning icon when not running
                    if details.get('running', False):
                        status_icon = "✅"
                        color = 'green'
                    else:
                        status_icon = "⚠️"
                        color = 'orange'
                    self.main_controller.log_message(f"{status_icon} {details['message']}", color)
                else:
                    # Standard handling for other services
                    status_icon = "✅" if details.get('running', details.get('valid', details.get('selected', False))) else "❌"
                    color = 'green' if details.get('running', details.get('valid', details.get('selected', False))) else 'red'
                    self.main_controller.log_message(f"{status_icon} {details['message']}", color)
                
                # Show additional details for API keys
                if service_name == 'api_keys' and details.get('issues'):
                    for issue in details['issues']:
                        self.main_controller.log_message(f"   {issue}", 'orange')
            
            # Count blocking issues (required services that are not running)
            blocking_issues = sum(1 for details in status_details.values() 
                                if details.get('required', True) and 
                                not details.get('running', details.get('valid', details.get('selected', False))))
            
            # Count warnings (non-required services that are not running)
            warnings = sum(1 for details in status_details.values() 
                          if not details.get('required', True) and 
                          not details.get('running', details.get('valid', details.get('selected', False))))
            
            if blocking_issues == 0 and warnings == 0:
                self.main_controller.log_message("🎉 All systems are ready for crawling!", 'green')
            elif blocking_issues == 0:
                self.main_controller.log_message(f"✅ Core requirements met. {warnings} warning(s) shown above.", 'green')
            else:
                self.main_controller.log_message(f"⚠️ {blocking_issues} blocking issue(s), {warnings} warning(s). You can still start the crawler.", 'orange')
                
        except Exception as e:
            self.main_controller.log_message(f"Error displaying validation details: {e}", 'red')
    
    def force_start_crawler(self):
        """Force start the crawler process without validation checks."""
        self.main_controller.log_message("Force starting crawler without validation checks...", 'orange')
        self._start_crawler_process()
    
    def _start_crawler_process(self):
        """Internal method to start the actual crawler process."""
        # Check if AI model is selected
        model_type = self.config.get('DEFAULT_MODEL_TYPE', None)
        if not model_type or (isinstance(model_type, str) and model_type.strip() == ''):
            self.main_controller.log_message(
                "ERROR: No AI model selected. Please select an AI model before starting a crawl.",
                'red'
            )
            self.main_controller.log_message(
                "Use the model dropdown in the configuration panel or run: python run_cli.py <provider> select-model <model>",
                'red'
            )
            return
        
        # Check if the required dependencies are installed for the selected AI provider
        try:
            from domain.model_adapters import check_dependencies
        except ImportError:
            self.main_controller.log_message(
                "ERROR: Could not import model_adapters module. Please check your installation.",
                'red'
            )
            return
                
        ai_provider = self.config.get('AI_PROVIDER', 'gemini').lower()
        deps_installed, error_msg = check_dependencies(ai_provider)
        
        if not deps_installed:
            self.main_controller.log_message(
                f"ERROR: Missing dependencies for {ai_provider} provider. {error_msg}",
                'red'
            )
            return
            
        # Continue with the rest of the start_crawler logic
        # Ensure output session directories are created just-in-time for this run
        try:
            output_dir = self.config.get('OUTPUT_DATA_DIR', 'output_data')
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            self.main_controller.log_message(f"ERROR: Failed to prepare output directories: {e}", 'red')
            return

        # Clean up stale flags
        try:
            # Shutdown flag
            if self._shutdown_flag_file_path and os.path.exists(self._shutdown_flag_file_path):
                os.remove(self._shutdown_flag_file_path)
            
            # Pause flag
            if self.orchestrator.flag_controller.is_pause_flag_present():
                self.orchestrator.flag_controller.remove_pause_flag()
                
            # Continue flag
            if self.orchestrator.flag_controller.is_continue_flag_present():
                self.orchestrator.flag_controller.remove_continue_flag()
                
            # Sync Step-by-step flag with checkbox
            if hasattr(self.main_controller, 'step_by_step_chk') and self.main_controller.step_by_step_chk.isChecked():
                self.orchestrator.flag_controller.create_step_by_step_flag()
            else:
                 # Checkbox not checked, ensure flag is removed
                if self.orchestrator.flag_controller.is_step_by_step_flag_present():
                    self.orchestrator.flag_controller.remove_step_by_step_flag()

        except Exception as e:
            self.main_controller.log_message(
                f"Warning: Could not clean up crawler flags: {e}", 'orange'
            )


        if hasattr(self.main_controller, 'log_output'):
            self.main_controller.log_message("Starting crawler...", 'blue')
        else:
            pass

        if not self.crawler_worker or not self.crawler_worker.isRunning():
            # Reset tracking variables
            self.step_count = 0
            self.last_action = "None"
            self.current_screenshot = None
            
            # Update UI
            self.main_controller.step_label.setText("Step: 0")
            self.main_controller.status_label.setText("Status: Starting...")
            self.main_controller.progress_bar.setValue(0)
            
            # Start the session timer
            if hasattr(self.main_controller, '_start_session_timer'):
                self.main_controller._start_session_timer()
            
            if hasattr(self.main_controller, 'start_stop_btn'):
                self.main_controller.start_stop_btn.setText("Stop Crawler")
                self.main_controller.start_stop_btn.setStyleSheet("background-color: #ffcccc; color: #cc0000;")
                self.main_controller.start_stop_btn.setEnabled(True)

            try:
                if hasattr(self.main_controller, 'generate_report_btn') and self.main_controller.generate_report_btn:
                    self.main_controller.generate_report_btn.setEnabled(False)
            except Exception:
                pass
            
            # Auto-hide settings panel on start
            if hasattr(self.main_controller, 'left_panel') and hasattr(self.main_controller, 'toggle_settings_btn'):
                self.main_controller.left_panel.setVisible(False)
                self.main_controller.toggle_settings_btn.setText("Show Settings")
            
            # Create the CrawlerWorker with the config
            self.crawler_worker = CrawlerWorker(self.config, parent=self)
            
            # Check feature flags from UI checkboxes
            if "ENABLE_TRAFFIC_CAPTURE" in self.main_controller.config_widgets:
                checkbox = self.main_controller.config_widgets["ENABLE_TRAFFIC_CAPTURE"]
                if isinstance(checkbox, QCheckBox):
                    self.crawler_worker.enable_traffic_capture = checkbox.isChecked()
            
            if "ENABLE_MOBSF_ANALYSIS" in self.main_controller.config_widgets:
                checkbox = self.main_controller.config_widgets["ENABLE_MOBSF_ANALYSIS"]
                if isinstance(checkbox, QCheckBox):
                    self.crawler_worker.enable_mobsf_analysis = checkbox.isChecked()
            
            if "ENABLE_VIDEO_RECORDING" in self.main_controller.config_widgets:
                checkbox = self.main_controller.config_widgets["ENABLE_VIDEO_RECORDING"]
                if isinstance(checkbox, QCheckBox):
                    self.crawler_worker.enable_video_recording = checkbox.isChecked()
            
            if "ENABLE_AI_RUN_REPORT" in self.main_controller.config_widgets:
                checkbox = self.main_controller.config_widgets["ENABLE_AI_RUN_REPORT"]
                if isinstance(checkbox, QCheckBox):
                    self.crawler_worker.enable_ai_run_report = checkbox.isChecked()
            
            # Connect worker signals to UI handlers
            self.crawler_worker.step_started.connect(self._on_worker_step_started)
            self.crawler_worker.screenshot_captured.connect(self._on_worker_screenshot_captured)
            self.crawler_worker.status_changed.connect(self._on_worker_status_changed)
            self.crawler_worker.error_occurred.connect(self._on_worker_error)
            self.crawler_worker.action_executed.connect(self._on_worker_action_executed)
            self.crawler_worker.finished_with_status.connect(self._on_worker_finished)
            self.crawler_worker.log_message.connect(self._on_worker_log_message)
            self.crawler_worker.finished.connect(self._on_thread_finished)
            
            # Start the worker thread
            self.crawler_worker.start()
            
            # --- Update Control Buttons State ---
            if hasattr(self.main_controller, 'pause_resume_btn'):
                self.main_controller.pause_resume_btn.setEnabled(True)
                self.main_controller.pause_resume_btn.setText("⏸️ Pause")
            
            if hasattr(self.main_controller, 'step_by_step_chk') and hasattr(self.main_controller, 'next_step_btn'):
                is_step_mode = self.main_controller.step_by_step_chk.isChecked()
                self.main_controller.next_step_btn.setEnabled(is_step_mode)

            self.update_progress()
        else:
            self.main_controller.log_message("Crawler is already running.", 'orange')
    
    @Slot()
    def stop_crawler(self) -> None:
        """Stop the crawler worker, trying graceful shutdown first."""
        if self.crawler_worker and self.crawler_worker.isRunning():
            self.main_controller.log_message("Stopping crawler... (waiting for current step to finish)", 'blue')
            self.main_controller.status_label.setText("Status: Stopping...")
            
            # Disable button to prevent double clicks
            if hasattr(self.main_controller, 'start_stop_btn'):
                self.main_controller.start_stop_btn.setEnabled(False)
                self.main_controller.start_stop_btn.setText("Stopping...")
            
            # Disable control buttons during shutdown
            if hasattr(self.main_controller, 'pause_resume_btn'):
                self.main_controller.pause_resume_btn.setEnabled(False)
            if hasattr(self.main_controller, 'next_step_btn'):
                self.main_controller.next_step_btn.setEnabled(False)

            # Request graceful stop via worker
            self.crawler_worker.request_stop()
            
            # Start a timer to force termination if graceful shutdown takes too long
            self.shutdown_timer.start(30000)  # 30 seconds timeout
        else:
            self.main_controller.log_message("No crawler running.", 'orange')
    
    @Slot()
    def force_stop_crawler_on_timeout(self) -> None:
        """Force stop the crawler worker if it doesn't respond to graceful shutdown."""
        if self.crawler_worker and self.crawler_worker.isRunning():
            self.main_controller.log_message("Crawler did not exit gracefully. Forcing termination...", 'red')
            self.crawler_worker.terminate()
            self.crawler_worker.wait(5000)  # Wait up to 5 seconds for thread to finish
        else:
            self.main_controller.log_message("Crawler already stopped.", 'green')
    
    # =========================================================================
    # Worker Signal Handlers (for CrawlerWorker QThread)
    # =========================================================================
    
    @Slot(int)
    def _on_worker_step_started(self, step: int) -> None:
        """Handle step started signal from worker."""
        self.step_count = step
        self.step_updated.emit(step)
        self.main_controller.step_label.setText(f"Step: {step}")
        self.update_progress()
    
    @Slot(str, bool)
    def _on_worker_screenshot_captured(self, path: str, blocked: bool) -> None:
        """Handle screenshot captured signal from worker."""
        if path and os.path.exists(path):
            self.current_screenshot = path
            self.screenshot_updated.emit(path)
            self.main_controller.update_screenshot(path)
        elif blocked:
            # Screenshot blocked by FLAG_SECURE
            self.main_controller.log_message("Screenshot blocked (FLAG_SECURE)", 'orange')
    
    @Slot(str)
    def _on_worker_status_changed(self, message: str) -> None:
        """Handle status change signal from worker."""
        self.main_controller.status_label.setText(f"Status: {message}")
    
    @Slot(str)
    def _on_worker_error(self, message: str) -> None:
        """Handle error signal from worker."""
        self.main_controller.log_message(f"Error: {message}", 'red')
        logging.error(f"Crawler error: {message}")
    
    @Slot(str)
    def _on_worker_action_executed(self, action_desc: str) -> None:
        """Handle action executed signal from worker."""
        self.last_action = action_desc
        self.action_updated.emit(action_desc)
    
    @Slot(str)
    def _on_worker_finished(self, status: str) -> None:
        """Handle finished signal from worker with status."""
        self.shutdown_timer.stop()
        
        # Clean up shutdown flag if present
        if self._shutdown_flag_file_path and os.path.exists(self._shutdown_flag_file_path):
            try:
                os.remove(self._shutdown_flag_file_path)
            except Exception:
                pass
        
        status_text = f"Finished: {status}"
        self.main_controller.log_message(f"Crawler {status_text}", 'blue')
        self.main_controller.status_label.setText(f"Status: {status_text}")
        
        # Play audio alert
        try:
            if hasattr(self.main_controller, '_audio_alert'):
                if status == "COMPLETED":
                    self.main_controller._audio_alert('finish')
                else:
                    self.main_controller._audio_alert('error')
        except Exception:
            pass
    
    @Slot()
    def _on_thread_finished(self) -> None:
        """Handle QThread finished signal - reset UI state."""
        self.shutdown_timer.stop()
        
        if hasattr(self.main_controller, 'start_stop_btn'):
            self.main_controller.start_stop_btn.setEnabled(True)
            self.main_controller.start_stop_btn.setText("Start Crawler")
            self.main_controller.start_stop_btn.setStyleSheet("")
        
        # Disable control buttons
        if hasattr(self.main_controller, 'pause_resume_btn'):
            self.main_controller.pause_resume_btn.setEnabled(False)
        if hasattr(self.main_controller, 'next_step_btn'):
            self.main_controller.next_step_btn.setEnabled(False)
        
        # Stop the session timer
        if hasattr(self.main_controller, '_stop_session_timer'):
            self.main_controller._stop_session_timer()
        
        # Auto-show settings panel
        if hasattr(self.main_controller, 'left_panel') and hasattr(self.main_controller, 'toggle_settings_btn'):
            self.main_controller.left_panel.setVisible(True)
            self.main_controller.toggle_settings_btn.setText("Hide Settings")
        
        # Enable report generation
        try:
            if hasattr(self.main_controller, 'generate_report_btn') and self.main_controller.generate_report_btn:
                self.main_controller.generate_report_btn.setEnabled(True)
        except Exception:
            pass
        
        self.crawler_worker = None
    
    @Slot(str)
    def _on_worker_log_message(self, message: str) -> None:
        """Handle log message signal from worker."""
        # Parse log level and color
        color = 'white'
        log_message = message
        
        prefixes = {
            'INFO:': 'blue',
            'WARNING:': 'orange',
            'ERROR:': 'red',
            'CRITICAL:': 'red',
            'DEBUG:': 'gray',
        }
        
        for prefix, p_color in prefixes.items():
            if message.startswith(prefix):
                log_message = message[len(prefix):].lstrip()
                color = p_color
                break
        
        if log_message and log_message != "None":
            self.main_controller.log_message(log_message, color)
    
    # NOTE: Legacy QProcess stdout parsing methods (read_stdout, _process_log_line, 
    # _handle_json_event) have been removed - now using QThread signals directly.

    @Slot()
    def open_session_folder(self) -> None:
        """Open the current session's output folder in the system file explorer."""
        from pathlib import Path
        import subprocess
        import platform
        
        try:
            # Try to get session directory from config
            session_dir = None
            
            # Method 1: Try the SESSION_DIR property (if device info is set)
            try:
                session_dir_str = self.config.SESSION_DIR
                if session_dir_str and '{' not in session_dir_str:  # Ensure not a template
                    session_dir = Path(session_dir_str)
                    if session_dir.exists():
                        self._open_folder_in_explorer(session_dir)
                        return
            except (RuntimeError, AttributeError):
                # SESSION_DIR property may raise RuntimeError if device info not available
                pass
            
            # Method 2: Fallback - find latest session for current app package
            app_package = self.config.get('APP_PACKAGE', None)
            output_data_dir = self.config.get('OUTPUT_DATA_DIR', None)
            
            if not app_package:
                self.main_controller.log_message(
                    "⚠️ No target app selected. Please select an app first.", 'orange'
                )
                return
            
            if not output_data_dir:
                self.main_controller.log_message(
                    "⚠️ Output directory not configured.", 'orange'
                )
                return
            
            # Look for session directories matching the app package
            output_dir = Path(output_data_dir)
            sessions_dir = output_dir / "sessions"
            
            if not sessions_dir.exists():
                self.main_controller.log_message(
                    f"⚠️ Sessions directory not found: {sessions_dir}", 'orange'
                )
                return
            
            # Find all session directories for this app package
            candidates = []
            for sd in sessions_dir.iterdir():
                if sd.is_dir() and app_package in sd.name:
                    candidates.append(sd)
            
            if not candidates:
                self.main_controller.log_message(
                    f"⚠️ No session directories found for '{app_package}'", 'orange'
                )
                return
            
            # Sort by name (descending) to get the latest session
            candidates.sort(key=lambda p: p.name, reverse=True)
            session_dir = candidates[0]
            
            self._open_folder_in_explorer(session_dir)
            
        except Exception as e:
            self.main_controller.log_message(f"Error opening session folder: {e}", 'red')
            logging.error(f"Error opening session folder: {e}")
    
    def _open_folder_in_explorer(self, folder_path: 'Path') -> None:
        """Open a folder in the system's file explorer (cross-platform)."""
        import subprocess
        import platform
        
        folder_str = str(folder_path.resolve())
        
        try:
            system = platform.system()
            
            if system == 'Windows':
                # Use os.startfile for Windows
                os.startfile(folder_str)
            elif system == 'Darwin':
                # macOS
                subprocess.run(['open', folder_str], check=True)
            else:
                # Linux and other Unix-like systems
                subprocess.run(['xdg-open', folder_str], check=True)
            
            self.main_controller.log_message(f"📂 Opened folder: {folder_str}", 'green')
            
        except Exception as e:
            self.main_controller.log_message(f"Error opening folder: {e}", 'red')
            logging.error(f"Error opening folder {folder_str}: {e}")

    # ========================================================================
    # Pause / Step Control Methods (Delegated to Orchestrator)
    # ========================================================================

    def enable_step_by_step(self) -> bool:
        """Enable step-by-step mode."""
        return self.orchestrator.flag_controller.create_step_by_step_flag()

    def disable_step_by_step(self) -> bool:
        """Disable step-by-step mode."""
        return self.orchestrator.flag_controller.remove_step_by_step_flag()

    def next_step(self) -> bool:
        """Advance one step when paused."""
        return self.orchestrator.flag_controller.create_continue_flag()

    def pause_crawler(self) -> bool:
        """Manually pause the crawler."""
        return self.orchestrator.flag_controller.create_pause_flag()

    def resume_crawler(self) -> bool:
        """Resume manual pause."""
        return self.orchestrator.flag_controller.remove_pause_flag()
