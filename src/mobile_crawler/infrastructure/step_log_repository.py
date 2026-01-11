"""Repository for managing step logs in crawler.db."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from mobile_crawler.infrastructure.database import DatabaseManager


@dataclass
class StepLog:
    """Data class representing a step in a crawl run."""
    id: Optional[int]
    run_id: int
    step_number: int
    timestamp: datetime
    from_screen_id: Optional[int]
    to_screen_id: Optional[int]
    action_type: str  # click, input, scroll_down, etc.
    action_description: Optional[str]  # human-readable
    target_bbox_json: Optional[str]  # {"top_left": [...], "bottom_right": [...]}
    input_text: Optional[str]  # for input actions
    execution_success: bool
    error_message: Optional[str]
    action_duration_ms: Optional[float]
    ai_response_time_ms: Optional[float]
    ai_reasoning: Optional[str]  # AI's reasoning for this action


class StepLogRepository:
    """Repository for CRUD operations on step_logs table."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository with database manager.

        Args:
            db_manager: DatabaseManager instance for crawler.db
        """
        self.db_manager = db_manager

    def create_step_log(self, step_log: StepLog) -> int:
        """Create a new step log and return its ID.

        Args:
            step_log: StepLog object (id will be ignored)

        Returns:
            The ID of the newly created step log
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO step_logs (
                run_id, step_number, timestamp, from_screen_id, to_screen_id,
                action_type, action_description, target_bbox_json, input_text,
                execution_success, error_message, action_duration_ms,
                ai_response_time_ms, ai_reasoning
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            step_log.run_id,
            step_log.step_number,
            step_log.timestamp.isoformat(),
            step_log.from_screen_id,
            step_log.to_screen_id,
            step_log.action_type,
            step_log.action_description,
            step_log.target_bbox_json,
            step_log.input_text,
            step_log.execution_success,
            step_log.error_message,
            step_log.action_duration_ms,
            step_log.ai_response_time_ms,
            step_log.ai_reasoning
        ))

        conn.commit()
        return cursor.lastrowid

    def get_step_logs_by_run(self, run_id: int) -> List[StepLog]:
        """Get all step logs for a specific run.

        Args:
            run_id: The run ID to filter by

        Returns:
            List of StepLog objects for the run
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, run_id, step_number, timestamp, from_screen_id, to_screen_id,
                   action_type, action_description, target_bbox_json, input_text,
                   execution_success, error_message, action_duration_ms,
                   ai_response_time_ms, ai_reasoning
            FROM step_logs
            WHERE run_id = ?
            ORDER BY step_number
        """, (run_id,))

        step_logs = []
        for row in cursor.fetchall():
            step_logs.append(StepLog(
                id=row[0],
                run_id=row[1],
                step_number=row[2],
                timestamp=datetime.fromisoformat(row[3]),
                from_screen_id=row[4],
                to_screen_id=row[5],
                action_type=row[6],
                action_description=row[7],
                target_bbox_json=row[8],
                input_text=row[9],
                execution_success=bool(row[10]),
                error_message=row[11],
                action_duration_ms=row[12],
                ai_response_time_ms=row[13],
                ai_reasoning=row[14]
            ))

        return step_logs

    def get_exploration_journal(self, run_id: int, limit: int = 15) -> List[StepLog]:
        """Get recent step logs for exploration journal (most recent first).

        Args:
            run_id: The run ID to get journal for
            limit: Maximum number of recent steps to return

        Returns:
            List of most recent StepLog objects for the run
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, run_id, step_number, timestamp, from_screen_id, to_screen_id,
                   action_type, action_description, target_bbox_json, input_text,
                   execution_success, error_message, action_duration_ms,
                   ai_response_time_ms, ai_reasoning
            FROM step_logs
            WHERE run_id = ?
            ORDER BY step_number DESC
            LIMIT ?
        """, (run_id, limit))

        step_logs = []
        for row in cursor.fetchall():
            step_logs.append(StepLog(
                id=row[0],
                run_id=row[1],
                step_number=row[2],
                timestamp=datetime.fromisoformat(row[3]),
                from_screen_id=row[4],
                to_screen_id=row[5],
                action_type=row[6],
                action_description=row[7],
                target_bbox_json=row[8],
                input_text=row[9],
                execution_success=bool(row[10]),
                error_message=row[11],
                action_duration_ms=row[12],
                ai_response_time_ms=row[13],
                ai_reasoning=row[14]
            ))

        # Reverse to get chronological order (oldest first)
        return list(reversed(step_logs))

    def get_step_count(self, run_id: int) -> int:
        """Get the total number of steps for a run.

        Args:
            run_id: The run ID to count steps for

        Returns:
            Number of steps in the run
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM step_logs WHERE run_id = ?
        """, (run_id,))

        return cursor.fetchone()[0]

    def delete_step_logs_by_run(self, run_id: int):
        """Delete all step logs for a specific run.

        Args:
            run_id: The run ID to delete step logs for
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM step_logs WHERE run_id = ?", (run_id,))
        conn.commit()

    def get_step_statistics(self, run_id: int) -> dict:
        """Get aggregated step statistics for a run.
        
        Returns:
            {
                'total_steps': int,
                'successful_steps': int,
                'failed_steps': int
            }
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_steps,
                SUM(CASE WHEN execution_success = 1 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN execution_success = 0 THEN 1 ELSE 0 END) as failed
            FROM step_logs 
            WHERE run_id = ?
        """, (run_id,))
        
        row = cursor.fetchone()
        if not row:
            return {'total_steps': 0, 'successful_steps': 0, 'failed_steps': 0}
        
        return {
            'total_steps': row[0] or 0,
            'successful_steps': row[1] or 0,
            'failed_steps': row[2] or 0
        }

    def get_ai_statistics(self, run_id: int) -> dict:
        """Get AI performance statistics for a run.
        
        Returns:
            {
                'ai_calls': int,
                'avg_response_time_ms': float
            }
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as ai_calls,
                AVG(ai_response_time_ms) as avg_response_time
            FROM step_logs 
            WHERE run_id = ? AND ai_response_time_ms IS NOT NULL
        """, (run_id,))
        
        row = cursor.fetchone()
        if not row:
            return {'ai_calls': 0, 'avg_response_time_ms': 0.0}
        
        return {
            'ai_calls': row[0] or 0,
            'avg_response_time_ms': row[1] or 0.0
        }

    def count_screen_visits_for_run(self, run_id: int) -> int:
        """Count total screen visits (including revisits) for a run."""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM step_logs 
            WHERE run_id = ? 
                AND (from_screen_id IS NOT NULL OR to_screen_id IS NOT NULL)
        """, (run_id,))
        
        row = cursor.fetchone()
        return row[0] if row else 0