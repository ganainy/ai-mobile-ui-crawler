"""
Grounding module for visual interaction mapping.
"""

from .dtos import GroundingOverlay, OCRResult
from .interfaces import GroundingService
from .manager import GroundingManager

__all__ = ["OCRResult", "GroundingOverlay", "GroundingService", "GroundingManager"]
