"""Configuration management."""

from .config_manager import get_config
from .paths import get_app_data_dir

__all__ = ["get_app_data_dir", "get_config"]
