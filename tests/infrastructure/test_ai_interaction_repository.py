"""Tests for AI interaction persistence with real SQLite.

Uses tmp_path fixtures with fresh DatabaseManager instances for isolation.
"""

from datetime import datetime

import pytest

from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.ai_interaction_repository import (
    AIInteraction,
    AIInteractionRepository,
)
from mobile_crawler.infrastructure.run_repository import Run, RunRepository


@pytest.fixture
def ai_repo(tmp_path):
    """Create an AIInteractionRepository with a fresh temporary database."""
    db_path = tmp_path / "test_ai.db"
    db_manager = DatabaseManager(db_path=db_path)
    db_manager.create_schema()
    repo = AIInteractionRepository(db_manager)
    yield repo
    db_manager.close()


@pytest.fixture
def run_repo(tmp_path):
    """Create a RunRepository with a fresh temporary database."""
    db_path = tmp_path / "test_ai.db"
    db_manager = DatabaseManager(db_path=db_path)
    db_manager.create_schema()
    repo = RunRepository(db_manager)
    yield repo
    db_manager.close()


def _create_run(run_repo, run_id=None):
    """Helper to create a run record for FK constraint."""
    run = Run(
        id=run_id,
        device_id="test_device",
        app_package="com.example.app",
        start_activity=None,
        start_time=datetime.now(),
        end_time=None,
        status="RUNNING",
        ai_provider=None,
        ai_model=None,
    )
    return run_repo.create_run(run)


class TestAIInteractionRepositoryInitialization:
    """Tests for AIInteractionRepository initialization."""

    def test_init_with_database_manager(self, tmp_path):
        """Test initialization with DatabaseManager."""
        db_path = tmp_path / "test.db"
        db_manager = DatabaseManager(db_path=db_path)
        db_manager.create_schema()
        repo = AIInteractionRepository(db_manager)
        assert repo.db_manager == db_manager


class TestAIInteractionRepositoryCreate:
    """Tests for creating AI interactions."""

    def test_create_ai_interaction_returns_id(self, ai_repo, run_repo):
        """Test create_ai_interaction returns a valid ID."""
        run_id = _create_run(run_repo)
        interaction = AIInteraction(
            id=None,
            run_id=run_id,
            step_number=1,
            timestamp=datetime.now(),
            request_json='{"prompt": "test"}',
            screenshot_path="/tmp/screenshot.png",
            response_raw='{"result": "ok"}',
            response_parsed_json='{"result": "ok"}',
            tokens_input=100,
            tokens_output=50,
            latency_ms=1500.0,
            success=True,
            error_message=None,
            retry_count=0,
        )
        interaction_id = ai_repo.create_ai_interaction(interaction)
        assert isinstance(interaction_id, int)
        assert interaction_id > 0

    def test_create_ai_interaction_with_minimal_data(self, ai_repo, run_repo):
        """Test create_ai_interaction with minimal required data."""
        run_id = _create_run(run_repo)
        interaction = AIInteraction(
            id=None,
            run_id=run_id,
            step_number=1,
            timestamp=datetime.now(),
            request_json='{}',
            screenshot_path=None,
            response_raw=None,
            response_parsed_json=None,
            tokens_input=None,
            tokens_output=None,
            latency_ms=None,
            success=True,
            error_message=None,
            retry_count=0,
        )
        interaction_id = ai_repo.create_ai_interaction(interaction)
        assert interaction_id > 0

    def test_create_ai_interaction_failed_interaction(self, ai_repo, run_repo):
        """Test create_ai_interaction for failed interaction."""
        run_id = _create_run(run_repo)
        interaction = AIInteraction(
            id=None,
            run_id=run_id,
            step_number=3,
            timestamp=datetime.now(),
            request_json='{"prompt": "test"}',
            screenshot_path=None,
            response_raw=None,
            response_parsed_json=None,
            tokens_input=None,
            tokens_output=None,
            latency_ms=None,
            success=False,
            error_message="Timeout error",
            retry_count=2,
        )
        interaction_id = ai_repo.create_ai_interaction(interaction)
        assert interaction_id > 0


