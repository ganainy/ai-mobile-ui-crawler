"""Migration v5: Remove legacy external agent example configs."""

from typing import Any

VERSION = 5


def migrate(config: dict[str, Any]) -> dict[str, Any]:
    """Remove legacy mai_ui and autoglm example entries from external_agents."""
    external_agents = config.get("external_agents", {})
    if isinstance(external_agents, dict):
        external_agents.pop("mai_ui", None)
        external_agents.pop("autoglm", None)

    return config
