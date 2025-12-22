"""
Context source constants for AI prompt building.

These constants define the available context sources that can be included
in AI prompts for the crawler.
"""


class ContextSource:
    """Constants for context source types used in CONTEXT_SOURCE configuration.
    
    HYBRID is always enabled (XML + OCR combined).
    IMAGE is optional for vision-capable models.
    """
    
    HYBRID = "hybrid"  # XML + OCR combined (always enabled)
    IMAGE = "image"    # Optional: Screenshots for vision models
    
    @classmethod
    def all(cls) -> list:
        """Return all available context source options."""
        return [cls.HYBRID, cls.IMAGE]
    
    @classmethod
    def default(cls) -> list:
        """Return the default context sources (HYBRID is always on)."""
        return [cls.HYBRID]
