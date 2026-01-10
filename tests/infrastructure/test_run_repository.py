"""Tests for run_repository.py."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import Run, RunRepository


@pytest.fixture
def temp_db_path():
    """Create a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    # Cleanup
    if path.exists():
        path.unlink()


@pytest.fixture
def db_manager(temp_db_path):
    """Create a database manager with temporary file."""
    manager = DatabaseManager(temp_db_path)
    manager.create_schema()
    yield manager
    manager.close()


@pytest.fixture
def run_repository(db_manager):
    """Create a run repository."""
    return RunRepository(db_manager)


@pytest.fixture
def sample_run():
    """Create a sample run for testing."""
    return Run(
        id=None,
        device_id="emulator-5554",
        app_package="com.example.testapp",
        start_activity="com.example.testapp.MainActivity",
        start_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        end_time=None,
        status="RUNNING",
        ai_provider="gemini",
        ai_model="gemini-1.5-flash",
        total_steps=0,
        unique_screens=0
    )


@pytest.fixture
def completed_run():
    """Create a completed run for testing."""
    return Run(
        id=None,
        device_id="emulator-5554",
        app_package="com.example.testapp",
        start_activity="com.example.testapp.MainActivity",
        start_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc),
        status="STOPPED",
        ai_provider="openrouter",
        ai_model="gpt-4",
        total_steps=150,
        unique_screens=25
    )


