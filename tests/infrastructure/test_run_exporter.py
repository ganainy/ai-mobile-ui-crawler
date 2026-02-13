"""Tests for RunExporter service."""

import pytest
import json
from datetime import datetime
from pathlib import Path

from mobile_crawler.infrastructure.run_exporter import RunExporter
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import Run, RunRepository
from mobile_crawler.infrastructure.step_log_repository import StepLog, StepLogRepository


@pytest.fixture
def db_manager(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_crawler.db"
    manager = DatabaseManager(db_path)
    manager.create_schema()
    return manager


@pytest.fixture
def sample_run(db_manager):
    """Create a sample run for testing."""
    run_repo = RunRepository(db_manager)
    run = Run(
        id=None,
        device_id="test-device",
        app_package="com.test.app",
        start_activity="MainActivity",
        start_time=datetime.now(),
        end_time=None,
        status='RUNNING',
        ai_provider='gemini',
        ai_model='gemini-1.5-flash',
        total_steps=0,
        unique_screens=0
    )
    run_id = run_repo.create_run(run)
    return run_id


class TestRunExporter:
    """Tests for RunExporter."""

    def test_export_run_creates_file(self, db_manager, sample_run, tmp_path):
        """Test that export_run creates a JSON file."""
        exporter = RunExporter(db_manager)
        output_dir = tmp_path / "exports"
        
        export_path = exporter.export_run(sample_run, output_dir)
        
        assert export_path.exists()
        assert export_path.suffix == ".json"

    def test_export_run_contains_required_keys(self, db_manager, sample_run, tmp_path):
        """Test that exported JSON contains all required sections."""
        exporter = RunExporter(db_manager)
        output_dir = tmp_path / "exports"
        
        export_path = exporter.export_run(sample_run, output_dir)
        
        with open(export_path, 'r') as f:
            data = json.load(f)
        
        assert "export_timestamp" in data
        assert "run" in data
        assert "screens" in data
        assert "step_logs" in data
        assert "transitions" in data
        assert "ai_interactions" in data
        assert "statistics" in data

    def test_export_run_metadata(self, db_manager, sample_run, tmp_path):
        """Test that run metadata is correctly exported."""
        exporter = RunExporter(db_manager)
        output_dir = tmp_path / "exports"
        
        export_path = exporter.export_run(sample_run, output_dir)
        
        with open(export_path, 'r') as f:
            data = json.load(f)
        
        assert data["run"]["id"] == sample_run
        assert data["run"]["device_id"] == "test-device"
        assert data["run"]["app_package"] == "com.test.app"
        assert data["run"]["ai_provider"] == "gemini"

    def test_export_run_with_step_logs(self, db_manager, sample_run, tmp_path):
        """Test that step logs are exported."""
        from mobile_crawler.infrastructure.screen_repository import Screen, ScreenRepository
        
        # Create a screen first
        screen_repo = ScreenRepository(db_manager)
        screen = Screen(
            id=None,
            composite_hash="abc123",
            visual_hash="abc123",
            screenshot_path="/path/to/screenshot.png",
            activity_name="MainActivity",
            first_seen_run_id=sample_run,
            first_seen_step=1
        )
        screen_id = screen_repo.create_screen(screen)
        
        # Add a step log
        step_log_repo = StepLogRepository(db_manager)
        step_log = StepLog(
            id=None,
            run_id=sample_run,
            step_number=1,
            timestamp=datetime.now(),
            from_screen_id=None,
            to_screen_id=screen_id,
            action_type="click",
            action_description="Clicked button",
            target_bbox_json='{"top_left": [10, 20], "bottom_right": [100, 80]}',
            input_text=None,
            execution_success=True,
            error_message=None,
            action_duration_ms=150.0,
            ai_response_time_ms=1200.0,
            ai_reasoning="Button visible"
        )
        step_log_repo.create_step_log(step_log)
        
        exporter = RunExporter(db_manager)
        export_path = exporter.export_run(sample_run, tmp_path / "exports")
        
        with open(export_path, 'r') as f:
            data = json.load(f)
        
        assert len(data["step_logs"]) == 1
        assert data["step_logs"][0]["step_number"] == 1
        assert data["step_logs"][0]["action_type"] == "click"
        assert data["step_logs"][0]["execution_success"] is True

    def test_export_run_not_found(self, db_manager, tmp_path):
        """Test that exporting non-existent run raises error."""
        exporter = RunExporter(db_manager)
        
        with pytest.raises(ValueError, match="Run 999 not found"):
            exporter.export_run(999, tmp_path / "exports")

    def test_clean_request_json_removes_base64(self, db_manager):
        """Test that base64 screenshots are removed from request JSON."""
        exporter = RunExporter(db_manager)
        
        request_json = json.dumps({
            "user_prompt": json.dumps({
                "screenshot": "iVBORw0KGgoAAAANSUhEUgAAAAUA" + "A" * 200,
                "other_data": "keep this"
            }),
            "system_prompt": "System prompt text"
        })
        
        cleaned = exporter._clean_request_json(request_json)
        
        user_prompt_data = json.loads(cleaned["user_prompt"])
        assert user_prompt_data["screenshot"] == "[BASE64_SCREENSHOT_REMOVED]"
        assert user_prompt_data["other_data"] == "keep this"

    def test_export_statistics(self, db_manager, sample_run, tmp_path):
        """Test that statistics are correctly calculated."""
        from mobile_crawler.infrastructure.screen_repository import Screen, ScreenRepository
        
        # Create screens first
        screen_repo = ScreenRepository(db_manager)
        screen_ids = []
        for i in range(3):
            screen = Screen(
                id=None,
                composite_hash=f"hash_{i}",
                visual_hash=f"hash_{i}",
                screenshot_path=f"/path/to/screen_{i}.png",
                activity_name=f"Activity{i}",
                first_seen_run_id=sample_run,
                first_seen_step=i + 1
            )
            screen_ids.append(screen_repo.create_screen(screen))
        
        # Add some step logs
        step_log_repo = StepLogRepository(db_manager)
        for i in range(3):
            step_log = StepLog(
                id=None,
                run_id=sample_run,
                step_number=i + 1,
                timestamp=datetime.now(),
                from_screen_id=screen_ids[i - 1] if i > 0 else None,
                to_screen_id=screen_ids[i],
                action_type="click",
                action_description=f"Step {i + 1}",
                target_bbox_json=None,
                input_text=None,
                execution_success=i != 1,  # One failure
                error_message="Error" if i == 1 else None,
                action_duration_ms=100.0,
                ai_response_time_ms=500.0,
                ai_reasoning=None
            )
            step_log_repo.create_step_log(step_log)
        
        exporter = RunExporter(db_manager)
        export_path = exporter.export_run(sample_run, tmp_path / "exports")
        
        with open(export_path, 'r') as f:
            data = json.load(f)
        
        stats = data["statistics"]
        assert stats["total_steps"] == 3
        assert stats["successful_actions"] == 2
        assert stats["failed_actions"] == 1
