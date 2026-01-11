"""Run exporter for exporting complete run data to JSON."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mobile_crawler.config import get_app_data_dir
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import RunRepository
from mobile_crawler.infrastructure.step_log_repository import StepLogRepository
from mobile_crawler.infrastructure.screen_repository import ScreenRepository
from mobile_crawler.infrastructure.ai_interaction_repository import AIInteractionRepository

logger = logging.getLogger(__name__)


class RunExporter:
    """Service for exporting complete run data to JSON files.
    
    Exports all data associated with a crawl run including:
    - Run metadata
    - Discovered screens
    - Step logs with screen transitions
    - AI interactions (with paths instead of base64)
    - Aggregated statistics
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize run exporter.
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.run_repository = RunRepository(db_manager)
        self.step_log_repository = StepLogRepository(db_manager)
        self.screen_repository = ScreenRepository(db_manager)
        self.ai_interaction_repository = AIInteractionRepository(db_manager)
    
    def export_run(self, run_id: int, output_dir: Optional[Path] = None) -> Path:
        """Export complete run data to JSON file.
        
        Args:
            run_id: ID of the run to export
            output_dir: Optional output directory, defaults to app_data_dir/exports
            
        Returns:
            Path to the exported JSON file
            
        Raises:
            ValueError: If run not found
        """
        # Get run data
        run = self.run_repository.get_run(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        # Determine output path
        if output_dir is None:
            output_dir = get_app_data_dir() / "exports"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"run_{run_id}_{timestamp}.json"
        output_path = output_dir / filename
        
        # Build export data
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "run": self._export_run_metadata(run),
            "screens": self._export_screens(run_id),
            "step_logs": self._export_step_logs(run_id),
            "transitions": self._export_transitions(run_id),
            "ai_interactions": self._export_ai_interactions(run_id),
            "statistics": self._export_statistics(run_id)
        }
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Run {run_id} exported to: {output_path}")
        return output_path
    
    def _export_run_metadata(self, run) -> Dict[str, Any]:
        """Export run metadata."""
        return {
            "id": run.id,
            "device_id": run.device_id,
            "app_package": run.app_package,
            "start_activity": run.start_activity,
            "start_time": run.start_time.isoformat() if run.start_time else None,
            "end_time": run.end_time.isoformat() if run.end_time else None,
            "status": run.status,
            "ai_provider": run.ai_provider,
            "ai_model": run.ai_model,
            "total_steps": run.total_steps,
            "unique_screens": run.unique_screens
        }
    
    def _export_screens(self, run_id: int) -> List[Dict[str, Any]]:
        """Export all screens discovered in this run."""
        screens = self.screen_repository.get_screens_by_run(run_id)
        
        return [
            {
                "id": screen.id,
                "composite_hash": screen.composite_hash,
                "visual_hash": screen.visual_hash,
                "screenshot_path": screen.screenshot_path,
                "activity_name": screen.activity_name,
                "first_seen_run_id": screen.first_seen_run_id,
                "first_seen_step": screen.first_seen_step
            }
            for screen in screens
        ]
    
    def _export_step_logs(self, run_id: int) -> List[Dict[str, Any]]:
        """Export all step logs for this run."""
        step_logs = self.step_log_repository.get_step_logs_by_run(run_id)
        
        return [
            {
                "id": step.id,
                "step_number": step.step_number,
                "timestamp": step.timestamp.isoformat() if step.timestamp else None,
                "from_screen_id": step.from_screen_id,
                "to_screen_id": step.to_screen_id,
                "action_type": step.action_type,
                "action_description": step.action_description,
                "target_bbox_json": step.target_bbox_json,
                "input_text": step.input_text,
                "execution_success": step.execution_success,
                "error_message": step.error_message,
                "action_duration_ms": step.action_duration_ms,
                "ai_response_time_ms": step.ai_response_time_ms,
                "ai_reasoning": step.ai_reasoning
            }
            for step in step_logs
        ]
    
    def _export_transitions(self, run_id: int) -> List[Dict[str, Any]]:
        """Export screen transitions for this run."""
        # Query transitions from database
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT from_screen_id, to_screen_id, action_type, COUNT(*) as count
            FROM transitions
            WHERE run_id = ?
            GROUP BY from_screen_id, to_screen_id, action_type
            ORDER BY count DESC
        """, (run_id,))
        
        transitions = []
        for row in cursor.fetchall():
            transitions.append({
                "from_screen_id": row[0],
                "to_screen_id": row[1],
                "action_type": row[2],
                "count": row[3]
            })
        
        return transitions
    
    def _export_ai_interactions(self, run_id: int) -> List[Dict[str, Any]]:
        """Export AI interactions with screenshot paths instead of base64."""
        interactions = self.ai_interaction_repository.get_ai_interactions_by_run(run_id)
        
        exported = []
        for interaction in interactions:
            # Parse request JSON to extract and clean it
            request_data = self._clean_request_json(interaction.request_json)
            
            exported.append({
                "id": interaction.id,
                "step_number": interaction.step_number,
                "timestamp": interaction.timestamp.isoformat() if interaction.timestamp else None,
                "screenshot_path": interaction.screenshot_path,
                "request_prompt": request_data,
                "response_raw": interaction.response_raw,
                "response_parsed_json": interaction.response_parsed_json,
                "tokens_input": interaction.tokens_input,
                "tokens_output": interaction.tokens_output,
                "latency_ms": interaction.latency_ms,
                "success": interaction.success,
                "error_message": interaction.error_message
            })
        
        return exported
    
    def _clean_request_json(self, request_json: Optional[str]) -> Optional[Dict]:
        """Clean request JSON by removing base64 screenshot data.
        
        Args:
            request_json: Raw request JSON string
            
        Returns:
            Cleaned request data with screenshot replaced by placeholder
        """
        if not request_json:
            return None
        
        try:
            request_data = json.loads(request_json)
            
            # Check if user_prompt contains the screenshot
            if 'user_prompt' in request_data:
                user_prompt = request_data['user_prompt']
                if isinstance(user_prompt, str):
                    try:
                        # Parse the user prompt JSON
                        user_prompt_data = json.loads(user_prompt)
                        if 'screenshot' in user_prompt_data:
                            # Replace base64 with placeholder
                            user_prompt_data['screenshot'] = "[BASE64_SCREENSHOT_REMOVED]"
                            request_data['user_prompt'] = json.dumps(user_prompt_data)
                    except json.JSONDecodeError:
                        # Not valid JSON, try regex replacement
                        request_data['user_prompt'] = self._remove_base64_from_string(user_prompt)
            
            return request_data
        except json.JSONDecodeError:
            # Return as-is if can't parse
            return {"raw": self._remove_base64_from_string(request_json)}
    
    def _remove_base64_from_string(self, text: str) -> str:
        """Remove base64 encoded data from a string using regex."""
        # Match base64 patterns (long strings of alphanumeric + /+= characters)
        # Typically base64 encoded images are quite long
        pattern = r'"screenshot"\s*:\s*"[A-Za-z0-9+/=]{100,}"'
        return re.sub(pattern, '"screenshot": "[BASE64_SCREENSHOT_REMOVED]"', text)
    
    def _export_statistics(self, run_id: int) -> Dict[str, Any]:
        """Export aggregated statistics for the run."""
        step_stats = self.step_log_repository.get_step_statistics(run_id)
        ai_stats = self.step_log_repository.get_ai_statistics(run_id)
        
        # Count unique screens from step logs
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(DISTINCT to_screen_id) 
            FROM step_logs 
            WHERE run_id = ? AND to_screen_id IS NOT NULL
        """, (run_id,))
        unique_screens_visited = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM step_logs 
            WHERE run_id = ? AND to_screen_id IS NOT NULL
        """, (run_id,))
        total_screen_visits = cursor.fetchone()[0] or 0
        
        return {
            "total_steps": step_stats.get('total_steps', 0),
            "successful_actions": step_stats.get('successful_steps', 0),
            "failed_actions": step_stats.get('failed_steps', 0),
            "unique_screens_visited": unique_screens_visited,
            "total_screen_visits": total_screen_visits,
            "ai_calls": ai_stats.get('ai_calls', 0),
            "avg_ai_response_time_ms": ai_stats.get('avg_response_time_ms', 0.0)
        }
