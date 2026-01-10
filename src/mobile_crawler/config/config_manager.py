"""Simple configuration stub for early development."""

from typing import Any


class SimpleConfig:
    """Simple configuration manager."""

    def __init__(self):
        """Initialize with default values."""
        self._defaults = {
            'appium_url': 'http://localhost:4723',
            'appium_connection_timeout': 30,
            'appium_implicit_wait': 10,
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self._defaults.get(key, default)


# Global config instance
_config = SimpleConfig()


def get_config() -> SimpleConfig:
    """Get the global configuration instance.

    Returns:
        Configuration instance
    """
    return _config