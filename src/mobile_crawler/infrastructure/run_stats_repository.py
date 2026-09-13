"""Repository for managing runtime statistics in crawler.db."""

import logging

from typing import Any

from mobile_crawler.core.runtime_stats_collector import RuntimeStats
from mobile_crawler.infrastructure.database import DatabaseManager

logger = logging.getLogger(__name__)


class RunStatsRepository:
    """Repository for CRUD operations on run_stats table."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository with database manager.

        Args:
            db_manager: DatabaseManager instance for crawler.db
        """
        self.db_manager = db_manager

    def save_run_stats(self, stats_dict: dict[str, Any]) -> None:
        """Insert or update a run_stats row (upsert by run_id).

        Args:
            stats_dict: Dictionary from RuntimeStats.to_db_dict() plus a
                "run_id" key. run_id is UNIQUE in the table, so repeated
                saves for the same run overwrite rather than duplicate.
        """
        run_id = stats_dict.get("run_id")
        if not run_id:
            logger.warning("Cannot save run_stats: missing run_id")
            return

        columns = list(stats_dict.keys())
        col_list = ", ".join(columns)
        placeholders = ", ".join(["?"] * len(columns))
        update_set = ", ".join(
            [f"{col} = excluded.{col}" for col in columns if col != "run_id"]
        )

        query = (
            f"INSERT INTO run_stats ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT(run_id) DO UPDATE SET {update_set}"
        )

        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, tuple(stats_dict[col] for col in columns))
            conn.commit()
            logger.debug(f"Saved run_stats for run_id={run_id}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save run_stats for run_id={run_id}: {e}")
            raise

    def get_run_stats(self, run_id: int) -> RuntimeStats | None:
        """Retrieve runtime statistics for a run.

        Args:
            run_id: The run ID to fetch stats for

        Returns:
            RuntimeStats object if a row exists, None otherwise
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM run_stats WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()
        if row is None:
            return None

        columns = [desc[0] for desc in cursor.description]
        data = dict(zip(columns, row))
        return RuntimeStats.from_db_dict(data)