"""Tests for StepLogRepository."""

import pytest
from datetime import datetime, timedelta

from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.step_log_repository import StepLogRepository, StepLog
from mobile_crawler.infrastructure.run_repository import RunRepository, Run


@pytest.fixture
def db_manager_with_run(tmp_path):
    """Create a database manager with a test database and a sample run."""
    db_path = tmp_path / "test.db"
    db_manager = DatabaseManager(db_path)
    db_manager.create_schema()

    # Create a sample run
    run_repo = RunRepository(db_manager)
    sample_run = Run(
        id=None,
        device_id="test_device_123",
        app_package="com.example.test",
        start_activity="com.example.test.MainActivity",
        start_time=datetime.now(),
        end_time=None,
        status="RUNNING",
        ai_provider="gemini",
        ai_model="gemini-1.5-flash",
        total_steps=0,
        unique_screens=0
    )
    run_id = run_repo.create_run(sample_run)

    # Store the run_id for tests to use
    db_manager._test_run_id = run_id
    return db_manager


@pytest.fixture
def step_log_repository(db_manager_with_run):
    """Create a StepLogRepository instance."""
    return StepLogRepository(db_manager_with_run)


@pytest.fixture
def sample_step_log(db_manager_with_run):
    """Create a sample step log."""
    run_id = db_manager_with_run._test_run_id
    return StepLog(
        id=None,
        run_id=run_id,
        step_number=1,
        timestamp=datetime.now(),
        from_screen_id=None,
        to_screen_id=None,
        action_type="click",
        action_description="Clicked on login button",
        target_bbox_json='{"top_left": [100, 200], "bottom_right": [300, 250]}',
        input_text=None,
        execution_success=True,
        error_message=None,
        action_duration_ms=150.5,
        ai_response_time_ms=250.0,
        ai_reasoning="User needs to log in to access the app"
    )


