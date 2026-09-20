"""Judging whether an accessibility tree is complete enough to skip OmniParser."""

from __future__ import annotations

from typing import Any


def _root_nodes(a11y_tree: Any) -> list[dict[str, Any]]:
    if isinstance(a11y_tree, dict):
        return [a11y_tree]
    if isinstance(a11y_tree, list):
        return [node for node in a11y_tree if isinstance(node, dict)]
    return []


def count_nodes(a11y_tree: Any) -> int:
    """Number of nodes in a Portal tree (a root dict, or a list of roots)."""
    count = 0
    stack = _root_nodes(a11y_tree)
    while stack:
        node = stack.pop()
        count += 1
        stack.extend(child for child in node.get("children", []) if isinstance(child, dict))
    return count
