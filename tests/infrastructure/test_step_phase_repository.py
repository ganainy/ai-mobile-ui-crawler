"""Tests for StepPhaseRepository."""

import sqlite3
from datetime import datetime, timedelta

import pytest

from mobile_crawler.domain.errors import RecorderError
from mobile_crawler.domain.step_phase_models import StepPhaseTransition
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import RunRepository, Run
from mobile_crawler.infrastructure.step_log_repository import StepLogRepository, StepLog
from mobile_crawler.infrastructure.step_phase_repository import StepPhaseRepository


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
        unique_screens=0,
    )
    run_id = run_repo.create_run(sample_run)

    # Store the run_id for tests to use
    db_manager._test_run_id = run_id
    return db_manager


@pytest.fixture
def step_phase_repository(db_manager_with_run):
    """Create a StepPhaseRepository instance."""
    return StepPhaseRepository(db_manager_with_run)


@pytest.fixture
def sample_transition(db_manager_with_run):
    """Create a sample phase transition."""
    run_id = db_manager_with_run._test_run_id
    return StepPhaseTransition(
        id=None,
        run_id=run_id,
        step_number=1,
        from_phase="capture",
        to_phase="decide",
        timestamp=datetime.now(),
        action_type="click",
        duration_ms=150.5,
        metadata_json='{"extra": "info"}',
    )


