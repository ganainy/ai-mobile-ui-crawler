"""Runtime statistics collector for crawl sessions."""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class RuntimeStats:
    """Comprehensive runtime statistics for a crawl session."""

    # Crawl Progress
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    crawl_duration_seconds: float = 0.0
    avg_step_duration_ms: float = 0.0

    # Screen Discovery
    unique_screens_visited: int = 0
    total_screen_visits: int = 0
    screens_per_minute: float = 0.0
    deepest_navigation_depth: int = 0
    most_visited_screen_id: Optional[int] = None
    most_visited_screen_count: int = 0
    unique_activities_visited: int = 0

    # Action Statistics
    actions_by_type: Dict[str, int] = field(default_factory=dict)
    successful_actions_by_type: Dict[str, int] = field(default_factory=dict)
    failed_actions_by_type: Dict[str, int] = field(default_factory=dict)
    avg_action_duration_ms: float = 0.0
    min_action_duration_ms: Optional[float] = None
    max_action_duration_ms: Optional[float] = None

    # AI Performance
    total_ai_calls: int = 0
    avg_ai_response_time_ms: float = 0.0
    min_ai_response_time_ms: Optional[float] = None
    max_ai_response_time_ms: Optional[float] = None
    ai_timeout_count: int = 0
    ai_error_count: int = 0
    ai_retry_count: int = 0
    invalid_response_count: int = 0
    total_ai_tokens_used: int = 0

    # Multi-Action Batching
    multi_action_batch_count: int = 0
    single_action_count: int = 0
    total_batch_actions: int = 0
    avg_batch_size: float = 0.0
    max_batch_size: int = 0
    batch_success_rate: float = 0.0

    # Error & Recovery
    stuck_detection_count: int = 0
    stuck_recovery_success: int = 0
    app_crash_count: int = 0
    app_relaunch_count: int = 0
    context_loss_count: int = 0
    context_recovery_count: int = 0
    invalid_bbox_count: int = 0

    # Device & Session
    device_id: Optional[str] = None
    device_model: Optional[str] = None
    android_version: Optional[str] = None
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    app_package: Optional[str] = None
    app_version: Optional[str] = None
    session_start_time: Optional[datetime] = None
    session_end_time: Optional[datetime] = None

    # Network & Security
    pcap_file_size_bytes: Optional[int] = None
    pcap_packet_count: Optional[int] = None
    mobsf_security_score: Optional[float] = None
    mobsf_high_issues: int = 0
    mobsf_medium_issues: int = 0
    mobsf_low_issues: int = 0
    video_file_size_bytes: Optional[int] = None
    video_duration_seconds: Optional[float] = None

    # Coverage
    screens_with_unexplored_elements: int = 0
    transition_count: int = 0
    unique_transitions: int = 0
    navigation_graph_edges: int = 0

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary for database insertion.

        Returns:
            Dictionary with all fields ready for run_stats table
        """
        return {
            # Crawl Progress
            "total_steps": self.total_steps,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "crawl_duration_seconds": self.crawl_duration_seconds,
            "avg_step_duration_ms": self.avg_step_duration_ms,

            # Screen Discovery
            "unique_screens_visited": self.unique_screens_visited,
            "total_screen_visits": self.total_screen_visits,
            "deepest_navigation_depth": self.deepest_navigation_depth,
            "most_visited_screen_id": self.most_visited_screen_id,
            "most_visited_screen_count": self.most_visited_screen_count,
            "unique_activities_visited": self.unique_activities_visited,

            # Action Statistics (JSON fields)
            "actions_by_type_json": json.dumps(self.actions_by_type),
            "successful_actions_by_type_json": json.dumps(self.successful_actions_by_type),
            "failed_actions_by_type_json": json.dumps(self.failed_actions_by_type),
            "avg_action_duration_ms": self.avg_action_duration_ms,
            "min_action_duration_ms": self.min_action_duration_ms,
            "max_action_duration_ms": self.max_action_duration_ms,

            # AI Performance
            "total_ai_calls": self.total_ai_calls,
            "avg_ai_response_time_ms": self.avg_ai_response_time_ms,
            "min_ai_response_time_ms": self.min_ai_response_time_ms,
            "max_ai_response_time_ms": self.max_ai_response_time_ms,
            "ai_timeout_count": self.ai_timeout_count,
            "ai_error_count": self.ai_error_count,
            "ai_retry_count": self.ai_retry_count,
            "invalid_response_count": self.invalid_response_count,
            "total_ai_tokens_used": self.total_ai_tokens_used,

            # Multi-Action Batching
            "multi_action_batch_count": self.multi_action_batch_count,
            "single_action_count": self.single_action_count,
            "total_batch_actions": self.total_batch_actions,
            "avg_batch_size": self.avg_batch_size,
            "max_batch_size": self.max_batch_size,

            # Error & Recovery
            "stuck_detection_count": self.stuck_detection_count,
            "stuck_recovery_success": self.stuck_recovery_success,
            "app_crash_count": self.app_crash_count,
            "app_relaunch_count": self.app_relaunch_count,
            "context_loss_count": self.context_loss_count,
            "context_recovery_count": self.context_recovery_count,
            "invalid_bbox_count": self.invalid_bbox_count,

            # Device & Session
            "device_model": self.device_model,
            "android_version": self.android_version,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "app_version": self.app_version,

            # Network & Security
            "pcap_file_size_bytes": self.pcap_file_size_bytes,
            "pcap_packet_count": self.pcap_packet_count,
            "mobsf_security_score": self.mobsf_security_score,
            "mobsf_high_issues": self.mobsf_high_issues,
            "mobsf_medium_issues": self.mobsf_medium_issues,
            "mobsf_low_issues": self.mobsf_low_issues,
            "video_file_size_bytes": self.video_file_size_bytes,
            "video_duration_seconds": self.video_duration_seconds,

            # Coverage
            "transition_count": self.transition_count,
            "unique_transitions": self.unique_transitions,
        }


class RuntimeStatsCollector:
    """Collects and manages runtime statistics during crawl sessions."""

    def __init__(self, run_id: int, run_stats_repository=None):
        """Initialize the stats collector.

        Args:
            run_id: ID of the run to collect stats for
            run_stats_repository: Optional repository for persisting stats
        """
        self._run_id = run_id
        self._run_stats_repository = run_stats_repository
        self._stats = RuntimeStats()
        self._screen_visit_counts: Dict[int, int] = {}
        self._transition_set: set = set()
        self._batch_results: List[bool] = []  # Track batch success/failure

    @property
    def stats(self) -> RuntimeStats:
        """Get the current statistics."""
        return self._stats

    def record_step_start(self) -> None:
        """Record that a new step has started."""
        self._stats.total_steps += 1

    def record_step_success(self, duration_ms: float) -> None:
        """Record a successful step execution.

        Args:
            duration_ms: Time taken to execute the step
        """
        self._stats.successful_steps += 1
        self._update_step_duration(duration_ms)

    def record_step_failure(self, duration_ms: float, error_message: str) -> None:
        """Record a failed step execution.

        Args:
            duration_ms: Time taken before failure
            error_message: Error message
        """
        self._stats.failed_steps += 1
        self._update_step_duration(duration_ms)

    def _update_step_duration(self, duration_ms: float) -> None:
        """Update average step duration.

        Args:
            duration_ms: Duration of the step
        """
        total_steps = self._stats.total_steps
        if total_steps > 0:
            # Recalculate average
            self._stats.avg_step_duration_ms = (
                (self._stats.avg_step_duration_ms * (total_steps - 1) + duration_ms) / total_steps
            )

    def record_screen_visit(self, screen_id: int, navigation_depth: int = 0) -> None:
        """Record a screen visit.

        Args:
            screen_id: ID of the screen visited
            navigation_depth: Current navigation depth from launch
        """
        # Update visit count
        self._screen_visit_counts[screen_id] = self._screen_visit_counts.get(screen_id, 0) + 1
        self._stats.total_screen_visits += 1

        # Track unique screens
        if self._screen_visit_counts[screen_id] == 1:
            self._stats.unique_screens_visited += 1

        # Update most visited screen
        visit_count = self._screen_visit_counts[screen_id]
        if visit_count > self._stats.most_visited_screen_count:
            self._stats.most_visited_screen_id = screen_id
            self._stats.most_visited_screen_count = visit_count

        # Update deepest navigation depth
        if navigation_depth > self._stats.deepest_navigation_depth:
            self._stats.deepest_navigation_depth = navigation_depth

    def record_action(self, action_type: str, success: bool, duration_ms: float) -> None:
        """Record an action execution.

        Args:
            action_type: Type of action (click, input, scroll_down, etc.)
            success: Whether the action succeeded
            duration_ms: Time taken to execute the action
        """
        # Update action counts by type
        self._stats.actions_by_type[action_type] = self._stats.actions_by_type.get(action_type, 0) + 1

        if success:
            self._stats.successful_actions_by_type[action_type] = (
                self._stats.successful_actions_by_type.get(action_type, 0) + 1
            )
        else:
            self._stats.failed_actions_by_type[action_type] = (
                self._stats.failed_actions_by_type.get(action_type, 0) + 1
            )

        # Update action duration stats
        self._stats.avg_action_duration_ms = (
            (self._stats.avg_action_duration_ms * (self._stats.total_ai_calls + self._stats.total_steps - 1) + duration_ms)
            / (self._stats.total_ai_calls + self._stats.total_steps)
        ) if (self._stats.total_ai_calls + self._stats.total_steps) > 0 else duration_ms

        if self._stats.min_action_duration_ms is None or duration_ms < self._stats.min_action_duration_ms:
            self._stats.min_action_duration_ms = duration_ms

        if self._stats.max_action_duration_ms is None or duration_ms > self._stats.max_action_duration_ms:
            self._stats.max_action_duration_ms = duration_ms

    def record_ai_call(self, response_time_ms: float, tokens_used: int = 0, success: bool = True, timeout: bool = False) -> None:
        """Record an AI API call.

        Args:
            response_time_ms: Time taken for AI response
            tokens_used: Number of tokens used
            success: Whether the call was successful
            timeout: Whether the call timed out
        """
        self._stats.total_ai_calls += 1
        self._stats.total_ai_tokens_used += tokens_used

        if timeout:
            self._stats.ai_timeout_count += 1
        elif not success:
            self._stats.ai_error_count += 1

        # Update response time stats
        if success:
            self._stats.avg_ai_response_time_ms = (
                (self._stats.avg_ai_response_time_ms * (self._stats.total_ai_calls - 1) + response_time_ms)
                / self._stats.total_ai_calls
            )

            if self._stats.min_ai_response_time_ms is None or response_time_ms < self._stats.min_ai_response_time_ms:
                self._stats.min_ai_response_time_ms = response_time_ms

            if self._stats.max_ai_response_time_ms is None or response_time_ms > self._stats.max_ai_response_time_ms:
                self._stats.max_ai_response_time_ms = response_time_ms

    def record_ai_retry(self) -> None:
        """Record an AI call retry."""
        self._stats.ai_retry_count += 1

    def record_invalid_response(self) -> None:
        """Record an invalid AI response (JSON parse or schema error)."""
        self._stats.invalid_response_count += 1

    def record_batch(self, action_count: int, success: bool) -> None:
        """Record a batch of actions.

        Args:
            action_count: Number of actions in the batch
            success: Whether the entire batch succeeded
        """
        self._batch_results.append(success)
        self._stats.total_batch_actions += action_count

        if action_count > 1:
            self._stats.multi_action_batch_count += 1
        else:
            self._stats.single_action_count += 1

        # Update max batch size
        if action_count > self._stats.max_batch_size:
            self._stats.max_batch_size = action_count

        # Update average batch size
        total_batches = self._stats.multi_action_batch_count + self._stats.single_action_count
        if total_batches > 0:
            self._stats.avg_batch_size = self._stats.total_batch_actions / total_batches

        # Update batch success rate
        if self._batch_results:
            self._stats.batch_success_rate = sum(self._batch_results) / len(self._batch_results)

    def record_stuck_detection(self) -> None:
        """Record a stuck detection event."""
        self._stats.stuck_detection_count += 1

    def record_stuck_recovery(self, success: bool) -> None:
        """Record a stuck recovery attempt.

        Args:
            success: Whether the recovery was successful
        """
        if success:
            self._stats.stuck_recovery_success += 1

    def record_app_crash(self) -> None:
        """Record an app crash."""
        self._stats.app_crash_count += 1

    def record_app_relaunch(self) -> None:
        """Record an app relaunch."""
        self._stats.app_relaunch_count += 1

    def record_context_loss(self) -> None:
        """Record a context loss event."""
        self._stats.context_loss_count += 1

    def record_context_recovery(self) -> None:
        """Record a successful context recovery."""
        self._stats.context_recovery_count += 1

    def record_invalid_bbox(self) -> None:
        """Record an invalid bounding box."""
        self._stats.invalid_bbox_count += 1

    def set_device_info(self, device_id: str, device_model: str, android_version: str,
                     screen_width: int, screen_height: int) -> None:
        """Set device information.

        Args:
            device_id: Device identifier
            device_model: Device model name
            android_version: Android OS version
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
        """
        self._stats.device_id = device_id
        self._stats.device_model = device_model
        self._stats.android_version = android_version
        self._stats.screen_width = screen_width
        self._stats.screen_height = screen_height

    def set_app_info(self, app_package: str, app_version: Optional[str] = None) -> None:
        """Set application information.

        Args:
            app_package: Target app package name
            app_version: App version (if detectable)
        """
        self._stats.app_package = app_package
        self._stats.app_version = app_version

    def start_session(self) -> None:
        """Mark the start of the crawl session."""
        self._stats.session_start_time = datetime.now()

    def end_session(self) -> None:
        """Mark the end of the crawl session and calculate final stats."""
        self._stats.session_end_time = datetime.now()

        # Calculate total duration
        if self._stats.session_start_time:
            duration = (self._stats.session_end_time - self._stats.session_start_time).total_seconds()
            self._stats.crawl_duration_seconds = duration

            # Calculate screens per minute
            if duration > 0:
                self._stats.screens_per_minute = (self._stats.total_screen_visits / duration) * 60

    def record_pcap_stats(self, file_size_bytes: int, packet_count: Optional[int] = None) -> None:
        """Record PCAP capture statistics.

        Args:
            file_size_bytes: Size of the PCAP file
            packet_count: Number of captured packets (if parseable)
        """
        self._stats.pcap_file_size_bytes = file_size_bytes
        self._stats.pcap_packet_count = packet_count

    def record_mobsf_results(self, security_score: float, high_issues: int,
                          medium_issues: int, low_issues: int) -> None:
        """Record MobSF static analysis results.

        Args:
            security_score: Overall security score
            high_issues: Number of high-severity issues
            medium_issues: Number of medium-severity issues
            low_issues: Number of low-severity issues
        """
        self._stats.mobsf_security_score = security_score
        self._stats.mobsf_high_issues = high_issues
        self._stats.mobsf_medium_issues = medium_issues
        self._stats.mobsf_low_issues = low_issues

    def record_video_stats(self, file_size_bytes: int, duration_seconds: float) -> None:
        """Record video recording statistics.

        Args:
            file_size_bytes: Size of the video file
            duration_seconds: Duration of the recording
        """
        self._stats.video_file_size_bytes = file_size_bytes
        self._stats.video_duration_seconds = duration_seconds

    def record_transition(self, from_screen_id: int, to_screen_id: int, action_type: str) -> None:
        """Record a screen-to-screen transition.

        Args:
            from_screen_id: Source screen ID
            to_screen_id: Destination screen ID
            action_type: Action that caused the transition
        """
        self._stats.transition_count += 1

        # Track unique transitions
        transition_key = (from_screen_id, to_screen_id, action_type)
        if transition_key not in self._transition_set:
            self._transition_set.add(transition_key)
            self._stats.unique_transitions += 1

        # Update navigation graph edges count
        edge_key = (from_screen_id, to_screen_id)
        if edge_key not in self._transition_set:
            self._transition_set.add(edge_key)
            self._stats.navigation_graph_edges += 1

    def record_activity_visit(self, activity_name: str, visited_activities: set) -> None:
        """Record a visit to an Android activity.

        Args:
            activity_name: Name of the activity
            visited_activities: Set of already visited activities
        """
        if activity_name and activity_name not in visited_activities:
            visited_activities.add(activity_name)
            self._stats.unique_activities_visited += 1

    def record_unexplored_screen(self) -> None:
        """Record a screen with unexplored elements."""
        self._stats.screens_with_unexplored_elements += 1

    def save(self) -> bool:
        """Persist statistics to database.

        Returns:
            True if save was successful, False otherwise
        """
        if self._run_stats_repository is None:
            logger.warning("No run_stats repository configured; stats not saved")
            return False

        try:
            # Ensure session is ended before saving
            if self._stats.session_end_time is None:
                self.end_session()

            # Convert to DB dict
            stats_dict = self._stats.to_db_dict()
            stats_dict["run_id"] = self._run_id

            # Save to repository
            self._run_stats_repository.save_run_stats(stats_dict)

            logger.info(f"Saved runtime stats for run {self._run_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save runtime stats for run {self._run_id}: {e}")
            return False

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of key statistics.

        Returns:
            Dictionary with key statistics for reporting
        """
        return {
            "total_steps": self._stats.total_steps,
            "successful_steps": self._stats.successful_steps,
            "failed_steps": self._stats.failed_steps,
            "unique_screens": self._stats.unique_screens_visited,
            "total_ai_calls": self._stats.total_ai_calls,
            "avg_ai_response_time_ms": round(self._stats.avg_ai_response_time_ms, 2) if self._stats.avg_ai_response_time_ms else 0,
            "crawl_duration_seconds": round(self._stats.crawl_duration_seconds, 2),
            "screens_per_minute": round(self._stats.screens_per_minute, 2) if self._stats.screens_per_minute else 0,
        }
