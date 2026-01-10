"""Stale run cleanup for recovering crashed crawl sessions."""

import logging
import psutil
from typing import List, Optional

from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import RunRepository, Run
from mobile_crawler.domain.traffic_capture_manager import TrafficCaptureManager
from mobile_crawler.domain.video_recording_manager import VideoRecordingManager

logger = logging.getLogger(__name__)


class StaleRunCleaner:
    """Cleans up stale runs that crashed without proper shutdown.

    On application startup, identifies runs marked as RUNNING but with
    no active process, then attempts to recover partial artifacts and
    mark the runs as ERROR.
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

        logger.info(f"Stale run cleanup completed: {cleaned_count} runs cleaned")
        return cleaned_count

    def _find_stale_runs(self) -> List[Run]:
        """Find runs that appear to be stale.

        Returns:
            List of runs marked as RUNNING but with no active process
        """
        # Get all runs with status RUNNING
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM runs WHERE status = 'RUNNING'")
        running_runs = []

        for row in cursor.fetchall():
            run = self.run_repository._row_to_run(row)
            running_runs.append(run)

        # Filter to only those with no active process
        stale_runs = []
        for run in running_runs:
            if not self._is_process_running(run):
                stale_runs.append(run)

        logger.info(f"Found {len(stale_runs)} stale runs out of {len(running_runs)} running runs")
        return stale_runs

    def _is_process_running(self, run: Run) -> bool:
        """Check if there's an active process for this run.

        This is a simplified check - in a real implementation, you might
        store process IDs or use other mechanisms to track active crawls.

        Args:
            run: The run to check

        Returns:
            True if process appears to be running
        """
        # For now, we'll assume no runs are actively running on startup
        # In a real implementation, you might check for:
        # - Process IDs stored in database
        # - Lock files
        # - Active Appium sessions
        # - etc.

        # Check if there are any python processes that might be crawlers
        crawler_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python.exe' or proc.info['name'] == 'python':
                    cmdline = proc.info['cmdline'] or []
                    if any('mobile_crawler' in arg or 'crawler' in arg for arg in cmdline):
                        crawler_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # If there are crawler processes running, assume they might be active
        # This is a very basic heuristic
        return len(crawler_processes) > 0

    def _cleanup_single_run(self, run: Run) -> None:
        """Clean up a single stale run.

        Args:
            run: The stale run to clean up
        """
        logger.info(f"Cleaning up stale run {run.id} for package {run.app_package}")

        # Attempt to stop any ongoing recordings
        self._stop_ongoing_recordings(run)

        # Mark run as ERROR
        self._mark_run_as_error(run)

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

    def _mark_run_as_error(self, run: Run) -> None:
        """Mark a run as ERROR status.

        Args:
            run: The run to mark as error
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        from datetime import datetime
        cursor.execute("""
            UPDATE runs
            SET status = 'ERROR', end_time = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), run.id))

        conn.commit()
        logger.info(f"Marked run {run.id} as ERROR")