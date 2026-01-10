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
}