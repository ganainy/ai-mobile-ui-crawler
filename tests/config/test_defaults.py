"""Tests for default config values."""

import pytest

from mobile_crawler.config.defaults import DEFAULTS


class TestDefaultConfigValues:
    """Tests for default configuration values."""

    def test_default_values_present(self):
        """Test that all expected default values are present."""
        expected_keys = [
            "max_crawl_steps",
            "max_crawl_duration_seconds",
            "action_delay_ms",
            "ai_timeout_seconds",
            "ai_retry_count",
            "log_level",
            "log_to_file",
            "log_to_database",
            "screenshot_max_width",
            "screenshot_format",
            "session_cleanup_on_start",
            "theme",
            "window_width",
            "window_height",
            "encrypt_api_keys",
            "screen_similarity_threshold",
            "use_perceptual_hashing",
            "enable_traffic_capture",
            "pcapdroid_package",
            "pcapdroid_activity",
            "pcapdroid_api_key",
            "traffic_capture_output_dir",
            "device_pcap_dir",
            "enable_video_recording",
            "enable_mobsf_analysis",
            "mobsf_api_url",
            "mobsf_api_key",
            "mobsf_scan_timeout",
            "mobsf_poll_interval",
            "mobsf_request_timeout",
            "use_droidrun_agent",
            "droidrun_reasoning_mode",
            "droidrun_max_cycles",
            "droidrun_streaming",
            "droidrun_retry_count",
            "droidrun_telemetry_enabled",
            "ui_parser_mode",
            "omniparser_backend",
            "omniparser_local_url",
            "omniparser_box_threshold",
            "omniparser_cache_ttl_days",
            "omniparser_a11y_ratio_threshold",
            "wait_default_timeout_ms",
            "wait_default_poll_interval_ms",
        ]
        for key in expected_keys:
            assert key in DEFAULTS, f"Missing default key: {key}"

    def test_numeric_intervals_positive(self):
        """Test that interval defaults are positive numbers."""
        interval_keys = [
            "max_crawl_steps",
            "max_crawl_duration_seconds",
            "action_delay_ms",
            "ai_timeout_seconds",
            "ai_retry_count",
            "screenshot_max_width",
            "window_width",
            "window_height",
            "screen_similarity_threshold",
            "mobsf_scan_timeout",
            "mobsf_poll_interval",
            "mobsf_request_timeout",
            "droidrun_max_cycles",
            "droidrun_retry_count",
            "omniparser_cache_ttl_days",
            "wait_default_timeout_ms",
            "wait_default_poll_interval_ms",
        ]
        for key in interval_keys:
            value = DEFAULTS[key]
            assert isinstance(value, (int, float)), f"{key} should be numeric"
            assert value > 0, f"{key} should be positive, got {value}"

    def test_paths_are_strings_or_none(self):
        """Test that path defaults are strings or None."""
        path_keys = [
            "log_level",
            "screenshot_format",
            "theme",
            "pcapdroid_package",
            "device_pcap_dir",
            "mobsf_api_url",
            "ui_parser_mode",
            "omniparser_backend",
            "omniparser_local_url",
        ]
        for key in path_keys:
            value = DEFAULTS[key]
            assert isinstance(value, str), f"{key} should be a string, got {type(value)}"
            assert value != "", f"{key} should not be empty"

    def test_boolean_defaults(self):
        """Test that boolean defaults are proper booleans."""
        bool_keys = [
            "log_to_file",
            "log_to_database",
            "session_cleanup_on_start",
            "encrypt_api_keys",
            "use_perceptual_hashing",
            "enable_traffic_capture",
            "enable_video_recording",
            "enable_mobsf_analysis",
            "use_droidrun_agent",
            "droidrun_reasoning_mode",
            "droidrun_streaming",
            "droidrun_telemetry_enabled",
        ]
        for key in bool_keys:
            value = DEFAULTS[key]
            assert isinstance(value, bool), f"{key} should be a bool, got {type(value)}"

    def test_none_allowed_defaults(self):
        """Test that defaults allowing None are correctly None."""
        none_keys = [
            "pcapdroid_activity",
            "pcapdroid_api_key",
            "traffic_capture_output_dir",
            "mobsf_api_key",
        ]
        for key in none_keys:
            assert DEFAULTS[key] is None, f"{key} should be None by default"

    def test_no_none_for_required_values(self):
        """Test that no required default is None."""
        required_keys = [
            "max_crawl_steps",
            "max_crawl_duration_seconds",
            "action_delay_ms",
            "ai_timeout_seconds",
            "ai_retry_count",
            "log_level",
            "screenshot_max_width",
            "screenshot_format",
            "theme",
            "window_width",
            "window_height",
            "use_droidrun_agent",
            "droidrun_reasoning_mode",
        ]
        for key in required_keys:
            assert DEFAULTS[key] is not None, f"Required key {key} should not be None"

    def test_wait_config_values(self):
        """Test that wait configuration values are positive."""
        wait_keys = [k for k in DEFAULTS.keys() if k.startswith("wait_")]
        assert len(wait_keys) > 0, "Should have wait configuration keys"
        for key in wait_keys:
            value = DEFAULTS[key]
            assert isinstance(value, int), f"{key} should be an integer"
            assert value > 0, f"{key} should be positive"

    def test_mobsf_timeout_reasonable(self):
        """Test that MobSF timeout is reasonable (minutes scale)."""
        assert DEFAULTS["mobsf_scan_timeout"] >= 60  # At least 1 minute
        assert DEFAULTS["mobsf_request_timeout"] >= 60  # At least 1 minute

    def test_droidrun_config_sensible(self):
        """Test DroidRun config values make sense."""
        assert DEFAULTS["droidrun_max_cycles"] >= 1
        assert DEFAULTS["droidrun_retry_count"] >= 0
        assert DEFAULTS["omniparser_box_threshold"] > 0
        assert DEFAULTS["omniparser_box_threshold"] < 1
        assert DEFAULTS["omniparser_cache_ttl_days"] >= 1

    def test_screenshot_max_width_reasonable(self):
        """Test screenshot max width is a reasonable value."""
        assert DEFAULTS["screenshot_max_width"] >= 320
        assert DEFAULTS["screenshot_max_width"] <= 3840

    def test_window_dimensions_reasonable(self):
        """Test window dimensions are reasonable."""
        assert DEFAULTS["window_width"] >= 800
        assert DEFAULTS["window_height"] >= 600
