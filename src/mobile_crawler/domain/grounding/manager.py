import os
import logging
from typing import List, Optional
from PIL import Image

from .dtos import OCRResult, GroundingOverlay
from .interfaces import GroundingService, OCREngine
from .ocr_engine import EasyOCREngine
from .overlay import OverlayDrawer
from .mapper import LabelMapper

logger = logging.getLogger(__name__)

class GroundingManager(GroundingService):
    """
    Main entry point for grounding logic.
    Coordinates OCR detection, label mapping, and overlay drawing.
    """
    
    def __init__(self, ocr_engine: Optional[OCREngine] = None):
        self.ocr_engine = ocr_engine or EasyOCREngine()
        self.drawer = OverlayDrawer()
        self.mapper = LabelMapper()

    def process_screenshot(self, screenshot_path: str) -> GroundingOverlay:
        """
        Executes the grounding pipeline on a screenshot.
        """
        import time
        start_time = time.time()
        
        if not os.path.exists(screenshot_path):
            raise FileNotFoundError(f"Screenshot not found: {screenshot_path}")
            
        # 1. OCR Detection
        logger.info(f"Running OCR on {screenshot_path}...")
        results = self.ocr_engine.detect_text(screenshot_path)
        ocr_duration = time.time() - start_time
        logger.info(f"Detected {len(results)} text regions in {ocr_duration:.2f}s.")
        
        # 2. Label Mapping
        label_map = self.mapper.assign_labels(results)
        
        # 3. Generate Output Path
        base, ext = os.path.splitext(screenshot_path)
        output_path = f"{base}_grounded{ext}"
        
        # 4. Draw Overlays
        self.drawer.draw(screenshot_path, results, output_path)
        
        # 5. Get Original Dimensions
        with Image.open(screenshot_path) as img:
            dims = img.size
            
        total_duration = time.time() - start_time
        logger.info(f"Grounding completed in {total_duration:.2f}s (OCR: {ocr_duration:.2f}s).")
            
        # 6. Build ocr_elements for prompt context
        ocr_elements = []
        # LabelMapper assigns labels sequentially to the results list
        for i, result in enumerate(results):
            label_id = i + 1
            ocr_elements.append({
                "label": label_id,
                "text": result.text,
                "bounds": result.box
            })

        return GroundingOverlay(
            marked_image_path=output_path,
            label_map=label_map,
            ocr_elements=ocr_elements,
            original_dimensions=dims
        )

    def process(self, screenshot_path: str) -> GroundingOverlay:
        """Alias for process_screenshot adhering to GroundingService interface."""
        return self.process_screenshot(screenshot_path)