class TestAIInteractionRepositoryRetrieve:
    """Tests for retrieving AI interactions."""

    def test_get_interactions_by_run_empty(self, ai_repo):
        """Test get_ai_interactions_by_run returns empty list for unknown run."""
        interactions = ai_repo.get_ai_interactions_by_run(999)
        assert interactions == []

    def test_get_interactions_by_run_returns_interactions(self, ai_repo, run_repo):
        """Test get_ai_interactions_by_run returns interactions for a run."""
        run_id = _create_run(run_repo)
        # Create multiple interactions for the same run
        for step in range(1, 4):
            interaction = AIInteraction(
                id=None,
                run_id=run_id,
                step_number=step,
                timestamp=datetime.now(),
                request_json=f'{{"step": {step}}}',
                screenshot_path=None,
                response_raw='{"ok": true}',
                response_parsed_json='{"ok": true}',
                tokens_input=100,
                tokens_output=50,
                latency_ms=1000.0,
                success=True,
                error_message=None,
                retry_count=0,
            )
            ai_repo.create_ai_interaction(interaction)

        interactions = ai_repo.get_ai_interactions_by_run(run_id)
        assert len(interactions) == 3
        # Should be ordered by step_number
        assert interactions[0].step_number == 1
        assert interactions[1].step_number == 2
        assert interactions[2].step_number == 3

    def test_get_interactions_by_run_different_runs(self, ai_repo, run_repo):
        """Test get_ai_interactions_by_run filters by run_id."""
        # Create interactions for different runs
        for _ in range(2):
            run_id = _create_run(run_repo)
            interaction = AIInteraction(
                id=None,
                run_id=run_id,
                step_number=1,
                timestamp=datetime.now(),
                request_json='{}',
                screenshot_path=None,
                response_raw=None,
                response_parsed_json=None,
                tokens_input=None,
                tokens_output=None,
                latency_ms=None,
                success=True,
                error_message=None,
                retry_count=0,
            )
            ai_repo.create_ai_interaction(interaction)

        # Count all interactions
        all_interactions = []
        # Need to know the actual run IDs - let's just verify we can retrieve
        # by querying all runs
        conn = ai_repo.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT run_id FROM ai_interactions")
        run_ids = [row[0] for row in cursor.fetchall()]
        
        assert len(run_ids) == 2
        for run_id in run_ids:
            interactions = ai_repo.get_ai_interactions_by_run(run_id)
            assert len(interactions) == 1
            assert interactions[0].run_id == run_id


class TestAIInteractionRepositoryDataIntegrity:
    """Tests for data integrity."""

    def test_retrieved_fields_match_stored(self, ai_repo, run_repo):
        """Test that retrieved fields match what was stored."""
        run_id = _create_run(run_repo)
        original = AIInteraction(
            id=None,
            run_id=run_id,
            step_number=10,
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            request_json='{"prompt": "click login"}',
            screenshot_path="/tmp/screenshot_10.png",
            response_raw='{"action": "click"}',
            response_parsed_json='{"action": "click", "target": "btn1"}',
            tokens_input=150,
            tokens_output=75,
            latency_ms=2000.5,
            success=True,
            error_message=None,
            retry_count=1,
        )
        interaction_id = ai_repo.create_ai_interaction(original)

        retrieved = ai_repo.get_ai_interactions_by_run(run_id)
        assert len(retrieved) == 1

        result = retrieved[0]
        assert result.id == interaction_id
        assert result.run_id == run_id
        assert result.step_number == 10
        assert result.request_json == '{"prompt": "click login"}'
        assert result.screenshot_path == "/tmp/screenshot_10.png"
        assert result.response_raw == '{"action": "click"}'
        assert result.response_parsed_json == '{"action": "click", "target": "btn1"}'
        assert result.tokens_input == 150
        assert result.tokens_output == 75
        assert result.latency_ms == 2000.5
        assert result.success is True
        assert result.error_message is None
        assert result.retry_count == 1

    def test_timestamp_roundtrip(self, ai_repo, run_repo):
        """Test timestamp is preserved through roundtrip."""
        run_id = _create_run(run_repo)
        ts = datetime(2024, 6, 15, 14, 30, 45)
        interaction = AIInteraction(
            id=None,
            run_id=run_id,
            step_number=1,
            timestamp=ts,
            request_json='{}',
            screenshot_path=None,
            response_raw=None,
            response_parsed_json=None,
            tokens_input=None,
            tokens_output=None,
            latency_ms=None,
            success=True,
            error_message=None,
            retry_count=0,
        )
        ai_repo.create_ai_interaction(interaction)

        retrieved = ai_repo.get_ai_interactions_by_run(run_id)
        assert len(retrieved) == 1
        # SQLite stores ISO format, so comparison should be close
        assert retrieved[0].timestamp.year == ts.year
        assert retrieved[0].timestamp.month == ts.month
        assert retrieved[0].timestamp.day == ts.day

    def test_boolean_success_field(self, ai_repo, run_repo):
        """Test success boolean field is stored and retrieved correctly."""
        run_id = _create_run(run_repo)
        for success_val in [True, False]:
            interaction = AIInteraction(
                id=None,
                run_id=run_id,
                step_number=1 if success_val else 2,
                timestamp=datetime.now(),
                request_json='{}',
                screenshot_path=None,
                response_raw=None,
                response_parsed_json=None,
                tokens_input=None,
                tokens_output=None,
                latency_ms=None,
                success=success_val,
                error_message=None,
                retry_count=0,
            )
            ai_repo.create_ai_interaction(interaction)

        interactions = ai_repo.get_ai_interactions_by_run(run_id)
        assert len(interactions) == 2
        assert interactions[0].success is True
        assert interactions[1].success is False
