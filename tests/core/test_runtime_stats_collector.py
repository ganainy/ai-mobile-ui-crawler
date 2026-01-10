"""Tests for RuntimeStatsCollector."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from mobile_crawler.core.runtime_stats_collector import (
    RuntimeStats,
    RuntimeStatsCollector,
)


class TestRuntimeStats:
    """Tests for RuntimeStats dataclass."""

    def test_initialization(self):
        """Test stats initialization with default values."""
        stats = RuntimeStats()

        assert stats.total_steps == 0
        assert stats.successful_steps == 0
        assert stats.failed_steps == 0
        assert stats.unique_screens_visited == 0
        assert stats.total_ai_calls == 0
        assert stats.actions_by_type == {}

    def test_to_db_dict(self):
        """Test conversion to database dictionary."""
        stats = RuntimeStats(
            total_steps=10,
            successful_steps=8,
            failed_steps=2,
            unique_screens_visited=5,
            actions_by_type={"click": 5, "scroll_down": 3},
            device_model="Pixel 5",
            android_version="13.0",
        )

        db_dict = stats.to_db_dict()

        assert db_dict["total_steps"] == 10
        assert db_dict["successful_steps"] == 8
        assert db_dict["failed_steps"] == 2
        assert db_dict["unique_screens_visited"] == 5
        assert "click" in db_dict["actions_by_type_json"]
        assert db_dict["device_model"] == "Pixel 5"
        assert db_dict["android_version"] == "13.0"


class TestRuntimeStatsCollector:
    """Tests for RuntimeStatsCollector."""

    def test_init(self):
        """Test initialization."""
        mock_repo = Mock()
        collector = RuntimeStatsCollector(run_id=100, run_stats_repository=mock_repo)

        assert collector._run_id == 100
        assert collector._run_stats_repository is mock_repo
        assert collector._stats.total_steps == 0
        assert collector._screen_visit_counts == {}
        assert collector._transition_set == set()

    def test_record_step_start(self):
        """Test recording step start."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_step_start()
        assert collector._stats.total_steps == 1

        collector.record_step_start()
        assert collector._stats.total_steps == 2

    def test_record_step_success(self):
        """Test recording successful step."""
        collector = RuntimeStatsCollector(run_id=100)
        collector.record_step_start()

        collector.record_step_success(duration_ms=500.0)

        assert collector._stats.successful_steps == 1
        assert collector._stats.failed_steps == 0
        assert collector._stats.avg_step_duration_ms == 500.0

    def test_record_step_failure(self):
        """Test recording failed step."""
        collector = RuntimeStatsCollector(run_id=100)
        collector.record_step_start()

        collector.record_step_failure(duration_ms=300.0, error_message="Element not found")

        assert collector._stats.successful_steps == 0
        assert collector._stats.failed_steps == 1
        assert collector._stats.avg_step_duration_ms == 300.0

    def test_record_screen_visit(self):
        """Test recording screen visits."""
        collector = RuntimeStatsCollector(run_id=100)

        # First visit to screen 1
        collector.record_screen_visit(screen_id=1, navigation_depth=1)
        assert collector._stats.unique_screens_visited == 1
        assert collector._stats.total_screen_visits == 1
        assert collector._stats.most_visited_screen_id == 1
        assert collector._stats.most_visited_screen_count == 1
        assert collector._stats.deepest_navigation_depth == 1

        # Second visit to screen 1
        collector.record_screen_visit(screen_id=1, navigation_depth=1)
        assert collector._stats.unique_screens_visited == 1  # No change
        assert collector._stats.total_screen_visits == 2
        assert collector._stats.most_visited_screen_count == 2

        # Visit to new screen 2
        collector.record_screen_visit(screen_id=2, navigation_depth=2)
        assert collector._stats.unique_screens_visited == 2
        assert collector._stats.deepest_navigation_depth == 2

    def test_record_action(self):
        """Test recording action execution."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_action(action_type="click", success=True, duration_ms=100.0)
        assert collector._stats.actions_by_type["click"] == 1
        assert collector._stats.successful_actions_by_type["click"] == 1
        assert "click" not in collector._stats.failed_actions_by_type
        assert collector._stats.min_action_duration_ms == 100.0
        assert collector._stats.max_action_duration_ms == 100.0

        collector.record_action(action_type="input", success=False, duration_ms=200.0)
        assert collector._stats.actions_by_type["input"] == 1
        assert collector._stats.failed_actions_by_type["input"] == 1
        assert "input" not in collector._stats.successful_actions_by_type

    def test_record_ai_call(self):
        """Test recording AI call."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_ai_call(response_time_ms=1000.0, tokens_used=100, success=True)

        assert collector._stats.total_ai_calls == 1
        assert collector._stats.total_ai_tokens_used == 100
        assert collector._stats.ai_timeout_count == 0
        assert collector._stats.ai_error_count == 0
        assert collector._stats.avg_ai_response_time_ms == 1000.0
        assert collector._stats.min_ai_response_time_ms == 1000.0
        assert collector._stats.max_ai_response_time_ms == 1000.0

    def test_record_ai_call_timeout(self):
        """Test recording AI call timeout."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_ai_call(response_time_ms=5000.0, tokens_used=0, success=False, timeout=True)

        assert collector._stats.total_ai_calls == 1
        assert collector._stats.ai_timeout_count == 1
        assert collector._stats.ai_error_count == 0

    def test_record_ai_call_error(self):
        """Test recording AI call error."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_ai_call(response_time_ms=500.0, tokens_used=0, success=False, timeout=False)

        assert collector._stats.total_ai_calls == 1
        assert collector._stats.ai_timeout_count == 0
        assert collector._stats.ai_error_count == 1

    def test_record_ai_retry(self):
        """Test recording AI retry."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_ai_retry()
        assert collector._stats.ai_retry_count == 1

        collector.record_ai_retry()
        assert collector._stats.ai_retry_count == 2

    def test_record_invalid_response(self):
        """Test recording invalid response."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_invalid_response()
        assert collector._stats.invalid_response_count == 1

        collector.record_invalid_response()
        assert collector._stats.invalid_response_count == 2

    def test_record_batch(self):
        """Test recording batch of actions."""
        collector = RuntimeStatsCollector(run_id=100)

        # Single action batch
        collector.record_batch(action_count=1, success=True)
        assert collector._stats.single_action_count == 1
        assert collector._stats.multi_action_batch_count == 0
        assert collector._stats.total_batch_actions == 1
        assert collector._stats.max_batch_size == 1
        assert collector._stats.avg_batch_size == 1.0
        assert collector._stats.batch_success_rate == 1.0

        # Multi-action batch
        collector.record_batch(action_count=3, success=True)
        assert collector._stats.multi_action_batch_count == 1
        assert collector._stats.single_action_count == 1
        assert collector._stats.total_batch_actions == 4
        assert collector._stats.max_batch_size == 3
        assert collector._stats.avg_batch_size == 2.0

        # Failed batch
        collector.record_batch(action_count=2, success=False)
        assert collector._stats.batch_success_rate == 2.0 / 3.0

    def test_record_stuck_detection(self):
        """Test recording stuck detection."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_stuck_detection()
        assert collector._stats.stuck_detection_count == 1

        collector.record_stuck_detection()
        assert collector._stats.stuck_detection_count == 2

    def test_record_stuck_recovery(self):
        """Test recording stuck recovery."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_stuck_recovery(success=True)
        assert collector._stats.stuck_recovery_success == 1

        collector.record_stuck_recovery(success=False)
        assert collector._stats.stuck_recovery_success == 1  # No change

    def test_record_app_crash(self):
        """Test recording app crash."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_app_crash()
        assert collector._stats.app_crash_count == 1

        collector.record_app_crash()
        assert collector._stats.app_crash_count == 2

    def test_record_app_relaunch(self):
        """Test recording app relaunch."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_app_relaunch()
        assert collector._stats.app_relaunch_count == 1

    def test_record_context_loss(self):
        """Test recording context loss."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_context_loss()
        assert collector._stats.context_loss_count == 1

        collector.record_context_loss()
        assert collector._stats.context_loss_count == 2

    def test_record_context_recovery(self):
        """Test recording context recovery."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_context_recovery()
        assert collector._stats.context_recovery_count == 1

    def test_record_invalid_bbox(self):
        """Test recording invalid bounding box."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_invalid_bbox()
        assert collector._stats.invalid_bbox_count == 1

        collector.record_invalid_bbox()
        assert collector._stats.invalid_bbox_count == 2

    def test_set_device_info(self):
        """Test setting device information."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.set_device_info(
            device_id="emulator-5554",
            device_model="Pixel 5",
            android_version="13.0",
            screen_width=1080,
            screen_height=2400,
        )

        assert collector._stats.device_id == "emulator-5554"
        assert collector._stats.device_model == "Pixel 5"
        assert collector._stats.android_version == "13.0"
        assert collector._stats.screen_width == 1080
        assert collector._stats.screen_height == 2400

    def test_set_app_info(self):
        """Test setting app information."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.set_app_info(app_package="com.example.app", app_version="1.2.3")

        assert collector._stats.app_package == "com.example.app"
        assert collector._stats.app_version == "1.2.3"

    def test_set_app_info_no_version(self):
        """Test setting app info without version."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.set_app_info(app_package="com.example.app")

        assert collector._stats.app_package == "com.example.app"
        assert collector._stats.app_version is None

    def test_start_and_end_session(self):
        """Test session start and end."""
        import time
        collector = RuntimeStatsCollector(run_id=100)

        assert collector._stats.session_start_time is None
        assert collector._stats.session_end_time is None

        collector.start_session()
        start_time = collector._stats.session_start_time
        assert start_time is not None
        assert isinstance(start_time, datetime)

        # Simulate some time passing
        time.sleep(0.001)  # Small delay to ensure times differ
        collector.end_session()
        assert collector._stats.session_end_time is not None
        assert collector._stats.session_end_time > start_time
        assert collector._stats.crawl_duration_seconds > 0

    def test_record_pcap_stats(self):
        """Test recording PCAP statistics."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_pcap_stats(file_size_bytes=1024000, packet_count=5000)

        assert collector._stats.pcap_file_size_bytes == 1024000
        assert collector._stats.pcap_packet_count == 5000

    def test_record_pcap_stats_no_packets(self):
        """Test recording PCAP stats without packet count."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_pcap_stats(file_size_bytes=1024000)

        assert collector._stats.pcap_file_size_bytes == 1024000
        assert collector._stats.pcap_packet_count is None

    def test_record_mobsf_results(self):
        """Test recording MobSF results."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_mobsf_results(
            security_score=75.5,
            high_issues=2,
            medium_issues=5,
            low_issues=10,
        )

        assert collector._stats.mobsf_security_score == 75.5
        assert collector._stats.mobsf_high_issues == 2
        assert collector._stats.mobsf_medium_issues == 5
        assert collector._stats.mobsf_low_issues == 10

    def test_record_video_stats(self):
        """Test recording video statistics."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_video_stats(file_size_bytes=5120000, duration_seconds=120.5)

        assert collector._stats.video_file_size_bytes == 5120000
        assert collector._stats.video_duration_seconds == 120.5

    def test_record_transition(self):
        """Test recording screen transitions."""
        collector = RuntimeStatsCollector(run_id=100)

        # First transition
        collector.record_transition(from_screen_id=1, to_screen_id=2, action_type="click")
        assert collector._stats.transition_count == 1
        assert collector._stats.unique_transitions == 1
        assert collector._stats.navigation_graph_edges == 1

        # Same transition again (should not increment unique)
        collector.record_transition(from_screen_id=1, to_screen_id=2, action_type="click")
        assert collector._stats.transition_count == 2
        assert collector._stats.unique_transitions == 1  # No change

        # Different transition
        collector.record_transition(from_screen_id=2, to_screen_id=3, action_type="scroll_down")
        assert collector._stats.transition_count == 3
        assert collector._stats.unique_transitions == 2
        assert collector._stats.navigation_graph_edges == 2

    def test_record_activity_visit(self):
        """Test recording activity visits."""
        collector = RuntimeStatsCollector(run_id=100)
        visited_activities = set()

        collector.record_activity_visit(activity_name=".MainActivity", visited_activities=visited_activities)
        assert collector._stats.unique_activities_visited == 1
        assert ".MainActivity" in visited_activities

        # Same activity again
        collector.record_activity_visit(activity_name=".MainActivity", visited_activities=visited_activities)
        assert collector._stats.unique_activities_visited == 1  # No change

        # Different activity
        collector.record_activity_visit(activity_name=".LoginActivity", visited_activities=visited_activities)
        assert collector._stats.unique_activities_visited == 2

    def test_record_activity_visit_none(self):
        """Test recording activity visit with None."""
        collector = RuntimeStatsCollector(run_id=100)
        visited_activities = set()

        collector.record_activity_visit(activity_name=None, visited_activities=visited_activities)
        assert collector._stats.unique_activities_visited == 0

    def test_record_unexplored_screen(self):
        """Test recording unexplored screen."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.record_unexplored_screen()
        assert collector._stats.screens_with_unexplored_elements == 1

        collector.record_unexplored_screen()
        assert collector._stats.screens_with_unexplored_elements == 2

    def test_save_success(self):
        """Test successful save to repository."""
        mock_repo = Mock()
        collector = RuntimeStatsCollector(run_id=100, run_stats_repository=mock_repo)

        collector.start_session()
        collector.record_step_start()
        collector.record_step_success(duration_ms=500.0)

        result = collector.save()

        assert result is True
        mock_repo.save_run_stats.assert_called_once()
        call_args = mock_repo.save_run_stats.call_args[0][0]
        assert call_args["run_id"] == 100
        assert call_args["total_steps"] == 1

    def test_save_no_repository(self):
        """Test save when no repository is configured."""
        collector = RuntimeStatsCollector(run_id=100)

        result = collector.save()

        assert result is False

    def test_save_repository_error(self):
        """Test save when repository raises an error."""
        mock_repo = Mock()
        mock_repo.save_run_stats.side_effect = Exception("Database error")
        collector = RuntimeStatsCollector(run_id=100, run_stats_repository=mock_repo)

        result = collector.save()

        assert result is False

    def test_save_auto_ends_session(self):
        """Test that save automatically ends session if not already ended."""
        mock_repo = Mock()
        collector = RuntimeStatsCollector(run_id=100, run_stats_repository=mock_repo)

        collector.start_session()
        assert collector._stats.session_end_time is None

        collector.save()

        assert collector._stats.session_end_time is not None

    def test_get_summary(self):
        """Test getting summary."""
        collector = RuntimeStatsCollector(run_id=100)

        collector.start_session()
        collector.record_step_start()
        collector.record_step_success(duration_ms=500.0)
        collector.record_ai_call(response_time_ms=1000.0, tokens_used=100, success=True)
        collector.record_screen_visit(screen_id=1, navigation_depth=1)
        collector.end_session()

        summary = collector.get_summary()

        assert summary["total_steps"] == 1
        assert summary["successful_steps"] == 1
        assert summary["failed_steps"] == 0
        assert summary["unique_screens"] == 1
        assert summary["total_ai_calls"] == 1
        assert summary["avg_ai_response_time_ms"] == 1000.0
        assert summary["crawl_duration_seconds"] >= 0
        assert "screens_per_minute" in summary

    def test_stats_property(self):
        """Test stats property accessor."""
        collector = RuntimeStatsCollector(run_id=100)

        stats = collector.stats

        assert isinstance(stats, RuntimeStats)
        assert stats is collector._stats

    def test_comprehensive_workflow(self):
        """Test a comprehensive workflow simulating a crawl session."""
        mock_repo = Mock()
        collector = RuntimeStatsCollector(run_id=100, run_stats_repository=mock_repo)

        # Setup
        collector.set_device_info(
            device_id="emulator-5554",
            device_model="Pixel 5",
            android_version="13.0",
            screen_width=1080,
            screen_height=2400,
        )
        collector.set_app_info(app_package="com.example.app", app_version="1.2.3")

        # Start session
        collector.start_session()

        # Simulate crawl
        collector.record_step_start()
        collector.record_step_success(duration_ms=500.0)
        collector.record_screen_visit(screen_id=1, navigation_depth=1)
        collector.record_action(action_type="click", success=True, duration_ms=200.0)
        collector.record_ai_call(response_time_ms=1000.0, tokens_used=100, success=True)
        collector.record_batch(action_count=1, success=True)

        # More steps
        collector.record_step_start()
        collector.record_step_success(duration_ms=600.0)
        collector.record_screen_visit(screen_id=2, navigation_depth=2)
        collector.record_action(action_type="scroll_down", success=True, duration_ms=300.0)
        collector.record_ai_call(response_time_ms=1200.0, tokens_used=150, success=True)
        collector.record_batch(action_count=3, success=True)

        # Record some errors
        collector.record_step_start()
        collector.record_step_failure(duration_ms=400.0, error_message="Timeout")
        collector.record_action(action_type="input", success=False, duration_ms=250.0)
        collector.record_invalid_bbox()

        # End and save
        collector.end_session()
        saved = collector.save()

        # Verify
        assert saved is True
        assert collector._stats.total_steps == 3
        assert collector._stats.successful_steps == 2
        assert collector._stats.failed_steps == 1
        assert collector._stats.unique_screens_visited == 2
        assert collector._stats.total_ai_calls == 2
        assert collector._stats.total_ai_tokens_used == 250
        assert collector._stats.invalid_bbox_count == 1
        assert mock_repo.save_run_stats.called
