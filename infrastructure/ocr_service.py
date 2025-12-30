"""
OCR Service module using EasyOCR.

Provides functionality to extract text and bounding boxes from images (bytes).
"""
import logging
import io
import time
from typing import List, Dict, Any, Optional, Union

try:
    import easyocr
    import numpy as np
    from PIL import Image
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

logger = logging.getLogger(__name__)

class OCRService:
    """
    Service for Optical Character Recognition using EasyOCR.
    """
    
    _instance = None
    _reader = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(OCRService, cls).__new__(cls)
        return cls._instance

    def __init__(self, languages: List[str] = None, gpu: bool = True):
        """
        Initialize the OCR service.
        
        Args:
            languages: List of languages to support (default: ['en'])
            gpu: Whether to use GPU if available (default: True)
        """
        if not EASYOCR_AVAILABLE:
            logger.warning("EasyOCR not installed. OCR functionality will be disabled.")
            return

        if self._reader is None:
            if languages is None:
                languages = ['en']
            
            # Try GPU first if requested, fall back to CPU if CUDA fails
            if gpu:
                try:
                    self._reader = easyocr.Reader(languages, gpu=True)
                    logger.info("EasyOCR initialized with GPU acceleration")
                except RuntimeError as e:
                    # Handle CUDA compatibility errors (e.g., new GPU architectures)
                    error_msg = str(e).lower()
                    if 'cuda' in error_msg or 'kernel' in error_msg or 'sm_' in error_msg:
                        logger.warning(f"GPU initialization failed (CUDA compatibility issue), falling back to CPU: {e}")
                        try:
                            self._reader = easyocr.Reader(languages, gpu=False)
                            logger.info("EasyOCR initialized with CPU (GPU fallback)")
                        except Exception as cpu_e:
                            logger.error(f"Failed to initialize EasyOCR on CPU: {cpu_e}", exc_info=True)
                    else:
                        logger.error(f"Failed to initialize EasyOCR: {e}", exc_info=True)
                except Exception as e:
                    logger.warning(f"GPU initialization failed, falling back to CPU: {e}")
                    try:
                        self._reader = easyocr.Reader(languages, gpu=False)
                        logger.info("EasyOCR initialized with CPU (GPU fallback)")
                    except Exception as cpu_e:
                        logger.error(f"Failed to initialize EasyOCR on CPU: {cpu_e}", exc_info=True)
            else:
                try:
                    self._reader = easyocr.Reader(languages, gpu=False)
                    logger.info("EasyOCR initialized with CPU")
                except Exception as e:
                    logger.error(f"Failed to initialize EasyOCR: {e}", exc_info=True)

    # Default status bar height percentage to crop (typically ~5% of screen height)
    STATUS_BAR_CROP_PCT = 0.05
    
    def extract_text_from_bytes(self, image_bytes: bytes, min_confidence: float = 0.5, crop_status_bar: bool = True) -> List[Dict[str, Any]]:
        """
        Extract text from image bytes.
        
        Args:
            image_bytes: Raw image bytes (PNG/JPG)
            min_confidence: Minimum confidence threshold (0.0 to 1.0)
            crop_status_bar: Whether to crop the status bar from the top (default: True)
            
        Returns:
            List of dictionaries containing:
            - text: Detected text
            - bounds: [x_min, y_min, x_max, y_max] (coordinates relative to ORIGINAL image)
            - confidence: Confidence score (0.0 to 1.0)
        """
        if not EASYOCR_AVAILABLE or not self._reader:
            logger.error("OCR service not available")
            return []
            
        try:
            start_time = time.time()
            
            # log running time every second to show progress (in-place update)
            import threading
            stop_logging = False

            def log_progress():
                while not stop_logging:
                    elapsed = time.time() - start_time
                    # Use carriage return to overwrite same line (no newline)
                    print(f"\rOCR running... {elapsed:.1f}s   ", end='', flush=True)
                    time.sleep(1)
            
            log_thread = threading.Thread(target=log_progress)
            log_thread.daemon = True
            log_thread.start()
            
            try:
                # EasyOCR expects numpy array or file path or bytes
                # For bytes, we might need to convert to numpy array if passing bytes directly doesn't work well,
                # but reader.readtext supports bytes directly in recent versions.
                # To be safe and handle formats, let's use PIL -> numpy
                image = Image.open(io.BytesIO(image_bytes))
                original_height = image.height
                
                # Check for placeholder/invalid image (e.g., all black from FLAG_SECURE)
                # Convert to grayscale and check if it's essentially uniform (all same color)
                try:
                    grayscale = image.convert('L')
                    extrema = grayscale.getextrema()  # Returns (min, max) pixel values
                    # If variance is very small (< 5), image is essentially uniform/blank
                    if extrema[1] - extrema[0] < 5:
                        logger.warning("Skipping OCR: Image appears to be a placeholder (uniform color, likely FLAG_SECURE)")
                        stop_logging = True
                        log_thread.join(timeout=0.5)
                        return []
                except Exception as check_err:
                    logger.debug(f"Could not check image uniformity: {check_err}")
                
                # Crop status bar from top if enabled
                status_bar_offset = 0
                if crop_status_bar:
                    status_bar_offset = int(original_height * self.STATUS_BAR_CROP_PCT)
                    # Crop: (left, upper, right, lower)
                    image = image.crop((0, status_bar_offset, image.width, image.height))
                
                image_np = np.array(image)

                # result format: [[bounding_box, text, confidence], ...]
                # bounding_box is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                results = self._reader.readtext(image_np)
            finally:
                stop_logging = True
                log_thread.join(timeout=1.0)
            
            processed_results = []
            for bbox, text, conf in results:
                if conf < min_confidence:
                    continue
                    
                # Extract coordinates
                # bbox is a list of 4 points: top-left, top-right, bottom-right, bottom-left
                (tl, tr, br, bl) = bbox
                
                # Convert to integer coordinates
                x_min = int(min(tl[0], bl[0]))
                x_max = int(max(tr[0], br[0]))
                y_min = int(min(tl[1], tr[1]))
                y_max = int(max(bl[1], br[1]))
                
                # Adjust y coordinates back to original image space (add back status bar offset)
                y_min_adjusted = y_min + status_bar_offset
                y_max_adjusted = y_max + status_bar_offset
                
                processed_results.append({
                    'text': text,
                    'bounds': [x_min, y_min_adjusted, x_max, y_max_adjusted],
                    'confidence': float(conf)
                })
                
            elapsed = time.time() - start_time
            # Clear the progress line and print final result
            print(f"\rOCR completed in {elapsed:.2f}s ({len(processed_results)} elements)   ", flush=True)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Error during OCR extraction: {e}", exc_info=True)
            return []

    def is_available(self) -> bool:
        """Check if OCR service is available and initialized."""
        return EASYOCR_AVAILABLE and self._reader is not None
