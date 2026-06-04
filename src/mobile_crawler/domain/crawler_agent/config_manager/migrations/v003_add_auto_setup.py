"""Migration v3: Add device.auto_setup field."""

from typing import Any

VERSION = 3


def migrate(config: dict[str, Any]) -> dict[str, Any]:
    """Add auto_setup to device config (defaults to True)."""
    device = config.setdefault("device", {})
    device.setdefault("auto_setup", True)
    return config
