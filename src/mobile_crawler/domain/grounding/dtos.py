from dataclasses import dataclass


@dataclass(frozen=True)
class OCRResult:
    """Represents a single text element detected on the screen."""
    text: str
    box: tuple[int, int, int, int]  # (x_min, y_min, x_max, y_max)
    confidence: float
    center: tuple[int, int]  # ((x1+x2)//2, (y1+y2)//2)

@dataclass(frozen=True)
class GroundingOverlay:
    """Represents the result of the grounding process."""
    marked_image_path: str
    label_map: dict[int, tuple[int, int]]  # Label_ID -> (x, y) center coordinates
    ocr_elements: list[dict] # List of detected elements for the AI prompt
    original_dimensions: tuple[int, int]
