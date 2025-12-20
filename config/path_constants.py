"""
Path and directory structure constants.

All directory names and file patterns can be overridden via environment variables
with sensible defaults. This provides flexibility for different deployment scenarios.
"""


from typing import Optional


class PathConstants:
    """Centralized path configuration with environment variable support."""
    
    # Directory names
    SESSIONS_DIR = "sessions"
    DATABASE_DIR = "database"
    SCREENSHOTS_DIR = "screenshots"
    REPORTS_DIR = "reports"
    ANNOTATED_SCREENSHOTS_DIR = "annotated_screenshots"
    LOG_DIR = "logs"
    CACHE_DIR = "cache"
    EXTRACTED_APK_DIR = "extracted_apk"
    MOBSF_SCAN_DIR = "mobsf_scan_results"
    VIDEO_RECORDING_DIR = "video"
    
    # File patterns
    DB_FILE_SUFFIX = "_crawl_data.db"
    APP_INFO_FILE_PATTERN = "device_{device_id}_app_info.json"
    LOG_FILE_NAME = "full.log"
    
    # Cache file names
    GEMINI_MODELS_CACHE = "gemini_models.json"
    OLLAMA_MODELS_CACHE = "ollama_models.json"
    OPENROUTER_MODELS_CACHE = "openrouter_models.json"
    
    @classmethod
    def get_db_filename(cls, package: str, suffix: Optional[str] = None) -> str:
        """Generate database filename for a package."""
        return f"{package}{suffix or cls.DB_FILE_SUFFIX}"
    
    @classmethod
    def get_app_info_filename(cls, device_id: str) -> str:
        """Generate app info filename for a device."""
        return cls.APP_INFO_FILE_PATTERN.format(device_id=device_id)
    
    @classmethod
    def get_cache_file_path(cls, cache_dir: str, cache_filename: str) -> str:
        """Get full path to a cache file."""
        import os
        return os.path.join(cache_dir, cls.CACHE_DIR, cache_filename)

