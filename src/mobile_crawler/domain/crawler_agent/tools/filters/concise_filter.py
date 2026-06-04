"""Concise filtering - all logic self-contained."""

from typing import Any

from .base import TreeFilter


class ConciseFilter(TreeFilter):
    """Concise tree filtering (formerly Droidrun)."""

    def filter(
        self, a11y_tree: dict[str, Any], device_context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Filter using concise logic."""
        screen_bounds = device_context.get("screen_bounds", {})
        filtering_params = device_context.get("filtering_params", {})

        return self._filter_node(a11y_tree, screen_bounds, filtering_params)

    def _filter_node(
        self,
        node: dict[str, Any],
        screen_bounds: dict[str, int],
        filtering_params: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Recursively filter node."""
        min_size = filtering_params.get("min_element_size", 5)
        screen_width = screen_bounds.get("width", 1080)
        screen_height = screen_bounds.get("height", 2400)

        if not self._intersects_screen(node, screen_width, screen_height):
            return None
        if not self._min_size(node, min_size):
            return None

        filtered_children = []
        for child in node.get("children", []):
            filtered_child = self._filter_node(child, screen_bounds, filtering_params)
            if filtered_child:
                filtered_children.append(filtered_child)

        return {**node, "children": filtered_children}

    @staticmethod
    def _intersects_screen(
        node: dict[str, Any], screen_width: int, screen_height: int
    ) -> bool:
        """Check if element intersects screen bounds."""
        bounds = node.get("boundsInScreen", {})
        left = bounds.get("left", 0)
        top = bounds.get("top", 0)
        right = bounds.get("right", 0)
        bottom = bounds.get("bottom", 0)
        return not (
            right <= 0 or bottom <= 0 or left >= screen_width or top >= screen_height
        )

    @staticmethod
    def _min_size(node: dict[str, Any], min_size: int) -> bool:
        """Check if element meets minimum size."""
        bounds = node.get("boundsInScreen", {})
        w = bounds.get("right", 0) - bounds.get("left", 0)
        h = bounds.get("bottom", 0) - bounds.get("top", 0)
        return w > min_size and h > min_size

    def get_name(self) -> str:
        """Return filter name."""
        return "concise"
