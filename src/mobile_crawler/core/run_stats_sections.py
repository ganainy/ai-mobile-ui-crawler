"""Qt-free layout and formatting of a persisted run_stats record.

Shared by the GUI's Run Statistics dialog and the `stats` CLI command so both
show the same sections, labels and value formatting.
"""

from typing import Any

from mobile_crawler.core.runtime_stats_collector import RuntimeStats

# (section title, list of (display label, RuntimeStats attribute))
RUN_STATS_SECTIONS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Crawl Progress",
        [
            ("Total Steps", "total_steps"),
            ("Successful Steps", "successful_steps"),
            ("Failed Steps", "failed_steps"),
            ("Duration (s)", "crawl_duration_seconds"),
            ("Avg Step (ms)", "avg_step_duration_ms"),
        ],
    ),
    (
        "Screen Discovery",
        [
            ("Unique Screens", "unique_screens_visited"),
            ("Total Visits", "total_screen_visits"),
            ("Deepest Depth", "deepest_navigation_depth"),
            ("Unique Activities", "unique_activities_visited"),
        ],
    ),
    (
        "Action Statistics",
        [
            ("Actions By Type", "actions_by_type"),
            ("Successful By Type", "successful_actions_by_type"),
            ("Failed By Type", "failed_actions_by_type"),
            ("Avg Duration (ms)", "avg_action_duration_ms"),
            ("Min Duration (ms)", "min_action_duration_ms"),
            ("Max Duration (ms)", "max_action_duration_ms"),
        ],
    ),
    (
        "AI Performance",
        [
            ("Total AI Calls", "total_ai_calls"),
            ("Avg Response (ms)", "avg_ai_response_time_ms"),
            ("Min Response (ms)", "min_ai_response_time_ms"),
            ("Max Response (ms)", "max_ai_response_time_ms"),
            ("Timeouts", "ai_timeout_count"),
            ("Errors", "ai_error_count"),
            ("Retries", "ai_retry_count"),
            ("Invalid Responses", "invalid_response_count"),
            ("Total Tokens", "total_ai_tokens_used"),
            ("Vision Calls", "vision_call_count"),
            ("Non-Vision Calls", "non_vision_call_count"),
            ("AI Success By Type", "ai_success_by_type"),
            ("AI Total By Type", "ai_total_by_type"),
        ],
    ),
    (
        "Batching",
        [
            ("Multi-Action Batches", "multi_action_batch_count"),
            ("Single Actions", "single_action_count"),
            ("Total Batch Actions", "total_batch_actions"),
            ("Avg Batch Size", "avg_batch_size"),
            ("Max Batch Size", "max_batch_size"),
        ],
    ),
    (
        "Error & Recovery",
        [
            ("Stuck Detections", "stuck_detection_count"),
            ("Stuck Recoveries", "stuck_recovery_success"),
            ("App Crashes", "app_crash_count"),
            ("App Relaunches", "app_relaunch_count"),
            ("Context Losses", "context_loss_count"),
            ("Context Recoveries", "context_recovery_count"),
            ("Avg Recovery (ms)", "avg_recovery_time_ms"),
        ],
    ),
    (
        "Device & App",
        [
            ("Device", "device_model"),
            ("Android Version", "android_version"),
            ("App Package", "app_package"),
            ("App Version", "app_version"),
        ],
    ),
    (
        "Network & Security",
        [
            ("PCAP Size (bytes)", "pcap_file_size_bytes"),
            ("PCAP Packets", "pcap_packet_count"),
            ("MobSF Score", "mobsf_security_score"),
            ("MobSF High", "mobsf_high_issues"),
            ("MobSF Medium", "mobsf_medium_issues"),
            ("MobSF Low", "mobsf_low_issues"),
        ],
    ),
    (
        "Coverage",
        [
            ("Transitions", "transition_count"),
            ("Unique Transitions", "unique_transitions"),
        ],
    ),
]


def format_stat_value(value: Any, missing: str = "—") -> str:
    """Format a stat value for display; `missing` stands in for None or an empty dict."""
    if value is None:
        return missing
    if isinstance(value, dict):
        if not value:
            return missing
        return ", ".join(f"{k}: {v}" for k, v in value.items())
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def persisted_stats_dict(stats: RuntimeStats) -> dict[str, Any]:
    """The fields stored in run_stats, with JSON columns decoded back to dicts.

    Keys are RuntimeStats attribute names; live-only fields (never persisted)
    are left out so they don't show up as misleading zeros.
    """
    return {
        key.removesuffix("_json"): getattr(stats, key.removesuffix("_json"))
        for key in stats.to_db_dict()
    }
