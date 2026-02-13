from typing import Protocol, List
from .dtos import OCRResult, GroundingOverlay

class OCREngine(Protocol):
    """Protocol for OCR engine implementations."""
    def detect_text(self, image_path: str) -> List[OCRResult]:
        """Detects text in the given image."""
        ...

class GroundingService(Protocol):
    """Protocol for the grounding service."""
    def process(self, screenshot_path: str) -> GroundingOverlay:
        """Processes a screenshot and returns grounding information."""
        ...
