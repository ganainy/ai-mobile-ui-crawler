"""OCR verification utility for finding text in screenshots."""

import base64
import io
import time
import logging
from typing import Optional
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

class OCRVerifier:
    """Handles OCR-based text detection on device screenshots."""

    def __init__(self, tesseract_cmd: Optional[str] = None):
        """Initialize OCR verifier.
        
        Args:
            tesseract_cmd: Optional path to tesseract executable.
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def find_text_on_screen(self, driver, text: str, timeout: int = 5, exclude_text: Optional[str] = None) -> bool:
        """Take screenshot and search for text using OCR.
        
        Args:
            driver: Appium WebDriver instance
            text: Text to search for
            timeout: Timeout in seconds
            exclude_text: Text that, if found alone or in a specific context, should be ignored
            
        Returns:
            True if text is found, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Take screenshot
                screenshot_b64 = driver.get_screenshot_as_base64()
                
                # Process image
                img = Image.open(io.BytesIO(base64.b64decode(screenshot_b64)))
                
                # Perform OCR
                detected_text = pytesseract.image_to_string(img)
                clean_text = " ".join(detected_text.split())
                logger.info(f"OCR Full Text: [{clean_text}]")
                
                # Check for match
                found_match = text.lower() in clean_text.lower()
                
                # If we found it, but it's part of the excluded text, keep looking
                if found_match and exclude_text and exclude_text.lower() in clean_text.lower():
                    # If the matching text is ONLY found inside the excluded phrase, it's a false positive
                    # We simplify this by checking if the text exists outside the excluded phrase
                    # (This is a bit naive but works for 'Success' vs 'Success: Hub Loaded')
                    remaining_text = clean_text.lower().replace(exclude_text.lower(), "")
                    if text.lower() not in remaining_text:
                        logger.info(f"Matched '{text}' but it was part of excluded '{exclude_text}'. Skipping...")
                        found_match = False
                
                if found_match:
                    logger.info(f"Verified target text '{text}' on screen")
                    return True
                    
            except Exception as e:
                logger.warning(f"OCR detection attempt failed: {e}")
                
            time.sleep(1)
            
        return False
