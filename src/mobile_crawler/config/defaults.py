"""Default configuration values."""

from typing import Dict, Any

# Default configuration values
# These are used when no other source provides a value
DEFAULTS: Dict[str, Any] = {
    # Appium settings
    'appium_url': 'http://localhost:4723',
    'appium_connection_timeout': 30,
    'appium_implicit_wait': 10,

    # Crawl settings
    'max_crawl_steps': 15,
    'max_crawl_duration_seconds': 600,
    'action_delay_ms': 500,

    # AI settings
    'ai_timeout_seconds': 30,
    'ai_retry_count': 2,

    # Logging
    'log_level': 'INFO',
    'log_to_file': True,
    'log_to_database': True,

    # Screenshot settings
    'screenshot_max_width': 1280,
    'screenshot_format': 'PNG',

    # Session settings
    'session_cleanup_on_start': True,

    # UI settings (for GUI)
    'theme': 'system',
    'window_width': 1200,
    'window_height': 800,

    # Security
    'encrypt_api_keys': True,

    # Screen deduplication settings
    'screen_similarity_threshold': 12,  # Hamming distance threshold for dHash (64-bit)
    'use_perceptual_hashing': True,     # Enable perceptual hashing for screen deduplication

    # Traffic capture settings (PCAPdroid)
    # Enable network traffic capture using PCAPdroid Android app
    'enable_traffic_capture': False,
    # PCAPdroid package name (default: official package from F-Droid)
    'pcapdroid_package': 'com.emanuelef.remote_capture',
    # PCAPdroid activity (auto-constructed as {package}/.activities.CaptureCtrl if None)
    'pcapdroid_activity': None,
    # Optional API key for PCAPdroid (recommended to avoid user consent prompts)
    'pcapdroid_api_key': None,
    # Output directory for PCAP files (resolved to session directory at runtime)
    'traffic_capture_output_dir': None,
    # Default PCAPdroid output directory on device
    'device_pcap_dir': '/sdcard/Download/PCAPdroid',

    # Video recording settings
    # Enable screen recording during crawl sessions (saved to session directory)
    'enable_video_recording': False,

    # MobSF static analysis settings
    # Enable MobSF static security analysis after crawl completion
    'enable_mobsf_analysis': False,
    # MobSF server API URL (must be running and accessible)
    'mobsf_api_url': 'http://localhost:8000',
    # MobSF API key (required for API access)
    'mobsf_api_key': None,
    # Maximum time to wait for scan completion (in seconds)
    'mobsf_scan_timeout': 900,  # 15 minutes (scans can take 5-10+ minutes for complex apps)
    # Interval between scan status polls (in seconds)
    'mobsf_poll_interval': 2,
}