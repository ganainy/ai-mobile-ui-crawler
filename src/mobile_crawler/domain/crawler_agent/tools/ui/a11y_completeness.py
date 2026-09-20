"""Judging whether an accessibility tree is complete enough to skip OmniParser.

In boost mode OmniParser (slow, vision-based) only runs when the tree looks
incomplete. ``evaluate`` returns the names of every check that failed; an empty
list means the tree is trusted. The names are logged so the checks can be tuned
from real runs.

Checks:
    no_tree        Portal gave no tree at all.
    few_nodes      Fewer nodes than ``min_nodes``.
    surface_view   A WebView / Flutter / game surface fills much of the screen, so its
                   contents are invisible to accessibility.
    text_only      There is text but nothing interactive.
    few_clickables Some, but fewer than ``min_clickables``, interactive nodes.
    uncovered_area More than ``max_uncovered_ratio`` of the screen is not covered by any
                   meaningful leaf node (text, description or interactive).
"""

from __future__ import annotations

from typing import Any

DEFAULT_OPTIONS: dict[str, Any] = {
    "min_clickables": 3,
    "max_uncovered_ratio": 0.4,
    "surface_classes": ("WebView", "FlutterView", "FlutterSurfaceView", "SurfaceView", "GLSurfaceView", "UnityPlayer"),
    "surface_min_screen_ratio": 0.5,
    "disabled": (),  # check names to skip
}

_GRID_COLUMNS = 24
_GRID_ROWS = 48


def _root_nodes(a11y_tree: Any) -> list[dict[str, Any]]:
    if isinstance(a11y_tree, dict):
        return [a11y_tree]
    if isinstance(a11y_tree, list):
        return [node for node in a11y_tree if isinstance(node, dict)]
    return []


def _walk(a11y_tree: Any):
    stack = _root_nodes(a11y_tree)
    while stack:
        node = stack.pop()
        yield node
        stack.extend(child for child in node.get("children", []) if isinstance(child, dict))


def count_nodes(a11y_tree: Any) -> int:
    """Number of nodes in a Portal tree (a root dict, or a list of roots)."""
    return sum(1 for _ in _walk(a11y_tree))


def _bounds(node: dict[str, Any]) -> tuple[int, int, int, int] | None:
    b = node.get("boundsInScreen")
    if not isinstance(b, dict):
        return None
    left, top, right, bottom = (int(b.get(k, 0) or 0) for k in ("left", "top", "right", "bottom"))
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def _is_interactive(node: dict[str, Any]) -> bool:
    return any(node.get(k) for k in ("isClickable", "isLongClickable", "isCheckable", "isEditable"))


def _has_content(node: dict[str, Any]) -> bool:
    return bool((node.get("text") or "").strip() or (node.get("contentDescription") or "").strip())


def _uncovered_ratio(nodes: list[dict[str, Any]], width: int, height: int) -> float:
    covered = [[False] * _GRID_COLUMNS for _ in range(_GRID_ROWS)]
    for node in nodes:
        if node.get("children") or node.get("isVisibleToUser") is False:
            continue  # only visible leaves count as content
        if not (_is_interactive(node) or _has_content(node)):
            continue
        box = _bounds(node)
        if box is None:
            continue
        left, top, right, bottom = box
        for row in range(_GRID_ROWS):
            cy = (row + 0.5) * height / _GRID_ROWS
            if not top <= cy < bottom:
                continue
            for col in range(_GRID_COLUMNS):
                if left <= (col + 0.5) * width / _GRID_COLUMNS < right:
                    covered[row][col] = True
    return 1 - sum(map(sum, covered)) / (_GRID_COLUMNS * _GRID_ROWS)


def evaluate(
    a11y_tree: Any,
    device_context: dict[str, Any] | None = None,
    *,
    min_nodes: int = 5,
    options: dict[str, Any] | None = None,
) -> list[str]:
    """Return the names of the checks that say *a11y_tree* is incomplete (empty = trust it)."""
    opts = {**DEFAULT_OPTIONS, **(options or {})}
    disabled = set(opts["disabled"])
    nodes = list(_walk(a11y_tree))
    if not nodes:
        return ["no_tree"]

    screen = (device_context or {}).get("screen_bounds", {})
    width, height = int(screen.get("width") or 1080), int(screen.get("height") or 1920)
    failed: list[str] = []

    if len(nodes) < min_nodes:
        failed.append("few_nodes")

    surfaces = tuple(opts["surface_classes"])
    for node in nodes:
        box = _bounds(node)
        if box and any(name in str(node.get("className", "")) for name in surfaces):
            area = (box[2] - box[0]) * (box[3] - box[1])
            if area >= opts["surface_min_screen_ratio"] * width * height:
                failed.append("surface_view")
                break

    interactive = sum(1 for n in nodes if _is_interactive(n) and _bounds(n))
    if interactive == 0:
        if any(_has_content(n) for n in nodes):
            failed.append("text_only")
    elif interactive < opts["min_clickables"]:
        failed.append("few_clickables")

    if _uncovered_ratio(nodes, width, height) > opts["max_uncovered_ratio"]:
        failed.append("uncovered_area")

    return [name for name in failed if name not in disabled]
