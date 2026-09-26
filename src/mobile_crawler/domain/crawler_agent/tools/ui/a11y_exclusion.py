"""Drop accessibility nodes that sit inside the Status Bar / Bottom Bar Exclusion."""

from typing import Any


def exclude_bars(a11y_tree: Any, screen_height: int, top_px: int, bottom_px: int) -> Any:
    """Remove nodes lying entirely inside the top or bottom exclusion strip.

    Portal reports the whole screen in absolute device pixels, while the
    screenshot already has these strips cropped (ADR-0002), so the tree is
    trimmed to match. Nodes that merely overlap a strip (containers, the
    root) stay. A dropped node's surviving children move up to its parent.
    Root nodes are never dropped. Nodes without bounds are kept.
    """
    top_px = max(0, top_px)
    bottom_px = max(0, bottom_px)
    if top_px + bottom_px <= 0 or not a11y_tree:
        return a11y_tree
    lower_edge = screen_height - bottom_px

    def in_strip(node: dict[str, Any]) -> bool:
        b = node.get("boundsInScreen")
        if not isinstance(b, dict):
            return False
        top, bottom = b.get("top"), b.get("bottom")
        if top is None or bottom is None:
            return False
        return (top_px > 0 and bottom <= top_px) or (bottom_px > 0 and top >= lower_edge)

    def prune_children(node: dict[str, Any]) -> list[dict[str, Any]]:
        kept: list[dict[str, Any]] = []
        for child in node.get("children") or []:
            if not isinstance(child, dict):
                continue
            pruned = prune_children(child)
            if in_strip(child):
                kept.extend(pruned)  # drop the node, keep whatever survives below it
            else:
                kept.append({**child, "children": pruned})
        return kept

    def prune_root(root: Any) -> Any:
        if not isinstance(root, dict):
            return root
        return {**root, "children": prune_children(root)}

    if isinstance(a11y_tree, list):
        return [prune_root(root) for root in a11y_tree]
    return prune_root(a11y_tree)
