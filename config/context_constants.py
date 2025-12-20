"""
Context source constants for AI prompt building.

These constants define the available context sources that can be included
in AI prompts for the crawler.
"""


class ContextSource:
    """Constants for context source types used in CONTEXT_SOURCE configuration."""
    
    XML = "xml"      # Include XML hierarchy in AI context
    OCR = "ocr"      # Include OCR-detected text elements in AI context
    IMAGE = "image"  # Include screenshots in AI context (for multimodal models)
    
    @classmethod
    def all(cls) -> list:
        """Return all available context source options."""
        return [cls.XML, cls.OCR, cls.IMAGE]
    
    @classmethod
    def default(cls) -> list:
        """Return the default context sources."""
        return [cls.XML, cls.IMAGE]
