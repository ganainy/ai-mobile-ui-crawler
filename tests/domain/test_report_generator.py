"""Tests for ReportGenerator."""

import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch

from mobile_crawler.domain.report_generator import ReportGenerator
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import Run
from mobile_crawler.infrastructure.step_log_repository import StepLog


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def test_generate_report_not_found(self):
        """Test generating report for non-existent run."""
        db_manager = Mock()
        run_repo = Mock()
        run_repo.get_run.return_value = None

        with patch('mobile_crawler.domain.report_generator.RunRepository', return_value=run_repo):
            generator = ReportGenerator(db_manager)

            with pytest.raises(ValueError, match="Run 999 not found"):
                generator.generate(999)

    @patch('mobile_crawler.domain.report_generator.SimpleDocTemplate')
    def test_generate_report_success(self, mock_doc, tmp_path):
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

        run_repo = Mock()
        run_repo.get_run.return_value = run

        # Mock stats
        stats = {
            'total_steps': 10,
            'successful_steps': 8,
            'failed_steps': 2,
            'crawl_duration_seconds': 300.0,
            'avg_step_duration_ms': 150.0,
            'unique_screens_visited': 5,
            'total_screen_visits': 12,
            'screens_per_minute': 2.4,
            'total_ai_calls': 10,
            'ai_error_count': 1,
            'stuck_detection_count': 0,
            'context_loss_count': 2
        }

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

        output_path = str(tmp_path / "test_report.pdf")

        with patch('mobile_crawler.domain.report_generator.RunRepository', return_value=run_repo), \
             patch('mobile_crawler.domain.report_generator.StepLogRepository', return_value=step_repo), \
             patch.object(ReportGenerator, '_get_runtime_stats', return_value=stats):

            generator = ReportGenerator(db_manager)
            result_path = generator.generate(1, output_path)

            assert result_path == output_path
            mock_doc.assert_called_once_with(output_path, pagesize=(612, 792))  # letter size
            mock_doc.return_value.build.assert_called_once()

    def test_get_runtime_stats_none(self):
        """Test getting stats when none exist."""
        db_manager = Mock()
        conn = Mock()
        cursor = Mock()
        cursor.fetchone.return_value = None
        conn.cursor.return_value = cursor
        db_manager.get_connection.return_value = conn

        generator = ReportGenerator(db_manager)
        result = generator._get_runtime_stats(1)

        assert result is None

    def test_get_runtime_stats_success(self):
        """Test getting runtime stats successfully."""
        db_manager = Mock()
        conn = Mock()
        cursor = Mock()
        cursor.fetchone.return_value = (1, 10, 8, 2, 300.0)  # Sample row
        cursor.description = [('run_id',), ('total_steps',), ('successful_steps',), ('failed_steps',), ('crawl_duration_seconds',)]
        conn.cursor.return_value = cursor
        db_manager.get_connection.return_value = conn

        generator = ReportGenerator(db_manager)
        result = generator._get_runtime_stats(1)

        assert result == {
            'run_id': 1,
            'total_steps': 10,
            'successful_steps': 8,
            'failed_steps': 2,
            'crawl_duration_seconds': 300.0
        }