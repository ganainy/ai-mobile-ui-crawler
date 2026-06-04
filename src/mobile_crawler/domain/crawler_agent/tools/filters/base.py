"""Base interface for accessibility tree filters."""

from abc import ABC, abstractmethod
from typing import Any


class TreeFilter(ABC):
    """Interface for filtering accessibility trees."""

    @abstractmethod
    def filter(
        self, a11y_tree: dict[str, Any], device_context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Filter tree and return filtered tree with hierarchy preserved."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return filter name."""
        pass
