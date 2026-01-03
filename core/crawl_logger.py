"""
Crawler-Specific Logging Module
================================

This module provides crawler-specific logging functionality using the centralized
logging infrastructure. It follows clean architecture by separating concerns:

- Domain: CrawlLogEntry (specialized log entry for crawler)
- Adapters: UIProtocolSink, DatabaseSink (crawler-specific sinks)
- Application: CrawlLogger (facade for crawler logging operations)
"""

import json
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union

# Updated import path
from core.logging_infrastructure import (
    LoggingService,
    LogEntry,
    LogLevel,
    ILogSink,
    ILogFormatter,
    get_logger
)


# ============================================================================
# DOMAIN LAYER - Crawler-specific domain objects
# ============================================================================

@dataclass(frozen=True)
class CrawlLogEntry:
    """Domain object representing a crawler-specific log entry."""
    step_count: int
    action: str
    target: str
    reasoning: str
    screen_id: Optional[int]
    success: bool
    decision_time: float
    token_count: Optional[int] = None
    error_message: Optional[str] = None
    
    def to_context(self) -> Dict[str, Any]:
        """Convert to context dictionary for logging."""
        return {
            'step': self.step_count,
            'action': self.action,
            'target': self.target,
            'screen_id': self.screen_id,
            'success': self.success,
            'decision_time': self.decision_time,
            'token_count': self.token_count,
            'error': self.error_message
        }


# ============================================================================
# ADAPTER LAYER - Specialized sinks for crawler
# ============================================================================

class UIProtocolSink(ILogSink):
    """
    Sink that writes to stdout using UI protocol format.
    
    This adapter converts log entries into the protocol format expected
    by the UI (e.g., 'UI_STEP:N', 'UI_ACTION:text', etc.)
    """
    
    def __init__(self):
        self.last_step = 0
        self.protocol_handlers = {
            'step': self._write_step,
            'action': self._write_action,
            'ai_prompt': self._write_ai_prompt,
            'ai_response': self._write_ai_response,
        }
    
    def write(self, entry: LogEntry) -> None:
        """Write log entry using UI protocol format."""
        context = entry.context
        
        # Determine protocol type from context
        protocol_type = context.get('protocol_type')
        
        if protocol_type in self.protocol_handlers:
            self.protocol_handlers[protocol_type](entry)
        else:
            # Default: write as structured log event
            # Extract basic log details
            level = getattr(entry, 'level_name', 'INFO')
            timestamp = getattr(entry, 'timestamp', datetime.now()).isoformat()
            
            self._emit_json('log', {
                'level': level,
                'message': entry.message,
                'timestamp': timestamp
            })
    
    def _write_step(self, entry: LogEntry) -> None:
        """Write step update."""
        step = entry.context.get('step', 0)
        self._emit_json('step', step)
    
    def _write_action(self, entry: LogEntry) -> None:
        """Write action information."""
        action_str = entry.message
        reasoning = entry.context.get('reasoning')
        decision_time = entry.context.get('decision_time', 0)
        
        self._emit_json('action', {
            'action': action_str,
            'reasoning': reasoning,
            'decision_time': decision_time
        })
    
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
        except Exception as e:
            # Fallback for critical failures
            print(f"JSON_IPC_ERROR:{str(e)}", flush=True)

    def _write_ai_prompt(self, entry: LogEntry) -> None:
        """Write AI prompt."""
        prompt_data = entry.context.get('prompt_data')
        if prompt_data:
            # Emit structured event for parent process
            self._emit_json('ai_prompt', prompt_data)
            
            # Service call (in-process fallback/testing)
            try:
                from infrastructure.ai_interaction_service import get_ai_interaction_service
                service = get_ai_interaction_service()
                prompt_str = prompt_data if isinstance(prompt_data, str) else json.dumps(prompt_data)
                service.record_prompt(prompt_str)
            except Exception:
                pass

    def _write_ai_response(self, entry: LogEntry) -> None:
        """Write AI response."""
        response_data = entry.context.get('response_data', {})
        
        if isinstance(response_data, dict):
            response_data = response_data.copy()
            if 'decision_time' in entry.context:
                response_data['decision_time_sec'] = round(entry.context['decision_time'], 3)
            if 'token_count' in entry.context:
                response_data['token_count'] = entry.context['token_count']
        
        # Emit structured event for parent process
        self._emit_json('ai_response', response_data)
        
        # Service call (in-process fallback/testing)
        try:
            response_json = json.dumps(response_data)
            try:
                from infrastructure.ai_interaction_service import get_ai_interaction_service
                service = get_ai_interaction_service()
                service.record_response_for_latest(response_json)
            except Exception:
                pass
        except Exception:
            pass
    
    def flush(self) -> None:
        """No buffering needed."""
        pass
    
    def close(self) -> None:
        """No cleanup needed."""
        pass