class TestStepLogRepository:
    """Test suite for StepLogRepository."""

    def test_create_step_log(self, step_log_repository, sample_step_log):
        """Test creating a step log."""
        step_id = step_log_repository.create_step_log(sample_step_log)
        assert step_id is not None
        assert step_id > 0

    def test_get_step_logs_by_run_empty(self, step_log_repository, db_manager_with_run):
        """Test getting step logs for a run with no steps."""
        run_id = db_manager_with_run._test_run_id
        step_logs = step_log_repository.get_step_logs_by_run(run_id)
        assert step_logs == []

    def test_get_step_logs_by_run_with_data(self, step_log_repository, sample_step_log):
        """Test getting step logs for a run with data."""
        # Create a step log
        step_id = step_log_repository.create_step_log(sample_step_log)

        # Retrieve step logs
        run_id = sample_step_log.run_id
        step_logs = step_log_repository.get_step_logs_by_run(run_id)

        assert len(step_logs) == 1
        step_log = step_logs[0]
        assert step_log.id == step_id
        assert step_log.run_id == sample_step_log.run_id
        assert step_log.step_number == sample_step_log.step_number
        assert step_log.action_type == sample_step_log.action_type
        assert step_log.action_description == sample_step_log.action_description
        assert step_log.execution_success == sample_step_log.execution_success

    def test_get_exploration_journal_empty(self, step_log_repository, db_manager_with_run):
        """Test getting exploration journal for a run with no steps."""
        run_id = db_manager_with_run._test_run_id
        journal = step_log_repository.get_exploration_journal(run_id)
        assert journal == []

    def test_get_exploration_journal_with_data(self, step_log_repository, sample_step_log):
        """Test getting exploration journal with data."""
        # Create multiple step logs
        base_time = datetime.now()

        steps = []
        for i in range(5):
            step = StepLog(
                id=None,
                run_id=sample_step_log.run_id,
                step_number=i + 1,
                timestamp=base_time + timedelta(seconds=i),
                from_screen_id=None,
                to_screen_id=None,
                action_type=f"action_{i}",
                action_description=f"Description {i}",
                target_bbox_json=None,
                input_text=None,
                execution_success=True,
                error_message=None,
                action_duration_ms=100.0 + i * 10,
                ai_response_time_ms=200.0 + i * 20,
                ai_reasoning=f"Reasoning {i}"
            )
            step_id = step_log_repository.create_step_log(step)
            step.id = step_id
            steps.append(step)

        # Get exploration journal (should return most recent first, then reverse to chronological)
        journal = step_log_repository.get_exploration_journal(sample_step_log.run_id, limit=3)

        # Should return the 3 most recent steps in chronological order
        assert len(journal) == 3
        assert journal[0].step_number == 3  # Most recent of the last 3
        assert journal[1].step_number == 4
        assert journal[2].step_number == 5  # Most recent overall

    def test_get_exploration_journal_limit(self, step_log_repository, sample_step_log):
        """Test exploration journal respects limit parameter."""
        # Create 10 step logs
        base_time = datetime.now()

        for i in range(10):
            step = StepLog(
                id=None,
                run_id=sample_step_log.run_id,
                step_number=i + 1,
                timestamp=base_time + timedelta(seconds=i),
                from_screen_id=None,
                to_screen_id=None,
                action_type=f"action_{i}",
                action_description=f"Description {i}",
                target_bbox_json=None,
                input_text=None,
                execution_success=True,
                error_message=None,
                action_duration_ms=100.0,
                ai_response_time_ms=200.0,
                ai_reasoning=f"Reasoning {i}"
            )
            step_log_repository.create_step_log(step)

        # Get journal with limit 5
        journal = step_log_repository.get_exploration_journal(sample_step_log.run_id, limit=5)
        assert len(journal) == 5

        # Should be steps 6-10 in chronological order
        for i, step_log in enumerate(journal):
            assert step_log.step_number == i + 6

    def test_get_step_count_empty(self, step_log_repository, db_manager_with_run):
        """Test getting step count for a run with no steps."""
        run_id = db_manager_with_run._test_run_id
        count = step_log_repository.get_step_count(run_id)
        assert count == 0

    def test_get_step_count_with_data(self, step_log_repository, sample_step_log):
        """Test getting step count for a run with data."""
        # Create multiple step logs
        for i in range(3):
            step = StepLog(
                id=None,
                run_id=sample_step_log.run_id,
                step_number=i + 1,
                timestamp=datetime.now() + timedelta(seconds=i),
                from_screen_id=None,
                to_screen_id=None,
                action_type="click",
                action_description=f"Description {i}",
                target_bbox_json=None,
                input_text=None,
                execution_success=True,
                error_message=None,
                action_duration_ms=100.0,
                ai_response_time_ms=200.0,
                ai_reasoning=f"Reasoning {i}"
            )
            step_log_repository.create_step_log(step)

        count = step_log_repository.get_step_count(sample_step_log.run_id)
        assert count == 3

    def test_step_log_with_all_fields(self, step_log_repository, db_manager_with_run):
        """Test creating and retrieving a step log with all fields populated."""
        run_id = db_manager_with_run._test_run_id
        timestamp = datetime.now()

        step_log = StepLog(
            id=None,
            run_id=run_id,
            step_number=42,
            timestamp=timestamp,
            from_screen_id=None,  # Use None to avoid foreign key issues
            to_screen_id=None,
            action_type="input",
            action_description="Entered username",
            target_bbox_json='{"top_left": [50, 100], "bottom_right": [250, 150]}',
            input_text="testuser@example.com",
            execution_success=False,
            error_message="Element not found",
            action_duration_ms=300.5,
            ai_response_time_ms=450.0,
            ai_reasoning="Need to fill login form to proceed"
        )

        step_id = step_log_repository.create_step_log(step_log)
        retrieved_logs = step_log_repository.get_step_logs_by_run(run_id)

        assert len(retrieved_logs) == 1
        retrieved = retrieved_logs[0]

        assert retrieved.id == step_id
        assert retrieved.run_id == run_id
        assert retrieved.step_number == 42
        assert abs((retrieved.timestamp - timestamp).total_seconds()) < 1  # Close enough
        assert retrieved.from_screen_id is None
        assert retrieved.to_screen_id is None
        assert retrieved.action_type == "input"
        assert retrieved.action_description == "Entered username"
        assert retrieved.target_bbox_json == '{"top_left": [50, 100], "bottom_right": [250, 150]}'
        assert retrieved.input_text == "testuser@example.com"
        assert retrieved.execution_success == False
        assert retrieved.error_message == "Element not found"
        assert retrieved.action_duration_ms == 300.5
        assert retrieved.ai_response_time_ms == 450.0
        assert retrieved.ai_reasoning == "Need to fill login form to proceed"

    def test_delete_step_logs_by_run(self, step_log_repository, sample_step_log):
        """Test deleting all step logs for a run."""
        # Create some step logs
        for i in range(3):
            step = StepLog(
                id=None,
                run_id=sample_step_log.run_id,
                step_number=i + 1,
                timestamp=datetime.now() + timedelta(seconds=i),
                from_screen_id=None,
                to_screen_id=None,
                action_type="click",
                action_description=f"Description {i}",
                target_bbox_json=None,
                input_text=None,
                execution_success=True,
                error_message=None,
                action_duration_ms=100.0,
                ai_response_time_ms=200.0,
                ai_reasoning=f"Reasoning {i}"
            )
            step_log_repository.create_step_log(step)

        run_id = sample_step_log.run_id
        assert step_log_repository.get_step_count(run_id) == 3

        # Delete step logs
        step_log_repository.delete_step_logs_by_run(run_id)

        # Verify they're gone
        assert step_log_repository.get_step_count(run_id) == 0
        assert step_log_repository.get_step_logs_by_run(run_id) == []