from dataclasses import dataclass
from typing import Protocol


@dataclass
class OCRResult:
    text: str
    box: tuple[int, int, int, int]  # x_min, y_min, x_max, y_max
    confidence: float

@dataclass
class GroundingOverlay:
    marked_image_path: str
    label_map: dict[int, tuple[int, int]]  # ID -> (x, y)

class GroundingService(Protocol):
    """
    Service responsible for visual grounding of UI elements.
    """

    def process(self, image_path: str) -> GroundingOverlay:
        """
        Takes a raw screenshot path, returns a marked screenshot path
        and a mapping of labels to coordinates.
        """
        ...