class DatabaseSink(ILogSink):
    """
    Sink that writes crawler logs to database.
    
    This adapter handles persistence of crawler logs to the database.
    """
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self._buffer: List[LogEntry] = []
        self._buffer_size = 10
    
    def write(self, entry: LogEntry) -> None:
        """Buffer log entry for database write."""
        self._buffer.append(entry)
        
        if len(self._buffer) >= self._buffer_size:
            self.flush()
    
    def flush(self) -> None:
        """Flush buffered entries to database."""
        if not self._buffer or not self.db_manager:
            return
        
        for entry in self._buffer:
            try:
                self._write_to_db(entry)
            except Exception as e:
                logging.error(f"Failed to write log to database: {e}")
        
        self._buffer.clear()
    
    def _write_to_db(self, entry: LogEntry) -> None:
        """Write a single entry to database."""
        context = entry.context
        
        # Only write entries that have step information
        if 'step' not in context:
            return
        
        # Extract relevant data from context
        run_id = context.get('run_id')
        if not run_id:
            return
        
        self.db_manager.insert_step_log(
            run_id=run_id,
            step_number=context.get('step', 0),
            from_screen_id=context.get('from_screen_id'),
            to_screen_id=context.get('to_screen_id'),
            action_description=entry.message,
            ai_suggestion_json=json.dumps(context.get('action_data')) if context.get('action_data') else None,
            mapped_action_json=json.dumps(context.get('action_data')) if context.get('action_data') else None,
            execution_success=context.get('success', False),
            error_message=context.get('error'),
            ai_response_time=context.get('decision_time', 0) * 1000,  # Convert to ms
            total_tokens=context.get('token_count'),
            ai_input_prompt=self._format_prompt(context.get('ai_prompt')),
            element_find_time_ms=context.get('element_find_time')
        )
    
    def _format_prompt(self, prompt_data: Optional[Union[str, Dict[str, Any]]]) -> Optional[str]:
        """Format AI prompt for database storage."""
        if not prompt_data:
            return None
        
        if isinstance(prompt_data, dict):
            return prompt_data.get('full_prompt', str(prompt_data))
        
        return str(prompt_data)
    
    def close(self) -> None:
        """Flush and close."""
        self.flush()


# ============================================================================
# APPLICATION LAYER - Crawler logging service
# ============================================================================

