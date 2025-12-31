"""
Telemetry service for CLI operations.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from cli.constants import keys as KEYS
from cli.constants import messages as MSG


class TelemetryService:
    """Service for managing telemetry and status reporting."""
    
    def __init__(self):
        """Initialize telemetry service."""
        self.start_time = datetime.now()
        self.events: List[Dict[str, Any]] = []
    
    def _emit_json(self, kind: str, data: Any) -> None:
        """Emit structured JSON event."""
        try:
             payload = {
                "type": "cli_event",
                "kind": kind,
                "data": data,
                "timestamp": datetime.now().isoformat()
             }
             print(f"JSON_IPC:{json.dumps(payload)}", flush=True)
        except Exception:
             pass

    def log_event(self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a telemetry event.
        
        Args:
            event_type: Type of event
            message: Event message
            data: Optional event data
        """
        event = {
            KEYS.KEY_TIMESTAMP: datetime.now().isoformat(),
            KEYS.KEY_TYPE: event_type,
            KEYS.KEY_MESSAGE: message,
            KEYS.KEY_DATA: data or {}
        }
        self.events.append(event)
        
        # Also log to standard logging
    
    def log_command_start(self, command_name: str, args: Dict[str, Any]) -> None:
        """
        Log command start.
        
        Args:
            command_name: Name of command
            args: Command arguments
        """
        self.log_event(MSG.EVENT_COMMAND_START, MSG.LOG_STARTING_COMMAND.format(command_name=command_name), {KEYS.KEY_ARGS: args})
    
    def log_command_end(self, command_name: str, success: bool, duration: Optional[float] = None) -> None:
        """
        Log command completion.
        
        Args:
            command_name: Name of command
            success: Whether command succeeded
            duration: Command duration in seconds
        """
        data: Dict[str, Any] = {KEYS.KEY_SUCCESS: success}
        if duration is not None:
            data[KEYS.KEY_DURATION_SECONDS] = duration
        
        status = MSG.LOG_COMMAND_COMPLETED_SUCCESSFULLY.format(command_name=command_name) if success else MSG.LOG_COMMAND_FAILED.format(command_name=command_name)
        self.log_event(MSG.EVENT_COMMAND_END, status, data)
    
    def log_error(self, error: Exception, context: Optional[str] = None) -> None:
        """
        Log an error event.
        
        Args:
            error: Exception that occurred
            context: Optional context information
        """
        data = {
            KEYS.KEY_ERROR_TYPE: type(error).__name__,
            KEYS.KEY_ERROR_MESSAGE: str(error)
        }
        if context:
            data[KEYS.KEY_CONTEXT] = context
        
        self.log_event(MSG.EVENT_ERROR, MSG.LOG_ERROR_OCCURRED.format(error=error), data)
    
    def log_service_check(self, service_name: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a service check result.
        
        Args:
            service_name: Name of service
            status: Service status ('running', 'stopped', 'error')
            details: Optional service details
        """
        self.log_event(MSG.EVENT_SERVICE_CHECK, MSG.LOG_SERVICE_IS_STATUS.format(service_name=service_name, status=status), details)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get session summary.
        
        Returns:
            Session summary dictionary
        """
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        command_count = len([e for e in self.events if e[KEYS.KEY_TYPE] == MSG.EVENT_COMMAND_START])
        error_count = len([e for e in self.events if e[KEYS.KEY_TYPE] == MSG.EVENT_ERROR])
        
        return {
            KEYS.KEY_START_TIME: self.start_time.isoformat(),
            KEYS.KEY_END_TIME: end_time.isoformat(),
            KEYS.KEY_DURATION_SECONDS: duration,
            KEYS.KEY_TOTAL_EVENTS: len(self.events),
            KEYS.KEY_COMMANDS_EXECUTED: command_count,
            KEYS.KEY_ERRORS_ENCOUNTERED: error_count,
            KEYS.KEY_SUCCESS_RATE: (command_count - error_count) / max(command_count, 1) * 100
        }
    
    def print_status_table(self, services: Dict[str, Dict[str, Any]]) -> None:
        """
        Print a formatted status table for services.
        
        Args:
            services: Dictionary of service information
        """
        self._emit_json('table', {'title': MSG.UI_SERVICE_STATUS_SUMMARY, 'data': services})
    
    def print_config_table(self, config: Dict[str, Any], filter_key: Optional[str] = None) -> None:
        """
        Print a formatted configuration table.
        
        Args:
            config: Configuration dictionary
            filter_key: Optional key to filter by
        """
        self._emit_json('config', {'config': config, 'filter': filter_key})
    
    def print_success(self, message: str) -> None:
        """
        Print a success message.
        
        Args:
            message: Success message
        """
        self._emit_json('log', {'level': 'SUCCESS', 'message': message})
        self.log_event(MSG.EVENT_SUCCESS, message)
    
    def print_warning(self, message: str) -> None:
        """
        Print a warning message.
        
        Args:
            message: Warning message
        """
        self._emit_json('log', {'level': 'WARNING', 'message': message})
        self.log_event(MSG.EVENT_WARNING, message)
    
    def print_error(self, message: str) -> None:
        """
        Print an error message.
        
        Args:
            message: Error message
        """
        self._emit_json('log', {'level': 'ERROR', 'message': message})
        self.log_event(MSG.EVENT_ERROR, message)
    
    def print_info(self, message: str) -> None:
        """
        Print an info message.
        
        Args:
            message: Info message
        """
        self._emit_json('log', {'level': 'INFO', 'message': message})
        self.log_event(MSG.EVENT_INFO, message)
    
    def get_recent_events(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent events.
        
        Args:
            count: Number of recent events to return
            
        Returns:
            List of recent events
        """
        return self.events[-count:] if self.events else []
    
    def print_crawler_status(self, status: Dict[str, Any]) -> None:
        """
        Print formatted crawler status.
        
        Args:
            status: Status dictionary from crawler service
        """
        self._emit_json('crawler_status', status)
    
    def print_device_list(self, devices: List[str]) -> None:
        """
        Print a formatted list of connected devices.
        
        Args:
            devices: List of device identifiers
        """
        if not devices:
            self._emit_json('log', {'level': 'INFO', 'message': MSG.NO_CONNECTED_DEVICES_FOUND})
            return
        
        self._emit_json('device_list', devices)
    
    
    def print_model_list(self, models: List[Dict[str, Any]]) -> None:
        """
        Print a formatted list of models (OpenRouter or Ollama).
        
        Args:
            models: List of model dictionaries
        """
        if not models:
            self._emit_json('log', {'level': 'INFO', 'message': MSG.UI_NO_MODELS_AVAILABLE})
            return
        
        self._emit_json('model_list', models)
    
    def print_selected_model(self, selected_model: Optional[Dict[str, Any]]) -> None:
        """
        Print the currently selected model (OpenRouter or Ollama).
        
        Args:
            selected_model: Model dictionary or None if no model is selected
        """
        if selected_model:
            self._emit_json('selected_model', selected_model)
        else:
            self._emit_json('log', {'level': 'INFO', 'message': MSG.UI_NO_OPENROUTER_MODEL_SELECTED})
    
    def print_model_selection(self, data: Dict[str, Any]) -> None:
        """
        Print model selection result.
        
        Args:
            data: Dictionary containing selection result
        """
        self._emit_json('model_selection', data)
    
    def print_json(self, data: Dict[str, Any]) -> None:
        """
        Print data as JSON.
        
        Args:
            data: Data to print as JSON
        """
        self._emit_json('json_output', data)
        self.log_event(MSG.EVENT_JSON_OUTPUT, MSG.LOG_OUTPUT_DATA_AS_JSON)
    
    def print_package_list(self, packages: List[str]) -> None:
        """
        Print a formatted list of packages.
        
        Args:
            packages: List of package names
        """
        if not packages:
            self.print_info(MSG.LIST_PACKAGES_NO_PKGS)
        else:
            self._emit_json('package_list', packages)
        
    def confirm_action(self, prompt_message: str) -> bool:
        """
        Prompt user for confirmation with a yes/no question.
        
        Args:
            prompt_message: Message to display to the user
            
        Returns:
            True if user confirms (yes/y), False if user cancels
        """
        from cli.constants import keys as KEYS
        from cli.constants import messages as MSG
        
        self.print_warning(prompt_message)
        response = input(MSG.CLEAR_PACKAGES_PROMPT).strip().lower()
        if response not in (KEYS.INPUT_YES, KEYS.INPUT_Y):
            self.print_info(MSG.CLEAR_PACKAGES_CANCELLED)
            return False
        return True
    
    def clear_events(self) -> None:
        """Clear all events."""
        self.events.clear()
        self.log_event(MSG.EVENT_SESSION_RESET, MSG.LOG_TELEMETRY_EVENTS_CLEARED)
    
    def print_image_context_configuration(self, data: Dict[str, Any]) -> None:
        """
        Print image context configuration information.
        
        Args:
            data: Dictionary containing image context configuration data
        """
        self._emit_json('image_context_config', data)
    
    def print_model_details(self, data: Dict[str, Any]) -> None:
        """
        Print detailed model information.
        
        Args:
            data: Dictionary containing model details data
        """
        self._emit_json('model_details', data)
