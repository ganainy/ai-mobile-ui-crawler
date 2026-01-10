"""Configuration management."""

from .paths import get_app_data_dir
from .config_manager import get_config

__all__ = ["get_app_data_dir", "get_config"]
