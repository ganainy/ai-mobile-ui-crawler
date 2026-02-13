"""Tests for StaleRunCleaner module."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

from mobile_crawler.core.stale_run_cleaner import StaleRunCleaner
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import RunRepository, Run


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    manager = Mock(spec=DatabaseManager)
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    manager.get_connection.return_value = conn
    return manager


@pytest.fixture
def mock_run_repository(mock_db_manager):
    """Create a mock run repository."""
    return Mock(spec=RunRepository)


@pytest.fixture
def mock_traffic_manager():
    """Create a mock traffic capture manager."""
    return Mock()


@pytest.fixture
def mock_video_manager():
    """Create a mock video recording manager."""
    return Mock()


@pytest.fixture
def sample_run():
    """Create a sample run object."""
    return Run(
        id=1,
        device_id="emulator-5554",
        app_package="com.example.app",
        start_activity=None,
        start_time=datetime.fromisoformat("2024-01-10T10:00:00"),
        end_time=None,
        status="RUNNING",
        ai_provider=None,
        ai_model=None,
        total_steps=0,
        unique_screens=0
    )


@pytest.fixture
def stale_run_cleaner(
    mock_db_manager,
    mock_run_repository,
    mock_traffic_manager,
    mock_video_manager
):
    """Create a StaleRunCleaner instance with mocked dependencies."""
    with patch.object(StaleRunCleaner, '__init__', lambda self, db_manager, traffic_capture_manager=None, video_recording_manager=None: None):
        cleaner = StaleRunCleaner.__new__(StaleRunCleaner)
        cleaner.db_manager = mock_db_manager
        cleaner.run_repository = mock_run_repository
        cleaner.traffic_capture_manager = mock_traffic_manager
        cleaner.video_recording_manager = mock_video_manager
        return cleaner


class TestStaleRunCleanerInit:
    """Tests for StaleRunCleaner initialization."""

    def test_init_with_all_dependencies(self, mock_db_manager, mock_traffic_manager, mock_video_manager):
        """Test initialization with all dependencies."""
        cleaner = StaleRunCleaner(
            db_manager=mock_db_manager,
            traffic_capture_manager=mock_traffic_manager,
            video_recording_manager=mock_video_manager
        )

        assert cleaner.db_manager == mock_db_manager
        assert cleaner.traffic_capture_manager == mock_traffic_manager
        assert cleaner.video_recording_manager == mock_video_manager
        assert isinstance(cleaner.run_repository, RunRepository)

    def test_init_without_optional_dependencies(self, mock_db_manager):
        """Test initialization without optional managers."""
        cleaner = StaleRunCleaner(
            db_manager=mock_db_manager,
            traffic_capture_manager=None,
            video_recording_manager=None
        )

        assert cleaner.db_manager == mock_db_manager
        assert cleaner.traffic_capture_manager is None
        assert cleaner.video_recording_manager is None


class TestCleanupStaleRuns:
    """Tests for cleanup_stale_runs method."""

    def test_cleanup_stale_runs_success(self, stale_run_cleaner, sample_run):
        """Test successful cleanup of stale runs."""
        stale_run_cleaner._find_stale_runs = Mock(return_value=[sample_run])
        stale_run_cleaner._cleanup_single_run = Mock()

        result = stale_run_cleaner.cleanup_stale_runs()

        assert result == 1
        stale_run_cleaner._find_stale_runs.assert_called_once()
        stale_run_cleaner._cleanup_single_run.assert_called_once_with(sample_run)

    def test_cleanup_multiple_stale_runs(self, stale_run_cleaner):
        """Test cleanup of multiple stale runs."""
        run1 = Run(
            id=1, device_id="dev1", app_package="pkg1", start_activity=None,
            start_time=datetime.fromisoformat("2024-01-10T10:00:00"), end_time=None,
            status="RUNNING", ai_provider=None, ai_model=None, total_steps=0, unique_screens=0
        )
        run2 = Run(
            id=2, device_id="dev2", app_package="pkg2", start_activity=None,
            start_time=datetime.fromisoformat("2024-01-10T10:00:00"), end_time=None,
            status="RUNNING", ai_provider=None, ai_model=None, total_steps=0, unique_screens=0
        )

        stale_run_cleaner._find_stale_runs = Mock(return_value=[run1, run2])
        stale_run_cleaner._cleanup_single_run = Mock()

        result = stale_run_cleaner.cleanup_stale_runs()

        assert result == 2
        assert stale_run_cleaner._cleanup_single_run.call_count == 2

    def test_cleanup_no_stale_runs(self, stale_run_cleaner):
        """Test cleanup when no stale runs found."""
        stale_run_cleaner._find_stale_runs = Mock(return_value=[])
        stale_run_cleaner._cleanup_single_run = Mock()

        result = stale_run_cleaner.cleanup_stale_runs()

        assert result == 0
        stale_run_cleaner._cleanup_single_run.assert_not_called()

    def test_cleanup_with_failure_continues(self, stale_run_cleaner, sample_run):
        """Test that cleanup continues even if one run fails."""
        run1 = Run(
            id=1, device_id="dev1", app_package="pkg1", start_activity=None,
            start_time=datetime.fromisoformat("2024-01-10T10:00:00"), end_time=None,
            status="RUNNING", ai_provider=None, ai_model=None, total_steps=0, unique_screens=0
        )
        run2 = Run(
            id=2, device_id="dev2", app_package="pkg2", start_activity=None,
            start_time=datetime.fromisoformat("2024-01-10T10:00:00"), end_time=None,
            status="RUNNING", ai_provider=None, ai_model=None, total_steps=0, unique_screens=0
        )

        stale_run_cleaner._find_stale_runs = Mock(return_value=[run1, run2])

        def cleanup_side_effect(run):
            if run.id == 1:
                raise Exception("Cleanup failed for run 1")

        stale_run_cleaner._cleanup_single_run = Mock(side_effect=cleanup_side_effect)

        result = stale_run_cleaner.cleanup_stale_runs()

        # Should still count the successful cleanup
        assert result == 1
        assert stale_run_cleaner._cleanup_single_run.call_count == 2


class TestFindStaleRuns:
    """Tests for _find_stale_runs method."""

    def test_find_stale_runs_with_stale(self, stale_run_cleaner, sample_run):
        """Test finding stale runs."""
        # Setup mock cursor
        conn = stale_run_cleaner.db_manager.get_connection.return_value
        cursor = conn.cursor.return_value

        # Mock database query to return one running run
        cursor.fetchall.return_value = [
            (1, "emulator-5554", "com.example.app", None, "RUNNING",
             "2024-01-10T10:00:00", None, None, None, 0, 0)
        ]

        # Mock run repository to convert row to Run object
        stale_run_cleaner.run_repository._row_to_run = Mock(return_value=sample_run)
        stale_run_cleaner._is_process_running = Mock(return_value=False)

        result = stale_run_cleaner._find_stale_runs()

        assert len(result) == 1
        assert result[0] == sample_run
        cursor.execute.assert_called_once_with("SELECT * FROM runs WHERE status = 'RUNNING'")

    def test_find_stale_runs_with_active_process(self, stale_run_cleaner, sample_run):
        """Test that runs with active processes are not considered stale."""
        conn = stale_run_cleaner.db_manager.get_connection.return_value
        cursor = conn.cursor.return_value

        cursor.fetchall.return_value = [
            (1, "emulator-5554", "com.example.app", None, "RUNNING",
             "2024-01-10T10:00:00", None, None, None, 0, 0)
        ]

        stale_run_cleaner.run_repository._row_to_run = Mock(return_value=sample_run)
        stale_run_cleaner._is_process_running = Mock(return_value=True)

        result = stale_run_cleaner._find_stale_runs()

        assert len(result) == 0

    def test_find_stale_runs_multiple_runs(self, stale_run_cleaner):
        """Test finding multiple stale runs."""
        run1 = Run(
            id=1, device_id="dev1", app_package="pkg1", start_activity=None,
            start_time=datetime.fromisoformat("2024-01-10T10:00:00"), end_time=None,
            status="RUNNING", ai_provider=None, ai_model=None, total_steps=0, unique_screens=0
        )
        run2 = Run(
            id=2, device_id="dev2", app_package="pkg2", start_activity=None,
            start_time=datetime.fromisoformat("2024-01-10T10:00:00"), end_time=None,
            status="RUNNING", ai_provider=None, ai_model=None, total_steps=0, unique_screens=0
        )

        conn = stale_run_cleaner.db_manager.get_connection.return_value
        cursor = conn.cursor.return_value

        cursor.fetchall.return_value = [
            (1, "dev1", "pkg1", None, "RUNNING", "2024-01-10T10:00:00", None, None, None, 0, 0),
            (2, "dev2", "pkg2", None, "RUNNING", "2024-01-10T10:00:00", None, None, None, 0, 0)
        ]

        stale_run_cleaner.run_repository._row_to_run = Mock(side_effect=[run1, run2])
        stale_run_cleaner._is_process_running = Mock(return_value=False)

        result = stale_run_cleaner._find_stale_runs()

        assert len(result) == 2
        assert result[0] == run1
        assert result[1] == run2

    def test_find_stale_runs_no_running_runs(self, stale_run_cleaner):
        """Test when no runs are in RUNNING status."""
        conn = stale_run_cleaner.db_manager.get_connection.return_value
        cursor = conn.cursor.return_value

        cursor.fetchall.return_value = []

        result = stale_run_cleaner._find_stale_runs()

        assert len(result) == 0


class TestIsProcessRunning:
    """Tests for _is_process_running method."""

    @patch('mobile_crawler.core.stale_run_cleaner.psutil.process_iter')
    def test_is_process_running_no_crawler_processes(self, mock_process_iter, stale_run_cleaner, sample_run):
        """Test when no crawler processes are running."""
        mock_process_iter.return_value = []

        result = stale_run_cleaner._is_process_running(sample_run)

        assert result is False

    @patch('mobile_crawler.core.stale_run_cleaner.psutil.process_iter')
    def test_is_process_running_with_crawler_process(self, mock_process_iter, stale_run_cleaner, sample_run):
        """Test when crawler processes are running."""
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'python',
            'cmdline': ['python', '-m', 'mobile_crawler', 'crawl']
        }
        mock_process_iter.return_value = [mock_proc]

        result = stale_run_cleaner._is_process_running(sample_run)

        assert result is True

    @patch('mobile_crawler.core.stale_run_cleaner.psutil.process_iter')
    def test_is_process_running_python_exe(self, mock_process_iter, stale_run_cleaner, sample_run):
        """Test with python.exe process name (Windows)."""
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'python.exe',
            'cmdline': ['python.exe', '-m', 'mobile_crawler', 'crawl']
        }
        mock_process_iter.return_value = [mock_proc]

        result = stale_run_cleaner._is_process_running(sample_run)

        assert result is True

    @patch('mobile_crawler.core.stale_run_cleaner.psutil.process_iter')
    def test_is_process_running_non_crawler_process(self, mock_process_iter, stale_run_cleaner, sample_run):
        """Test with non-crawler python process."""
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'python',
            'cmdline': ['python', 'other_script.py']
        }
        mock_process_iter.return_value = [mock_proc]

        result = stale_run_cleaner._is_process_running(sample_run)

        assert result is False

    @patch('mobile_crawler.core.stale_run_cleaner.psutil.process_iter')
    def test_is_process_running_with_access_denied(self, mock_process_iter, stale_run_cleaner, sample_run):
        """Test handling of AccessDenied exception."""
        import psutil
        # Return an empty list - no processes found
        mock_process_iter.return_value = []

        result = stale_run_cleaner._is_process_running(sample_run)

        assert result is False

    @patch('mobile_crawler.core.stale_run_cleaner.psutil.process_iter')
    def test_is_process_running_with_no_such_process(self, mock_process_iter, stale_run_cleaner, sample_run):
        """Test handling of NoSuchProcess exception."""
        import psutil
        # Return an empty list - no processes found
        mock_process_iter.return_value = []

        result = stale_run_cleaner._is_process_running(sample_run)

        assert result is False


class TestCleanupSingleRun:
    """Tests for _cleanup_single_run method."""

    def test_cleanup_single_run(self, stale_run_cleaner, sample_run):
        """Test cleanup of a single run."""
        stale_run_cleaner._stop_ongoing_recordings = Mock()
        stale_run_cleaner._mark_run_as_error = Mock()

        stale_run_cleaner._cleanup_single_run(sample_run)

        stale_run_cleaner._stop_ongoing_recordings.assert_called_once_with(sample_run)
        stale_run_cleaner._mark_run_as_error.assert_called_once_with(sample_run)


class TestStopOngoingRecordings:
    """Tests for _stop_ongoing_recordings method."""

    def test_stop_both_recordings(self, stale_run_cleaner, sample_run):
        """Test stopping both video and traffic recordings."""
        stale_run_cleaner.video_recording_manager.stop_and_save = Mock()
        stale_run_cleaner.traffic_capture_manager.stop_and_pull = Mock()

        stale_run_cleaner._stop_ongoing_recordings(sample_run)

        stale_run_cleaner.video_recording_manager.stop_and_save.assert_called_once_with(sample_run.device_id)
        stale_run_cleaner.traffic_capture_manager.stop_and_pull.assert_called_once_with(sample_run.device_id)

    def test_stop_video_only(self, stale_run_cleaner, sample_run):
        """Test stopping only video recording when traffic manager is None."""
        stale_run_cleaner.traffic_capture_manager = None
        stale_run_cleaner.video_recording_manager.stop_and_save = Mock()

        stale_run_cleaner._stop_ongoing_recordings(sample_run)

        stale_run_cleaner.video_recording_manager.stop_and_save.assert_called_once_with(sample_run.device_id)

    def test_stop_traffic_only(self, stale_run_cleaner, sample_run):
        """Test stopping only traffic capture when video manager is None."""
        stale_run_cleaner.video_recording_manager = None
        stale_run_cleaner.traffic_capture_manager.stop_and_pull = Mock()

        stale_run_cleaner._stop_ongoing_recordings(sample_run)

        stale_run_cleaner.traffic_capture_manager.stop_and_pull.assert_called_once_with(sample_run.device_id)

    def test_stop_recordings_with_video_failure(self, stale_run_cleaner, sample_run):
        """Test that traffic capture stops even if video stop fails."""
        stale_run_cleaner.video_recording_manager.stop_and_save = Mock(side_effect=Exception("Video stop failed"))
        stale_run_cleaner.traffic_capture_manager.stop_and_pull = Mock()

        stale_run_cleaner._stop_ongoing_recordings(sample_run)

        stale_run_cleaner.video_recording_manager.stop_and_save.assert_called_once()
        stale_run_cleaner.traffic_capture_manager.stop_and_pull.assert_called_once()

    def test_stop_recordings_both_fail(self, stale_run_cleaner, sample_run):
        """Test handling when both recordings fail to stop."""
        stale_run_cleaner.video_recording_manager.stop_and_save = Mock(side_effect=Exception("Video error"))
        stale_run_cleaner.traffic_capture_manager.stop_and_pull = Mock(side_effect=Exception("Traffic error"))

        # Should not raise exception
        stale_run_cleaner._stop_ongoing_recordings(sample_run)

        stale_run_cleaner.video_recording_manager.stop_and_save.assert_called_once()
        stale_run_cleaner.traffic_capture_manager.stop_and_pull.assert_called_once()

    def test_stop_recordings_no_managers(self, stale_run_cleaner, sample_run):
        """Test when both managers are None."""
        stale_run_cleaner.video_recording_manager = None
        stale_run_cleaner.traffic_capture_manager = None

        # Should not raise exception
        stale_run_cleaner._stop_ongoing_recordings(sample_run)


class TestMarkRunAsError:
    """Tests for _mark_run_as_error method."""

    def test_mark_run_as_error(self, stale_run_cleaner, sample_run):
        """Test marking a run as ERROR."""
        conn = stale_run_cleaner.db_manager.get_connection.return_value
        cursor = conn.cursor.return_value

        stale_run_cleaner._mark_run_as_error(sample_run)

        cursor.execute.assert_called_once()
        execute_args = cursor.execute.call_args[0]
        assert "UPDATE runs" in execute_args[0]
        assert "SET status = 'ERROR'" in execute_args[0]
        assert execute_args[1][0] is not None  # timestamp
        assert execute_args[1][1] == sample_run.id
        conn.commit.assert_called_once()

    def test_mark_run_as_error_with_timestamp(self, stale_run_cleaner, sample_run):
        """Test that timestamp is set when marking as error."""
        conn = stale_run_cleaner.db_manager.get_connection.return_value
        cursor = conn.cursor.return_value

        before_time = datetime.now()
        stale_run_cleaner._mark_run_as_error(sample_run)
        after_time = datetime.now()

        execute_args = cursor.execute.call_args[0]
        timestamp = execute_args[1][0]
        parsed_timestamp = datetime.fromisoformat(timestamp)

        assert before_time <= parsed_timestamp <= after_time


class TestIntegration:
    """Integration tests for StaleRunCleaner."""

    @patch('mobile_crawler.core.stale_run_cleaner.psutil.process_iter')
    def test_full_cleanup_flow(self, mock_process_iter, stale_run_cleaner, sample_run):
        """Test the full cleanup flow from finding to marking as error."""
        # Setup
        mock_process_iter.return_value = []

        conn = stale_run_cleaner.db_manager.get_connection.return_value
        cursor = conn.cursor.return_value
        cursor.fetchall.return_value = [
            (1, "emulator-5554", "com.example.app", None, "RUNNING",
             "2024-01-10T10:00:00", None, None, None, 0, 0)
        ]

        stale_run_cleaner.run_repository._row_to_run = Mock(return_value=sample_run)
        stale_run_cleaner.video_recording_manager.stop_and_save = Mock()
        stale_run_cleaner.traffic_capture_manager.stop_and_pull = Mock()

        # Execute
        result = stale_run_cleaner.cleanup_stale_runs()

        # Verify
        assert result == 1
        stale_run_cleaner.video_recording_manager.stop_and_save.assert_called_once_with("emulator-5554")
        stale_run_cleaner.traffic_capture_manager.stop_and_pull.assert_called_once_with("emulator-5554")
        cursor.execute.assert_called()
        conn.commit.assert_called()