class TestRunRepository:
    """Test RunRepository functionality."""

    def test_create_run(self, run_repository, sample_run):
        """Test creating a new run."""
        run_id = run_repository.create_run(sample_run)

        assert run_id is not None
        assert isinstance(run_id, int)

        # Verify the run was created
        created_run = run_repository.get_run(run_id)
        assert created_run is not None
        assert created_run.id == run_id
        assert created_run.device_id == sample_run.device_id
        assert created_run.app_package == sample_run.app_package
        assert created_run.status == sample_run.status

    def test_get_run_not_found(self, run_repository):
        """Test getting a non-existent run returns None."""
        assert run_repository.get_run(999) is None

    def test_get_all_runs_empty(self, run_repository):
        """Test getting all runs when database is empty."""
        runs = run_repository.get_all_runs()
        assert runs == []

    def test_get_all_runs(self, run_repository, sample_run, completed_run):
        """Test getting all runs."""
        # Create multiple runs
        id1 = run_repository.create_run(sample_run)
        id2 = run_repository.create_run(completed_run)

        runs = run_repository.get_all_runs()

        assert len(runs) == 2
        # Should be ordered by start_time descending
        # Both have same start_time, so check that both IDs are present
        run_ids = {run.id for run in runs}
        assert run_ids == {id1, id2}

    def test_get_runs_by_package(self, run_repository, sample_run):
        """Test getting runs by app package."""
        # Create runs for different packages
        run1 = sample_run
        run2 = Run(
            id=None,
            device_id="emulator-5554",
            app_package="com.different.app",
            start_activity="com.different.app.Main",
            start_time=datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
            end_time=None,
            status="RUNNING",
            ai_provider="ollama",
            ai_model="llama2",
            total_steps=0,
            unique_screens=0
        )

        id1 = run_repository.create_run(run1)
        id2 = run_repository.create_run(run2)

        # Get runs for first package
        runs = run_repository.get_runs_by_package("com.example.testapp")
        assert len(runs) == 1
        assert runs[0].id == id1

        # Get runs for second package
        runs = run_repository.get_runs_by_package("com.different.app")
        assert len(runs) == 1
        assert runs[0].id == id2

        # Get runs for non-existent package
        runs = run_repository.get_runs_by_package("com.nonexistent.app")
        assert runs == []

    def test_get_runs_by_status(self, run_repository, sample_run, completed_run):
        """Test getting runs by status."""
        # Create runs with different statuses
        id1 = run_repository.create_run(sample_run)  # RUNNING
        id2 = run_repository.create_run(completed_run)  # STOPPED

        # Get running runs
        running_runs = run_repository.get_runs_by_status("RUNNING")
        assert len(running_runs) == 1
        assert running_runs[0].id == id1

        # Get stopped runs
        stopped_runs = run_repository.get_runs_by_status("STOPPED")
        assert len(stopped_runs) == 1
        assert stopped_runs[0].id == id2

        # Get error runs (should be empty)
        error_runs = run_repository.get_runs_by_status("ERROR")
        assert error_runs == []

    def test_update_run(self, run_repository, sample_run):
        """Test updating an existing run."""
        # Create a run
        run_id = run_repository.create_run(sample_run)

        # Get the run and modify it
        run = run_repository.get_run(run_id)
        assert run is not None

        run.status = "STOPPED"
        run.end_time = datetime(2024, 1, 1, 12, 45, 0, tzinfo=timezone.utc)
        run.total_steps = 100
        run.unique_screens = 15

        # Update it
        success = run_repository.update_run(run)
        assert success is True

        # Verify the update
        updated_run = run_repository.get_run(run_id)
        assert updated_run is not None
        assert updated_run.status == "STOPPED"
        assert updated_run.end_time == run.end_time
        assert updated_run.total_steps == 100
        assert updated_run.unique_screens == 15

    def test_update_run_not_found(self, run_repository, sample_run):
        """Test updating a non-existent run."""
        sample_run.id = 999
        success = run_repository.update_run(sample_run)
        assert success is False

    def test_update_run_stats(self, run_repository, sample_run):
        """Test updating just the statistics fields."""
        # Create a run
        run_id = run_repository.create_run(sample_run)

        # Update stats
        success = run_repository.update_run_stats(run_id, 200, 30)
        assert success is True

        # Verify the update
        run = run_repository.get_run(run_id)
        assert run is not None
        assert run.total_steps == 200
        assert run.unique_screens == 30

    def test_update_run_stats_not_found(self, run_repository):
        """Test updating stats for non-existent run."""
        success = run_repository.update_run_stats(999, 100, 10)
        assert success is False

    def test_delete_run(self, run_repository, sample_run):
        """Test deleting a run."""
        # Create a run
        run_id = run_repository.create_run(sample_run)

        # Verify it exists
        assert run_repository.get_run(run_id) is not None

        # Delete it
        success = run_repository.delete_run(run_id)
        assert success is True

        # Verify it's gone
        assert run_repository.get_run(run_id) is None

    def test_delete_run_not_found(self, run_repository):
        """Test deleting a non-existent run."""
        success = run_repository.delete_run(999)
        assert success is False

    def test_get_run_count(self, run_repository, sample_run):
        """Test getting run count."""
        # Initially empty
        assert run_repository.get_run_count() == 0

        # Add some runs
        run_repository.create_run(sample_run)
        assert run_repository.get_run_count() == 1

        run_repository.create_run(sample_run)
        assert run_repository.get_run_count() == 2

    def test_get_recent_runs(self, run_repository, sample_run):
        """Test getting recent runs."""
        # Create multiple runs
        run_ids = []
        for i in range(5):
            run = Run(
                id=None,
                device_id=f"device-{i}",
                app_package="com.example.testapp",
                start_activity="com.example.testapp.MainActivity",
                start_time=datetime(2024, 1, 1, 12 + i, 0, 0, tzinfo=timezone.utc),
                end_time=None,
                status="RUNNING",
                ai_provider="gemini",
                ai_model="gemini-1.5-flash",
                total_steps=0,
                unique_screens=0
            )
            run_id = run_repository.create_run(run)
            run_ids.append(run_id)

        # Get recent runs (limit 3)
        recent_runs = run_repository.get_recent_runs(3)
        assert len(recent_runs) == 3

        # Should be ordered by start_time descending (most recent first)
        assert recent_runs[0].id == run_ids[4]  # Latest start time
        assert recent_runs[1].id == run_ids[3]
        assert recent_runs[2].id == run_ids[2]

    def test_datetime_serialization(self, run_repository):
        """Test that datetime objects are properly serialized/deserialized."""
        start_time = datetime(2024, 1, 1, 12, 30, 45, 123456, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 13, 15, 30, 654321, tzinfo=timezone.utc)

        run = Run(
            id=None,
            device_id="test-device",
            app_package="com.test.app",
            start_activity="com.test.app.Main",
            start_time=start_time,
            end_time=end_time,
            status="STOPPED",
            ai_provider="ollama",
            ai_model="codellama",
            total_steps=50,
            unique_screens=10
        )

        # Create and retrieve
        run_id = run_repository.create_run(run)
        retrieved_run = run_repository.get_run(run_id)

        assert retrieved_run is not None
        assert retrieved_run.start_time == start_time
        assert retrieved_run.end_time == end_time

    def test_none_values_handling(self, run_repository):
        """Test handling of None values in optional fields."""
        run = Run(
            id=None,
            device_id="test-device",
            app_package="com.test.app",
            start_activity=None,  # None value
            start_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            end_time=None,  # None value
            status="RUNNING",
            ai_provider=None,  # None value
            ai_model=None,  # None value
            total_steps=0,
            unique_screens=0
        )

        run_id = run_repository.create_run(run)
        retrieved_run = run_repository.get_run(run_id)

        assert retrieved_run is not None
        assert retrieved_run.start_activity is None
        assert retrieved_run.end_time is None
        assert retrieved_run.ai_provider is None
        assert retrieved_run.ai_model is None
