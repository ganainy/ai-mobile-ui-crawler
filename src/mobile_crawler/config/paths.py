"""Configuration utilities."""

import platform
from pathlib import Path


def get_app_data_dir() -> Path:
    """Get platform-specific application data directory for mobile-crawler.

    Returns:
        Path to app data directory where databases and config files are stored.
    """
    system = platform.system()

    if system == "Windows":
        # %APPDATA%/mobile-crawler
        appdata = Path.home() / "AppData" / "Roaming"
        return appdata / "mobile-crawler"
    elif system == "Darwin":  # macOS
        # ~/Library/Application Support/mobile-crawler
        return Path.home() / "Library" / "Application Support" / "mobile-crawler"
    else:  # Linux and others
        # ~/.local/share/mobile-crawler
        return Path.home() / ".local" / "share" / "mobile-crawler"