class CrawlLogger:
    """
    Facade for crawler logging operations.
    
    This class provides a clean, domain-specific API for crawler logging
    while using the centralized logging infrastructure underneath.
    """
    
    def __init__(self, db_manager=None, config=None):
        self.db_manager = db_manager
        self.config = config
        
        # Create the underlying logging service
        self._service = get_logger('crawler')
        
        # Add specialized sinks
        self._ui_sink = UIProtocolSink()
        self._service.add_sink(self._ui_sink)
        
        if db_manager:
            self._db_sink = DatabaseSink(db_manager)
            self._service.add_sink(self._db_sink)
        
        # Store OCR results for target resolution
        self._current_ocr_results: Optional[List[Dict[str, Any]]] = None
    
    def set_run_context(self, run_id: int) -> None:
        """Set the run ID context for all subsequent logs."""
        self._service.set_context(run_id=run_id)
    
    def set_ocr_results(self, ocr_results: Optional[List[Dict[str, Any]]]) -> None:
        """Set current OCR results for target resolution."""
        self._current_ocr_results = ocr_results
    
    def log_step(self, step_count: int) -> None:
        """Log current step to UI."""
        self._service.info(
            f"Step {step_count}",
            protocol_type='step',
            step=step_count
        )
        
    def log_ui_step(self, step_count: int) -> None:
        """Log current step to UI (alias for log_step)."""
        self.log_step(step_count)
    
    def log_context(
        self,
        step_count: int,
        is_stuck: bool,
        stuck_reason: str,
        action_history: List[Dict[str, Any]],
        visited_screens: List[Dict[str, Any]],
        current_screen_id: Optional[int],
        current_screen_visit_count: int,
        current_screen_actions: List[Dict[str, Any]]
    ) -> None:
        """Log crawler context (compact version)."""
        context_summary = (
            f"Step {step_count} | Screen #{current_screen_id} "
            f"(visit #{current_screen_visit_count}) | "
            f"History: {len(action_history)} actions | "
            f"Screens: {len(visited_screens)}"
        )
        
        level = LogLevel.WARNING if is_stuck else LogLevel.INFO
        
        self._service.log(
            context_summary,
            level=level,
            step=step_count,
            screen_id=current_screen_id,
            visit_count=current_screen_visit_count,
            stuck=is_stuck,
            stuck_reason=stuck_reason if is_stuck else None
        )
        
        if is_stuck:
            self._service.warning(f"[STUCK]: {stuck_reason}")
            
    def log_ai_context(
        self, step_count: int, is_stuck: bool, stuck_reason: str,
        action_history: List[Dict[str, Any]],
        visited_screens: List[Dict[str, Any]],
        current_screen_id: Optional[int],
        current_screen_visit_count: int,
        current_screen_actions: List[Dict[str, Any]]
    ):
        """Log the context being sent to the AI (compact version) - Alias for log_context."""
        self.log_context(
            step_count, is_stuck, stuck_reason,
            action_history, visited_screens,
            current_screen_id, current_screen_visit_count,
            current_screen_actions
        )
    
    def log_ai_prompt(self, ai_input_prompt: Optional[Union[str, Dict[str, Any]]]) -> None:
        """Log AI input prompt."""
        if not ai_input_prompt:
            return
        
        self._service.info(
            "AI Prompt",
            protocol_type='ai_prompt',
            prompt_data=ai_input_prompt
        )
        
    def log_ai_input_prompt(self, ai_input_prompt: Optional[Union[str, Dict[str, Any]]]):
        """Log the complete AI input prompt to the UI - Alias."""
        self.log_ai_prompt(ai_input_prompt)
    
    def log_ai_decision(
        self,
        action_data: Dict[str, Any],
        decision_time: float,
        ai_input_prompt: Optional[Union[str, Dict[str, Any]]] = None,
        ocr_results: Optional[List[Dict[str, Any]]] = None,
        token_count: Optional[int] = None
    ) -> str:
        """
        Log AI decision and return formatted action string.
        """
        if ocr_results is not None:
            self.set_ocr_results(ocr_results)
            
        # Log the prompt first
        if ai_input_prompt:
            self.log_ai_prompt(ai_input_prompt)
        
        # Resolve target to human-readable text
        target = action_data.get('target_identifier', 'unknown')
        readable_target = self._resolve_target(target)
        
        action_str = f"{action_data.get('action', 'unknown')} on {readable_target}"
        reasoning = action_data.get('reasoning', '')
        
        # Log the action
        self._service.info(
            action_str,
            protocol_type='action',
            action=action_data.get('action'),
            target=readable_target,
            reasoning=reasoning,
            decision_time=decision_time
        )
        
        # Log the response (compact)
        self._service.info(
            "AI Response",
            protocol_type='ai_response',
            response_data=action_data,
            decision_time=decision_time,
            token_count=token_count
        )
        
        return action_str
    
    def log_step_to_db(
        self,
        run_id: int,
        step_number: int,
        from_screen_id: Optional[int],
        to_screen_id: Optional[int],
        action_data: Optional[Dict[str, Any]],
        action_str: str,
        success: bool,
        ai_response_time_ms: float,
        token_count: Optional[int],
        ai_input_prompt: Optional[str],
        element_find_time_ms: Optional[float],
        error_message: Optional[str] = None
    ) -> None:
        """Log step to database."""
        if not success and not error_message:
            error_message = "Action execution failed"
        
        self._service.info(
            action_str,
            step=step_number,
            from_screen_id=from_screen_id,
            to_screen_id=to_screen_id,
            action_data=action_data,
            success=success,
            error=error_message,
            decision_time=ai_response_time_ms / 1000,  # Convert to seconds
            token_count=token_count,
            ai_prompt=ai_input_prompt,
            element_find_time=element_find_time_ms
        )
    
    def _resolve_target(self, target_identifier: Optional[str]) -> str:
        """
        Resolve target identifier to human-readable text.
        
        For OCR IDs like 'ocr_8', returns the actual text content (e.g., 'Login').
        For XML IDs, returns the ID itself.
        """
        if not target_identifier:
            return "unknown"
        
        # Check if it's an OCR ID (format: ocr_X)
        if target_identifier.startswith("ocr_") and self._current_ocr_results:
            try:
                idx = int(target_identifier.split("_")[1])
                if 0 <= idx < len(self._current_ocr_results):
                    text = self._current_ocr_results[idx].get('text', target_identifier)
                    # Truncate long text
                    if len(text) > 30:
                        text = text[:27] + "..."
                    return f"'{text}'"
            except (ValueError, IndexError):
                pass
        
        # Return the ID itself for XML identifiers
        return target_identifier
    
    def _resolve_target_to_text(
        self, target_identifier: Optional[str],
        ocr_results: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Resolve target identifier to human-readable text (Alias)."""
        if ocr_results is not None:
            self.set_ocr_results(ocr_results)
        return self._resolve_target(target_identifier)
    
    def _get_transition_message(
        self, from_id: Optional[int], to_id: Optional[int]
    ) -> str:
        """Generate transition message between screens (Helper)."""
        if to_id:
            if from_id == to_id:
                return " -> stayed on same screen"
            else:
                return f" -> navigated to Screen #{to_id}"
        return " -> no navigation"
    
    def flush(self) -> None:
        """Flush all logs."""
        self._service.flush_all()
    
    def close(self) -> None:
        """Close all sinks."""
        self._service.close_all()
