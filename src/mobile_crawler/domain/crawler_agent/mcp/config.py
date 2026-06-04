"""MCP configuration models."""

from dataclasses import dataclass, field


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""

    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    prefix: str | None = None
    enabled: bool = True
    include_tools: list[str] | None = None
    exclude_tools: list[str] = field(default_factory=list)


@dataclass
class MCPConfig:
    """MCP client configuration."""

    enabled: bool = False
    servers: dict[str, MCPServerConfig] = field(default_factory=dict)
