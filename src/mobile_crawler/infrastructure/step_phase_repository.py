"""Repository for managing step phase transitions in crawler.db."""

import sqlite3
from contextlib import closing
from datetime import datetime
from typing import Any, Dict, List, Optional

from mobile_crawler.domain.errors import ErrorContext, RecorderError
from mobile_crawler.domain.step_phase_models import StepPhaseTransition
from mobile_crawler.infrastructure.database import DatabaseManager


class StepPhaseRepository:
    """Repository for persisting and querying step phase transitions."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository with database manager.

        Args:
            db_manager: DatabaseManager instance for crawler.db
        """
        self.db_manager = db_manager

    def record_transition(self, transition: StepPhaseTransition) -> int:
        """Record a phase transition. Returns the inserted row ID.

        Args:
            transition: StepPhaseTransition to persist.

        Returns:
            The ID of the newly created row.

        Raises:
            RecorderError: If the database operation fails.
        """
        try:
            with closing(self.db_manager.get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO step_phase_transitions
                        (run_id, step_number, from_phase, to_phase,
                         timestamp, action_type, duration_ms, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        transition.run_id,
                        transition.step_number,
                        transition.from_phase,
                        transition.to_phase,
                        transition.timestamp.isoformat(),
                        transition.action_type,
                        transition.duration_ms,
                        transition.metadata_json,
                    ),
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.OperationalError as e:
            raise RecorderError(
                f"Failed to record phase transition: {e}",
                context=ErrorContext(run_id=transition.run_id),
                cause=e,
            ) from e

    def get_current_phase(self, run_id: int, step_number: int) -> Optional[str]:
        """Get the current phase for a step (the to_phase of the latest transition).

        Args:
            run_id: The run ID.
            step_number: The step number.

        Returns:
            The current phase string, or None if no transitions exist.
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT to_phase FROM step_phase_transitions
            WHERE run_id = ? AND step_number = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """,
            (run_id, step_number),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def get_transitions_for_step(
        self, run_id: int, step_number: int
    ) -> List[StepPhaseTransition]:
        """Get all phase transitions for a specific step, ordered chronologically.

        Args:
            run_id: The run ID.
            step_number: The step number.

        Returns:
            List of StepPhaseTransition objects ordered by timestamp ASC.
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, run_id, step_number, from_phase, to_phase,
                   timestamp, action_type, duration_ms, metadata_json
            FROM step_phase_transitions
            WHERE run_id = ? AND step_number = ?
            ORDER BY timestamp ASC
        """,
            (run_id, step_number),
        )
        return [self._row_to_transition(row) for row in cursor.fetchall()]

    def get_transitions_for_run(self, run_id: int) -> List[StepPhaseTransition]:
        """Get all phase transitions for a run, ordered by step then time.

        Args:
            run_id: The run ID.

        Returns:
            List of StepPhaseTransition objects ordered by step_number, timestamp.
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, run_id, step_number, from_phase, to_phase,
                   timestamp, action_type, duration_ms, metadata_json
            FROM step_phase_transitions
            WHERE run_id = ?
            ORDER BY step_number ASC, timestamp ASC
        """,
            (run_id,),
        )
        return [self._row_to_transition(row) for row in cursor.fetchall()]

    def get_step_phase_summary(
        self, run_id: int, step_number: int
    ) -> Optional[Dict[str, Any]]:
        """Get a summary of phase data for a step.

        Args:
            run_id: The run ID.
            step_number: The step number.

        Returns:
            Dict with total_transitions, current_phase, first/last transition times,
            or None if no transitions exist.
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) as total,
                   MIN(timestamp) as first_ts,
                   MAX(timestamp) as last_ts
            FROM step_phase_transitions
            WHERE run_id = ? AND step_number = ?
        """,
            (run_id, step_number),
        )
        row = cursor.fetchone()
        if not row or row[0] == 0:
            return None
        current = self.get_current_phase(run_id, step_number)
        return {
            "total_transitions": row[0],
            "current_phase": current,
            "first_transition_time": row[1],
            "last_transition_time": row[2],
        }

    def update_step_current_phase(
        self, run_id: int, step_number: int, phase: str
    ) -> None:
        """Update the current_phase column on step_logs for fast queries.

        Args:
            run_id: The run ID.
            step_number: The step number.
            phase: The current phase string.

        Raises:
            RecorderError: If the database operation fails.
        """
        try:
            with closing(self.db_manager.get_connection()) as conn:
                conn.execute(
                    """
                    UPDATE step_logs SET current_phase = ?
                    WHERE run_id = ? AND step_number = ?
                """,
                    (phase, run_id, step_number),
                )
                conn.commit()
        except sqlite3.OperationalError as e:
            raise RecorderError(
                f"Failed to update step current phase: {e}",
                context=ErrorContext(run_id=run_id),
                cause=e,
            ) from e

    def _row_to_transition(self, row) -> StepPhaseTransition:
        """Convert a database row to a StepPhaseTransition.

        Args:
            row: Tuple of column values from a SELECT query.

        Returns:
            StepPhaseTransition instance.
        """
        return StepPhaseTransition(
            id=row[0],
            run_id=row[1],
            step_number=row[2],
            from_phase=row[3],
            to_phase=row[4],
            timestamp=datetime.fromisoformat(row[5]),
            action_type=row[6],
            duration_ms=row[7],
            metadata_json=row[8],
        )
