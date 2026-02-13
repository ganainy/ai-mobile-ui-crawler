"""Stale run cleanup for recovering crashed crawl sessions."""

import logging
from typing import List, Optional
from datetime import datetime

from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import RunRepository, Run
from mobile_crawler.domain.traffic_capture_manager import TrafficCaptureManager
from mobile_crawler.domain.video_recording_manager import VideoRecordingManager

logger = logging.getLogger(__name__)


class StaleRunCleaner:
    """Cleans up stale runs that crashed without proper shutdown.

    On application startup, unconditionally marks all runs with 'RUNNING' status
    as 'INTERRUPTED', assuming a single-instance application model where startup
    implies previous sessions have terminated.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        traffic_capture_manager: Optional[TrafficCaptureManager] = None,
        video_recording_manager: Optional[VideoRecordingManager] = None
    ):
        """Initialize stale run cleaner.

        Args:
            db_manager: Database manager for accessing runs
            traffic_capture_manager: Optional traffic capture manager for PCAP cleanup
            video_recording_manager: Optional video recording manager for video cleanup
        """
        self.db_manager = db_manager
        self.run_repository = RunRepository(db_manager)
        self.traffic_capture_manager = traffic_capture_manager
        self.video_recording_manager = video_recording_manager

    def cleanup_stale_runs(self) -> int:
        """Clean up all stale runs.

        Returns:
            Number of stale runs cleaned up
        """
        logger.info("Starting stale run cleanup")

        stale_runs = self._find_stale_runs()
        cleaned_count = 0

        for run in stale_runs:
            try:
                self._cleanup_single_run(run)
                cleaned_count += 1
                logger.info(f"Cleaned up stale run {run.id}")
            except Exception as e:
                logger.error(f"Failed to clean up stale run {run.id}: {e}")

        if cleaned_count > 0:
            logger.info(f"Stale run cleanup completed: {cleaned_count} runs marked as INTERRUPTED")
        else:
            logger.info("No stale runs found")
            
        return cleaned_count

    def _find_stale_runs(self) -> List[Run]:
        """Find runs that appear to be stale.

        Returns:
            List of runs marked as RUNNING
        """
        # Get all runs with status RUNNING
        # Since this runs on startup, ANY running run is considered stale/interrupted
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM runs WHERE status = 'RUNNING'")
        stale_runs = []

        for row in cursor.fetchall():
            run = self.run_repository._row_to_run(row)
            stale_runs.append(run)

        return stale_runs

    def _cleanup_single_run(self, run: Run) -> None:
        """Clean up a single stale run.

        Args:
            run: The stale run to clean up
        """
        logger.info(f"Cleaning up stale run {run.id} for package {run.app_package}")

        # Attempt to stop any ongoing recordings (best effort, though process likely dead)
        self._stop_ongoing_recordings(run)

        # Mark run as INTERRUPTED
        self._mark_run_as_interrupted(run)

    def _stop_ongoing_recordings(self, run: Run) -> None:
        """Stop any ongoing recordings for the run.

        Args:
            run: The run to stop recordings for
        """
        device_id = run.device_id

        # Stop video recording if manager available
        if self.video_recording_manager:
            try:
                logger.info(f"Attempting to stop video recording for run {run.id}")
                self.video_recording_manager.stop_and_save(device_id)
                logger.info(f"Video recording stopped for run {run.id}")
            except Exception as e:
                logger.warning(f"Failed to stop video recording for run {run.id}: {e}")

        # Stop traffic capture if manager available
        if self.traffic_capture_manager:
            try:
                logger.info(f"Attempting to stop traffic capture for run {run.id}")
                self.traffic_capture_manager.stop_and_pull(device_id)
                logger.info(f"Traffic capture stopped for run {run.id}")
            except Exception as e:
                logger.warning(f"Failed to stop traffic capture for run {run.id}: {e}")

    def _mark_run_as_interrupted(self, run: Run) -> None:
        """Mark a run as INTERRUPTED status.

        Args:
            run: The run to mark
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE runs
            SET status = 'INTERRUPTED', end_time = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), run.id))

        conn.commit()
        logger.info(f"Marked run {run.id} as INTERRUPTED")
