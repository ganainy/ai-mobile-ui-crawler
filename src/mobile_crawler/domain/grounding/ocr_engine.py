import logging
from typing import List
import easyocr
import numpy as np
from .dtos import OCRResult
from .interfaces import OCREngine

logger = logging.getLogger(__name__)

class EasyOCREngine(OCREngine):
    """Wrapper for EasyOCR detection."""
    
    def __init__(self, languages=['en'], gpu=True):
        try:
            self.reader = easyocr.Reader(languages, gpu=gpu)
            logger.info(f"EasyOCR initialized with languages={languages}, gpu={gpu}")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            raise

    def detect_text(self, image_path: str) -> List[OCRResult]:
        """
        Detects text and converts result to OCRResult objects.
        EasyOCR output format: [([[x,y], [x,y], [x,y], [x,y]], text, confidence), ...]
        """
        try:
            # detail=1 returns bounding box, text, confidence
            raw_results = self.reader.readtext(image_path)
            
            results = []
            for bbox, text, confidence in raw_results:
                # bbox is list of 4 points: tl, tr, br, bl
                # Convert to x_min, y_min, x_max, y_max
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                x_min, x_max = int(min(xs)), int(max(xs))
                y_min, y_max = int(min(ys)), int(max(ys))
                
                center = ((x_min + x_max) // 2, (y_min + y_max) // 2)
                
                results.append(OCRResult(
                    text=text,
                    box=(x_min, y_min, x_max, y_max),
                    confidence=float(confidence),
                    center=center
                ))
            
            return results
        except Exception as e:
            logger.error(f"OCR detection error for {image_path}: {e}")
            return []