class TestStepPhaseRepository:
    """Test suite for StepPhaseRepository."""

    def test_record_transition_returns_positive_id(self, step_phase_repository, sample_transition):
        """Test recording a transition returns a positive integer ID."""
        result_id = step_phase_repository.record_transition(sample_transition)
        assert result_id is not None
        assert result_id > 0

    def test_get_current_phase_returns_latest_to_phase(self, step_phase_repository, sample_transition):
        """Test get_current_phase returns the to_phase of the most recent transition."""
        step_phase_repository.record_transition(sample_transition)

        # Record another transition for the same step
        second = StepPhaseTransition(
            id=None,
            run_id=sample_transition.run_id,
            step_number=1,
            from_phase="decide",
            to_phase="execute",
            timestamp=datetime.now() + timedelta(seconds=1),
        )
        step_phase_repository.record_transition(second)

        current = step_phase_repository.get_current_phase(
            sample_transition.run_id, 1
        )
        assert current == "execute"

    def test_get_current_phase_returns_none_when_empty(self, step_phase_repository, db_manager_with_run):
        """Test get_current_phase returns None when no transitions exist."""
        run_id = db_manager_with_run._test_run_id
        result = step_phase_repository.get_current_phase(run_id, 999)
        assert result is None

    def test_get_transitions_for_step_ordered_by_timestamp(self, step_phase_repository, sample_transition):
        """Test get_transitions_for_step returns transitions ordered by timestamp ASC."""
        base_time = datetime.now()
        run_id = sample_transition.run_id

        phases = [
            ("capture", "decide", base_time),
            ("decide", "execute", base_time + timedelta(seconds=1)),
            ("execute", "record", base_time + timedelta(seconds=2)),
        ]
        for from_p, to_p, ts in phases:
            step_phase_repository.record_transition(
                StepPhaseTransition(
                    id=None,
                    run_id=run_id,
                    step_number=1,
                    from_phase=from_p,
                    to_phase=to_p,
                    timestamp=ts,
                )
            )

        transitions = step_phase_repository.get_transitions_for_step(run_id, 1)
        assert len(transitions) == 3
        assert transitions[0].from_phase == "capture"
        assert transitions[0].to_phase == "decide"
        assert transitions[1].from_phase == "decide"
        assert transitions[1].to_phase == "execute"
        assert transitions[2].from_phase == "execute"
        assert transitions[2].to_phase == "record"

    def test_get_transitions_for_run_ordered_by_step_and_time(self, step_phase_repository, db_manager_with_run):
        """Test get_transitions_for_run returns transitions ordered by step_number, timestamp."""
        run_id = db_manager_with_run._test_run_id
        base_time = datetime.now()

        # Step 1 transitions
        step_phase_repository.record_transition(
            StepPhaseTransition(
                id=None,
                run_id=run_id,
                step_number=1,
                from_phase="capture",
                to_phase="decide",
                timestamp=base_time,
            )
        )
        step_phase_repository.record_transition(
            StepPhaseTransition(
                id=None,
                run_id=run_id,
                step_number=1,
                from_phase="decide",
                to_phase="execute",
                timestamp=base_time + timedelta(seconds=1),
            )
        )

        # Step 2 transitions
        step_phase_repository.record_transition(
            StepPhaseTransition(
                id=None,
                run_id=run_id,
                step_number=2,
                from_phase="capture",
                to_phase="decide",
                timestamp=base_time + timedelta(seconds=2),
            )
        )

        transitions = step_phase_repository.get_transitions_for_run(run_id)
        assert len(transitions) == 3
        # Ordered by step_number ASC, then timestamp ASC
        assert transitions[0].step_number == 1
        assert transitions[0].from_phase == "capture"
        assert transitions[1].step_number == 1
        assert transitions[1].from_phase == "decide"
        assert transitions[2].step_number == 2

    def test_record_transition_wraps_db_error_in_recorder_error(self, db_manager_with_run):
        """Test record_transition wraps sqlite3.OperationalError in RecorderError."""
        # Create a repository with a DB that has no schema
        import tempfile
        from pathlib import Path

        bad_db_path = Path(tempfile.mktemp(suffix=".db"))
        bad_db = DatabaseManager(bad_db_path)
        # Do NOT call create_schema -- the table won't exist
        repo = StepPhaseRepository(bad_db)

        transition = StepPhaseTransition(
            id=None,
            run_id=1,
            step_number=1,
            from_phase="capture",
            to_phase="decide",
            timestamp=datetime.now(),
        )

        with pytest.raises(RecorderError) as exc_info:
            repo.record_transition(transition)

        assert exc_info.value.context.run_id == 1

        # Clean up
        try:
            bad_db_path.unlink()
        except OSError:
            pass

    def test_get_step_phase_summary_returns_dict(self, step_phase_repository, db_manager_with_run):
        """Test get_step_phase_summary returns dict with total_transitions, current_phase, timestamps."""
        run_id = db_manager_with_run._test_run_id
        base_time = datetime.now()

        step_phase_repository.record_transition(
            StepPhaseTransition(
                id=None,
                run_id=run_id,
                step_number=1,
                from_phase="capture",
                to_phase="decide",
                timestamp=base_time,
            )
        )
        step_phase_repository.record_transition(
            StepPhaseTransition(
                id=None,
                run_id=run_id,
                step_number=1,
                from_phase="decide",
                to_phase="execute",
                timestamp=base_time + timedelta(seconds=1),
            )
        )

        summary = step_phase_repository.get_step_phase_summary(run_id, 1)
        assert summary is not None
        assert summary["total_transitions"] == 2
        assert summary["current_phase"] == "execute"
        assert summary["first_transition_time"] is not None
        assert summary["last_transition_time"] is not None

    def test_get_step_phase_summary_returns_none_when_no_transitions(self, step_phase_repository, db_manager_with_run):
        """Test get_step_phase_summary returns None when no transitions exist."""
        run_id = db_manager_with_run._test_run_id
        summary = step_phase_repository.get_step_phase_summary(run_id, 999)
        assert summary is None

    def test_update_step_current_phase_sets_column(self, step_phase_repository, db_manager_with_run):
        """Test update_step_current_phase updates the current_phase column on step_logs."""
        run_id = db_manager_with_run._test_run_id

        # First create a step_log entry
        step_log_repo = StepLogRepository(db_manager_with_run)
        step_log = StepLog(
            id=None,
            run_id=run_id,
            step_number=1,
            timestamp=datetime.now(),
            from_screen_id=None,
            to_screen_id=None,
            action_type="click",
            action_description="Test step",
            target_bbox_json=None,
            input_text=None,
            execution_success=True,
            error_message=None,
            action_duration_ms=100.0,
            ai_response_time_ms=200.0,
            ai_reasoning="Test",
        )
        step_log_repo.create_step_log(step_log)

        # Update current_phase via the phase repository
        step_phase_repository.update_step_current_phase(run_id, 1, "execute")

        # Verify the column was updated
        conn = db_manager_with_run.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT current_phase FROM step_logs WHERE run_id = ? AND step_number = ?",
            (run_id, 1),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "execute"
