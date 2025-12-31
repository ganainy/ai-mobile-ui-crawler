"""
Image preprocessing service for the Appium Traverser.

Provides early-stage image resizing and optimization to reduce memory usage,
OCR processing time, and AI token consumption.
"""

import io
import logging
from typing import Optional, Tuple

from PIL import Image, ImageFilter

from config.numeric_constants import (
    IMAGE_MAX_WIDTH_DEFAULT,
    IMAGE_DEFAULT_QUALITY,
    IMAGE_DEFAULT_FORMAT,
    IMAGE_BG_COLOR,
    IMAGE_SHARPEN_RADIUS,
    IMAGE_SHARPEN_PERCENT,
    IMAGE_SHARPEN_THRESHOLD,
)

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Singleton service for early-stage image preprocessing.
    
    Applies resize, format conversion, and sharpening immediately after capture
    to reduce memory footprint and speed up downstream processing (OCR, AI).
    """
    
    _instance: Optional['ImagePreprocessor'] = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config=None):
        if self._initialized:
            return
        self._config = config
        self._initialized = True
    
    def set_config(self, config):
        """Update the config reference."""
        self._config = config
    
    def _get_max_width(self) -> int:
        """Get max width from config or use default."""
        if self._config:
            return self._config.get('IMAGE_MAX_WIDTH', None) or IMAGE_MAX_WIDTH_DEFAULT
        return IMAGE_MAX_WIDTH_DEFAULT
    
    def _get_quality(self) -> int:
        """Get image quality from config or use default."""
        if self._config:
            return self._config.get('IMAGE_QUALITY', None) or IMAGE_DEFAULT_QUALITY
        return IMAGE_DEFAULT_QUALITY
    
    def _get_format(self) -> str:
        """Get image format from config or use default."""
        if self._config:
            return self._config.get('IMAGE_FORMAT', None) or IMAGE_DEFAULT_FORMAT
        return IMAGE_DEFAULT_FORMAT
    
    def preprocess_screenshot(
        self,
        screenshot_bytes: bytes,
        apply_sharpening: bool = True
    ) -> Tuple[bytes, int, int]:
        """
        Preprocess screenshot bytes immediately after capture.
        
        Args:
            screenshot_bytes: Raw screenshot bytes from Appium
            apply_sharpening: Whether to apply sharpening filter
            
        Returns:
            Tuple of (processed_bytes, width, height)
        """
        if not screenshot_bytes:
            return screenshot_bytes, 0, 0
        
        try:
            # Open image from bytes
            img = Image.open(io.BytesIO(screenshot_bytes))
            original_size = len(screenshot_bytes)
            original_width, original_height = img.size
            
            # Get preprocessing settings
            max_width = self._get_max_width()
            quality = self._get_quality()
            image_format = self._get_format().upper()
            
            # Resize if necessary (maintain aspect ratio)
            was_resized = False
            if img.width > max_width:
                scale = max_width / img.width
                new_height = int(img.height * scale)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                was_resized = True
            
            # Convert to RGB if necessary (for JPEG compatibility)
            if img.mode in ('RGBA', 'LA', 'P'):
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, IMAGE_BG_COLOR)
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else:
                    img = img.convert('RGB')
            
            # Apply sharpening to preserve text clarity
            if apply_sharpening:
                img = img.filter(
                    ImageFilter.UnsharpMask(
                        radius=IMAGE_SHARPEN_RADIUS,
                        percent=IMAGE_SHARPEN_PERCENT,
                        threshold=IMAGE_SHARPEN_THRESHOLD
                    )
                )
            
            # Encode to bytes with optimal settings
            output_buffer = io.BytesIO()
            if image_format == 'JPEG':
                img.save(
                    output_buffer,
                    format='JPEG',
                    quality=quality,
                    optimize=True,
                    progressive=True,
                    subsampling='4:2:0'
                )
            elif image_format == 'WEBP':
                img.save(
                    output_buffer,
                    format='WEBP',
                    quality=quality,
                    optimize=True
                )
            else:  # PNG or others
                img.save(output_buffer, format=image_format, optimize=True)
            
            processed_bytes = output_buffer.getvalue()
            new_size = len(processed_bytes)
            
            # Log compression stats
            if was_resized or new_size < original_size:
                compression_ratio = original_size / new_size if new_size > 0 else 1
                logger.debug(
                    f"Image preprocessed: {original_width}x{original_height} -> "
                    f"{img.width}x{img.height}, {original_size} -> {new_size} bytes "
                    f"({compression_ratio:.1f}x compression)"
                )
            
            return processed_bytes, img.width, img.height
            
        except Exception as e:
            logger.error(f"Error preprocessing screenshot: {e}", exc_info=True)
            # Return original on error
            return screenshot_bytes, 0, 0
    
    def preprocess_for_ocr(
        self,
        screenshot_bytes: bytes
    ) -> bytes:
        """
        Preprocess screenshot for OCR specifically.
        
        Uses slightly different settings optimized for text detection.
        
        Args:
            screenshot_bytes: Raw or already-preprocessed screenshot bytes
            
        Returns:
            Processed bytes optimized for OCR
        """
        # For OCR, we use the same preprocessing but ensure sharpening is applied
        processed_bytes, _, _ = self.preprocess_screenshot(
            screenshot_bytes,
            apply_sharpening=True
        )
        return processed_bytes
    
    def get_pil_image(self, screenshot_bytes: bytes) -> Optional[Image.Image]:
        """
        Get a PIL Image from preprocessed bytes.
        
        Useful for passing to AI providers that need PIL Image objects.
        
        Args:
            screenshot_bytes: Preprocessed screenshot bytes
            
        Returns:
            PIL Image object or None on error
        """
        if not screenshot_bytes:
            return None
        
        try:
            return Image.open(io.BytesIO(screenshot_bytes))
        except Exception as e:
            logger.error(f"Error opening image from bytes: {e}")
            return None
    
    def get_pil_image_for_ai(
        self,
        screenshot_bytes: bytes,
        max_width: Optional[int] = None
    ) -> Optional[Image.Image]:
        """
        Get a PIL Image prepared for AI model consumption.
        
        Handles RGB conversion and fallback resize if needed.
        Screenshots should already be preprocessed, but this provides a safety net.
        
        Args:
            screenshot_bytes: Screenshot bytes (should be preprocessed)
            max_width: Optional max width override for provider-specific limits
            
        Returns:
            PIL Image ready for AI model encoding, or None on error
        """
        if not screenshot_bytes:
            return None
        
        try:
            img = Image.open(io.BytesIO(screenshot_bytes))
            
            # Use provided max_width or get from config
            target_width = max_width or self._get_max_width()
            
            # Fallback resize if image is somehow still too large
            if img.width > target_width:
                scale = target_width / img.width
                new_height = int(img.height * scale)
                img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                logger.debug(f"Fallback resize applied: {img.width}x{img.height}")
            
            # Convert to RGB for consistent AI model handling
            if img.mode in ('RGBA', 'LA', 'P'):
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, IMAGE_BG_COLOR)
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else:
                    img = img.convert('RGB')
            
            return img
            
        except Exception as e:
            logger.error(f"Error preparing image for AI: {e}", exc_info=True)
            return None


# Module-level singleton instance
_preprocessor: Optional[ImagePreprocessor] = None


def get_preprocessor(config=None) -> ImagePreprocessor:
    """Get the singleton ImagePreprocessor instance."""
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = ImagePreprocessor(config)
    elif config is not None:
        _preprocessor.set_config(config)
    return _preprocessor
