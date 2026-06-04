"""Tests for ReportGenerator."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from mobile_crawler.domain.report_generator import ReportGenerator
from mobile_crawler.infrastructure.run_repository import Run
from mobile_crawler.infrastructure.step_log_repository import StepLog


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def test_generate_report_not_found(self):
        """Test generating report for non-existent run."""
        db_manager = Mock()
        run_repo = Mock()
        run_repo.get_run_by_id.return_value = None

        with patch('mobile_crawler.domain.report_generator.RunRepository', return_value=run_repo):
            generator = ReportGenerator(db_manager)

            with pytest.raises(ValueError, match="Run 999 not found"):
                generator.generate(999)

    def test_generate_report_success(self, tmp_path):
        """Test successful report generation."""
        # Setup mocks
        db_manager = Mock()

        # Mock run
        run = Run(
            id=1,
            device_id="device123",
            app_package="com.example.app",
            start_activity="MainActivity",
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 10, 5, 0),
            status="STOPPED",
            ai_provider="gemini",
            ai_model="gemini-pro",
            total_steps=10,
            unique_screens=5
        )
        run.session_path = str(tmp_path)

        run_repo = Mock()
        run_repo.get_run_by_id.return_value = run

        # Mock step logs
        step_logs = [
            StepLog(
                id=1,
                run_id=1,
                step_number=1,
                timestamp=datetime(2024, 1, 1, 10, 0, 30),
                from_screen_id=None,
                to_screen_id=1,
                action_type="click",
                action_description="Click login button",
                target_bbox_json='{"top_left": [100, 200], "bottom_right": [200, 250]}',
                input_text=None,
                execution_success=True,
                error_message=None,
                action_duration_ms=100.0,
                ai_response_time_ms=500.0,
                ai_reasoning="Button is visible"
            ),
            StepLog(
                id=2,
                run_id=1,
                step_number=2,
                timestamp=datetime(2024, 1, 1, 10, 1, 0),
                from_screen_id=1,
                to_screen_id=2,
                action_type="input",
                action_description="Enter username",
                target_bbox_json=None,
                input_text="testuser",
                execution_success=False,
                error_message="Element not found",
                action_duration_ms=50.0,
                ai_response_time_ms=400.0,
                ai_reasoning="Input field detected"
            )
        ]

        step_repo = Mock()
        step_repo.get_step_logs_by_run.return_value = step_logs

        ai_interaction_repo = Mock()
        ai_interaction_repo.get_ai_interactions_by_run.return_value = []

        output_path = str(tmp_path / "test_report.html")

        with patch('mobile_crawler.domain.report_generator.RunRepository', return_value=run_repo), \
             patch('mobile_crawler.domain.report_generator.StepLogRepository', return_value=step_repo), \
             patch('mobile_crawler.domain.report_generator.AIInteractionRepository', return_value=ai_interaction_repo), \
             patch('mobile_crawler.domain.report_generator.JinjaReportGenerator') as mock_jinja_cls:

            generator = ReportGenerator(db_manager)
            result_path = generator.generate(1, output_path)

            assert result_path == output_path
            mock_jinja_cls.return_value.generate.assert_called_once()

    def test_generate_report_without_output_path(self, tmp_path):
        """Test report generation without explicit output path."""
        db_manager = Mock()

        run = Run(
            id=1,
            device_id="device123",
            app_package="com.example.app",
            start_activity="MainActivity",
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 10, 5, 0),
            status="STOPPED",
            ai_provider="gemini",
            ai_model="gemini-pro",
            total_steps=10,
            unique_screens=5
        )
        run.session_path = str(tmp_path)

        run_repo = Mock()
        run_repo.get_run_by_id.return_value = run

        step_repo = Mock()
        step_repo.get_step_logs_by_run.return_value = []

        ai_interaction_repo = Mock()
        ai_interaction_repo.get_ai_interactions_by_run.return_value = []

        with patch('mobile_crawler.domain.report_generator.RunRepository', return_value=run_repo), \
             patch('mobile_crawler.domain.report_generator.StepLogRepository', return_value=step_repo), \
             patch('mobile_crawler.domain.report_generator.AIInteractionRepository', return_value=ai_interaction_repo), \
             patch('mobile_crawler.domain.report_generator.JinjaReportGenerator') as mock_jinja_cls:

            generator = ReportGenerator(db_manager)
            result_path = generator.generate(1)

            assert result_path.endswith("report_run_1.html")
            mock_jinja_cls.return_value.generate.assert_called_once()

    def test_safe_json_load(self):
        """Test _safe_json_load helper method."""
        db_manager = Mock()
        generator = ReportGenerator(db_manager)

        # Valid JSON
        result = generator._safe_json_load('{"key": "value"}')
        assert result == {"key": "value"}

        # None input
        result = generator._safe_json_load(None)
        assert result == {}

        # Invalid JSON but valid Python literal
        result = generator._safe_json_load("{'key': 'value'}")
        assert result == {"key": "value"}

        # Completely invalid
        result = generator._safe_json_load("not json at all")
        assert result == {"raw": "not json at all"}
