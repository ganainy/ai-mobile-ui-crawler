"""Default configuration values."""

from typing import Any

# Default configuration values
# These are used when no other source provides a value
DEFAULTS: dict[str, Any] = {
    # Crawl settings
    "max_crawl_steps": 15,
    "max_crawl_duration_seconds": 600,
    "action_delay_ms": 500,
    # AI settings
    "ai_timeout_seconds": 30,
    "ai_retry_count": 2,
    # Logging
    "log_level": "INFO",
    "log_to_file": True,
    "log_to_database": True,
    # Screenshot settings
    "screenshot_max_width": 1280,
    "screenshot_format": "PNG",
    # Session settings
    "session_cleanup_on_start": True,
    # UI settings (for GUI)
    "theme": "system",
    "window_width": 1200,
    "window_height": 800,
    # Security
    "encrypt_api_keys": True,
    # Screen deduplication settings
    "screen_similarity_threshold": 12,  # Hamming distance threshold for dHash (64-bit)
    "use_perceptual_hashing": True,  # Enable perceptual hashing for screen deduplication
    # Traffic capture settings (PCAPdroid)
    # Enable network traffic capture using PCAPdroid Android app
    "enable_traffic_capture": False,
    # PCAPdroid package name (Google Play package used by the intent API)
    "pcapdroid_package": "com.emanuelef.remote_capture",
    # PCAPdroid activity used by the official app API
    "pcapdroid_activity": "com.emanuelef.remote_capture/.activities.CaptureCtrl",
    # Optional API key for PCAPdroid (recommended to avoid user consent prompts)
    "pcapdroid_api_key": None,
    # Request PCAPdroid TLS decryption when capture is enabled
    "pcapdroid_tls_decryption": False,
    # Wait for PCAPdroid to initialize after start
    "pcapdroid_init_wait": 3.0,
    # Wait for PCAPdroid to finalize the file after stop
    "pcapdroid_finalize_wait": 2.0,
    # Best-effort approval of PCAPdroid/API/VPN consent during capture startup
    "pcapdroid_auto_accept_consent": True,
    "pcapdroid_consent_timeout_seconds": 15.0,
    "pcapdroid_consent_poll_interval_seconds": 1.0,
    # Output directory for PCAP files (resolved to session directory at runtime)
    "traffic_capture_output_dir": None,
    # Default PCAPdroid output directory on device
    "device_pcap_dir": "/sdcard/Download/PCAPdroid",
    # Video recording settings
    # Enable screen recording during crawl sessions (saved to session directory)
    "enable_video_recording": False,
    # ADB screenrecord maximum/default is 180 seconds. Keep segments at or below this.
    "video_recording_segment_seconds": 180,
    # Directory on the Android device used for temporary video segments before pull.
    "video_recording_device_dir": "/sdcard/mobile-crawler/videos",
    # Wait after screenrecord stops before pulling the finalized MP4.
    "video_recording_finalize_wait": 1.0,
    # MobSF static analysis settings
    # Enable MobSF static security analysis after crawl completion
    "enable_mobsf_analysis": False,
    # MobSF server API URL (must be running and accessible)
    "mobsf_api_url": "http://localhost:8000",
    # MobSF API key (required for API access)
    "mobsf_api_key": None,
    # Maximum time to wait for scan completion (in seconds)
    "mobsf_scan_timeout": 900,  # 15 minutes (scans can take 5-10+ minutes for complex apps)
    # Interval between scan status polls (in seconds)
    "mobsf_poll_interval": 2,
    # HTTP request timeout for MobSF API calls (in seconds)
    "mobsf_request_timeout": 300,  # 5 minutes for large report downloads
    # Test credentials
    # DroidRun Agent Integration settings
    # Enable DroidRun's advanced AI agent system for multi-step planning
    "use_droidrun_agent": True,
    # Wake/unlock preflight before launching the target app or DroidRun
    "pre_crawl_wake_device": True,
    "pre_crawl_unlock_swipe": True,
    "pre_crawl_wake_timeout_seconds": 5.0,
    # Use reasoning mode for complex planning (vs direct execution)
    "droidrun_reasoning_mode": True,
    # Maximum planning/execution cycles for DroidRun agent
    "droidrun_max_cycles": 5,
    # Agent streaming output (for real-time updates)
    "droidrun_streaming": False,
    # DroidRun agent retry count for failed operations
    "droidrun_retry_count": 2,
    # UI parser strategy: accessibility-first with OmniParser fallback
    "ui_parser_mode": "boost",
    "omniparser_backend": "replicate",
    "omniparser_local_url": "http://localhost:8000",
    "omniparser_box_threshold": 0.05,
    "omniparser_cache_ttl_days": 30,
    "omniparser_a11y_ratio_threshold": 0.5,
    # Adaptive wait profiles for UI synchronization (replaces fixed sleeps)
    "wait_default_timeout_ms": 3000,
    "wait_default_poll_interval_ms": 200,
    "wait_tap_timeout_ms": 2000,
    "wait_tap_poll_interval_ms": 150,
    "wait_click_timeout_ms": 3000,
    "wait_click_poll_interval_ms": 200,
    "wait_scroll_timeout_ms": 1500,
    "wait_scroll_poll_interval_ms": 100,
    "wait_swipe_timeout_ms": 1500,
    "wait_swipe_poll_interval_ms": 100,
    "wait_type_timeout_ms": 2000,
    "wait_type_poll_interval_ms": 200,
    "wait_back_timeout_ms": 3000,
    "wait_back_poll_interval_ms": 200,
    "wait_home_timeout_ms": 3000,
    "wait_home_poll_interval_ms": 200,
    "wait_start_app_timeout_ms": 5000,
    "wait_start_app_poll_interval_ms": 300,
}
