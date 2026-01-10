"""Repository for managing crawl runs in crawler.db."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from mobile_crawler.infrastructure.database import DatabaseManager


@dataclass
class Run:
    """Data class representing a crawl run."""
    id: Optional[int]
    device_id: str
    app_package: str
    start_activity: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    status: str  # RUNNING, STOPPED, ERROR
    ai_provider: Optional[str]  # gemini, openrouter, ollama
    ai_model: Optional[str]  # model name used
    total_steps: int = 0
    unique_screens: int = 0


class RunRepository:
    """Repository for CRUD operations on runs table with cascading deletes."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository with database manager.

        Args:
            db_manager: DatabaseManager instance for crawler.db
        """
        self.db_manager = db_manager

    def create_run(self, run: Run) -> int:
        """Create a new run and return its ID.

        Args:
            run: Run object (id will be ignored)

        Returns:
            The ID of the newly created run
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO runs (
                device_id, app_package, start_activity, start_time, end_time,
                status, ai_provider, ai_model, total_steps, unique_screens
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run.device_id,
            run.app_package,
            run.start_activity,
            run.start_time.isoformat(),
            run.end_time.isoformat() if run.end_time else None,
            run.status,
            run.ai_provider,
            run.ai_model,
            run.total_steps,
            run.unique_screens
        ))

        run_id = cursor.lastrowid
        conn.commit()
        return run_id

    def get_run(self, run_id: int) -> Optional[Run]:
        """Get a run by ID.

        Args:
            run_id: The run ID to retrieve

        Returns:
            Run object if found, None otherwise
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_run(row)

    def get_all_runs(self) -> list[Run]:
        """Get all runs ordered by start_time descending.

        Returns:
            List of all runs
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM runs ORDER BY start_time DESC")
        rows = cursor.fetchall()

        return [self._row_to_run(row) for row in rows]

    def get_runs_by_package(self, app_package: str) -> list[Run]:
        """Get all runs for a specific app package.

        Args:
            app_package: The app package name

        Returns:
            List of runs for the package
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM runs WHERE app_package = ? ORDER BY start_time DESC",
            (app_package,)
        )
        rows = cursor.fetchall()

        return [self._row_to_run(row) for row in rows]

    def get_runs_by_status(self, status: str) -> list[Run]:
        """Get all runs with a specific status.

        Args:
            status: Status to filter by (RUNNING, STOPPED, ERROR)

        Returns:
            List of runs with the specified status
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM runs WHERE status = ? ORDER BY start_time DESC",
            (status,)
        )
        rows = cursor.fetchall()

        return [self._row_to_run(row) for row in rows]

    def update_run(self, run: Run) -> bool:
        """Update an existing run.

        Args:
            run: Run object with updated values (must have valid id)

        Returns:
            True if run was updated, False if not found
        """
        if run.id is None:
            return False

        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE runs SET
                device_id = ?, app_package = ?, start_activity = ?, start_time = ?,
                end_time = ?, status = ?, ai_provider = ?, ai_model = ?,
                total_steps = ?, unique_screens = ?
            WHERE id = ?
        """, (
            run.device_id,
            run.app_package,
            run.start_activity,
            run.start_time.isoformat(),
            run.end_time.isoformat() if run.end_time else None,
            run.status,
            run.ai_provider,
            run.ai_model,
            run.total_steps,
            run.unique_screens,
            run.id
        ))

        updated = cursor.rowcount > 0
        conn.commit()
        return updated

    def update_run_stats(self, run_id: int, total_steps: int, unique_screens: int) -> bool:
        """Update just the statistics fields of a run.

        Args:
            run_id: The run ID to update
            total_steps: New total steps count
            unique_screens: New unique screens count

        Returns:
            True if run was updated, False if not found
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE runs SET total_steps = ?, unique_screens = ?
            WHERE id = ?
        """, (total_steps, unique_screens, run_id))

        updated = cursor.rowcount > 0
        conn.commit()
        return updated

    def delete_run(self, run_id: int) -> bool:
        """Delete a run and all related data (cascading delete).

        This will delete:
        - The run record
        - All step_logs for this run
        - All transitions for this run
        - The run_stats record for this run
        - All ai_interactions for this run

        Args:
            run_id: The run ID to delete

        Returns:
            True if run was deleted, False if not found
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        # Check if run exists first
        cursor.execute("SELECT id FROM runs WHERE id = ?", (run_id,))
        if cursor.fetchone() is None:
            return False

        # Delete in order to respect foreign key constraints
        # ai_interactions first (no dependencies)
        cursor.execute("DELETE FROM ai_interactions WHERE run_id = ?", (run_id,))

        # transitions next (depends on screens, but screens may be referenced by other runs)
        cursor.execute("DELETE FROM transitions WHERE run_id = ?", (run_id,))

        # step_logs next (depends on screens)
        cursor.execute("DELETE FROM step_logs WHERE run_id = ?", (run_id,))

        # run_stats (depends on screens for most_visited_screen_id)
        cursor.execute("DELETE FROM run_stats WHERE run_id = ?", (run_id,))

        # Finally delete the run itself
        cursor.execute("DELETE FROM runs WHERE id = ?", (run_id,))

        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted

    def get_run_count(self) -> int:
        """Get total number of runs in the database.

        Returns:
            Total count of runs
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM runs")
        return cursor.fetchone()[0]

    def get_recent_runs(self, limit: int = 10) -> list[Run]:
        """Get the most recent runs.

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of most recent runs
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM runs ORDER BY start_time DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()

        return [self._row_to_run(row) for row in rows]

    def _row_to_run(self, row) -> Run:
        """Convert a database row to a Run object.

        Args:
            row: SQLite Row object

        Returns:
            Run object
        """
        return Run(
            id=row["id"],
            device_id=row["device_id"],
            app_package=row["app_package"],
            start_activity=row["start_activity"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
            status=row["status"],
            ai_provider=row["ai_provider"],
            ai_model=row["ai_model"],
            total_steps=row["total_steps"],
            unique_screens=row["unique_screens"]
        )
