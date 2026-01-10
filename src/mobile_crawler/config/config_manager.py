"""Configuration manager with precedence: SQLite → environment variables → module defaults."""

import os
from typing import Any, Optional

from .defaults import DEFAULTS
from ..infrastructure.user_config_store import UserConfigStore


class ConfigManager:
    """Configuration manager with precedence order.

    Precedence (highest to lowest):
    1. SQLite database (user_config.db)
    2. Environment variables (CRAWLER_ prefix)
    3. Module defaults
    """

    def __init__(self, user_config_store: Optional[UserConfigStore] = None):
        """Initialize configuration manager.

        Args:
            user_config_store: User config store instance. If None, creates default.
        """
        if user_config_store is None:
            user_config_store = UserConfigStore()
        self.user_config_store = user_config_store

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with precedence.

        Args:
            key: Configuration key
            default: Default value if key not found in any source

        Returns:
            Configuration value
        """
        # 1. Check SQLite database
        try:
            db_value = self.user_config_store.get_setting(key)
            if db_value is not None:
                return db_value
        except Exception:
            # If DB access fails, continue to next source
            pass

        # 2. Check environment variables
        env_key = f"CRAWLER_{key.upper()}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            # Try to convert to appropriate type
            return self._convert_env_value(env_value)

        # 3. Check module defaults
        if key in DEFAULTS:
            return DEFAULTS[key]

        # 4. Return provided default
        return default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value in database.

        Args:
            key: Configuration key
            value: Value to set
        """
        self.user_config_store.set_setting(key, value)

    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type.

        Args:
            value: String value from environment

        Returns:
            Converted value
        """
        # Try boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'

        # Try int
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value


# Global config instance
_config = ConfigManager()


def get_config() -> ConfigManager:
    """Get the global configuration instance.

    Returns:
        Configuration manager instance
    """
    return _config