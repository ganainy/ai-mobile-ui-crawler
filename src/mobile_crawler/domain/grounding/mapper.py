
from .dtos import OCRResult


class LabelMapper:
    """Assigns sequential numeric labels to OCR results and maintains a mapping."""

    def __init__(self):
        self._label_map: dict[int, tuple[int, int]] = {}

    def assign_labels(self, results: list[OCRResult]) -> dict[int, tuple[int, int]]:
        """
        Assigns IDs starting from 1 to each OCRResult and maps them to their centers.
        Clear previous map before assigning.
        """
        self.clear()
        for i, res in enumerate(results, start=1):
            self._label_map[i] = res.center
        return self._label_map

    def get_map(self) -> dict[int, tuple[int, int]]:
        """Returns the current mapping of Label ID -> (x, y)."""
        return self._label_map.copy()

    def clear(self) -> None:
        """Clears the internal mapping."""
        self._label_map = {}
