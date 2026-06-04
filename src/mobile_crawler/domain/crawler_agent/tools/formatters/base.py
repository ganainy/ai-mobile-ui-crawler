"""Base interface for tree formatters."""

from abc import ABC, abstractmethod
from typing import Any


class TreeFormatter(ABC):
    """Interface for formatting filtered trees."""

    @abstractmethod
    def format(
        self, filtered_tree: dict[str, Any] | None, phone_state: dict[str, Any]
    ) -> tuple[str, str, list[dict[str, Any]], dict[str, Any]]:
        """Format filtered tree to standard output format.

        Args:
            filtered_tree: Filtered accessibility tree (or None)
            phone_state: Raw phone state dictionary

        Returns:
            Tuple of:
            - formatted_text (str): Complete formatted device state for prompts
            - focused_text (str): Text content of focused element (empty if none)
            - a11y_tree (List[Dict]): Flattened/Processed accessibility tree with indices
            - phone_state (Dict): Raw phone state dict
        """
        pass
