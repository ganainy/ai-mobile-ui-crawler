"""
Grounding module for visual interaction mapping.
"""

from .dtos import OCRResult, GroundingOverlay
from .interfaces import GroundingService
from .manager import GroundingManager

__all__ = ["OCRResult", "GroundingOverlay", "GroundingService", "GroundingManager"]
