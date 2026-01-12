"""Screenshot capture and processing utilities."""

import io
import time
from typing import Optional, Tuple, BinaryIO
from pathlib import Path
import logging
import base64

from PIL import Image
import numpy as np

from mobile_crawler.infrastructure.appium_driver import AppiumDriver
from mobile_crawler.infrastructure.device_detection import AndroidDevice

logger = logging.getLogger(__name__)


class ScreenshotCaptureError(Exception):
    """Raised when screenshot capture fails."""
    pass


class ScreenshotCapture:
    """Handles screenshot capture and processing for Android devices."""

    def __init__(
        self,
        driver: AppiumDriver,
        run_id: int,
        max_width: int = 800,
        max_height: int = 600,
        output_dir: Optional[Path] = None,
        ai_max_width: int = 1024,
        ai_max_height: int = 1024,
        ai_jpeg_quality: int = 75
    ):
        """Initialize screenshot capture.

        Args:
            driver: Appium driver instance
            run_id: Run ID to create run-specific subdirectory (required)
            max_width: Maximum width for downscaled screenshots
            max_height: Maximum height for downscaled screenshots
            output_dir: Directory to save screenshots (default: ./screenshots/run_{id})
            ai_max_width: Maximum width for AI-optimized images
            ai_max_height: Maximum height for AI-optimized images
            ai_jpeg_quality: JPEG quality for AI images (1-95, lower = smaller file)
        """
        self.driver = driver
        self.max_width = max_width
        self.max_height = max_height
        
        # Create run-specific directory
        if output_dir is None:
            self.output_dir = Path("screenshots") / f"run_{run_id}"
        else:
            self.output_dir = output_dir
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # AI compression settings
        self.ai_max_width = ai_max_width
        self.ai_max_height = ai_max_height
        self.ai_jpeg_quality = ai_jpeg_quality

    def capture_screenshot(self) -> Image.Image:
        """Capture a screenshot from the device.

        Returns:
            PIL Image object

        Raises:
            ScreenshotCaptureError: If capture fails
        """
        try:
            # Get screenshot as base64 string
            screenshot_base64 = self.driver.get_driver().get_screenshot_as_base64()

            # Convert base64 to PIL Image
            screenshot_bytes = io.BytesIO()
            screenshot_bytes.write(bytes(screenshot_base64, 'utf-8'))
            screenshot_bytes.seek(0)

            # Decode base64 and create PIL Image
            image_data = base64.b64decode(screenshot_base64)
            image = Image.open(io.BytesIO(image_data))

            return image

        except Exception as e:
            raise ScreenshotCaptureError(f"Failed to capture screenshot: {e}") from e

    def capture_full(self, filename: Optional[str] = None) -> Tuple[Image.Image, str, str, float]:
        """Capture a screenshot and return image, path, AI-optimized base64, and scale factor.

        This method provides all data needed by the crawler loop in one call.
        The base64 string is compressed for efficient AI processing:
        - Downscaled to max 1024x1024 (configurable)
        - Converted to JPEG at 75% quality (configurable)
        - Typically reduces size by 80-90% vs raw PNG

        IMPORTANT: The returned scale_factor must be used to convert AI coordinates
        back to original screen coordinates: original_coord = ai_coord / scale_factor

        Args:
            filename: Optional filename for the screenshot

        Returns:
            Tuple of (PIL Image, file path, AI-optimized base64 string, scale_factor)
            - scale_factor: The factor used to downscale (e.g., 0.5 means image was halved)
              Use this to convert AI coordinates back: screen_coord = ai_coord / scale_factor

        Raises:
            ScreenshotCaptureError: If capture fails
        """
        try:
            # Get screenshot as base64 string
            screenshot_base64 = self.driver.get_driver().get_screenshot_as_base64()

            # Convert base64 to PIL Image
            image_data = base64.b64decode(screenshot_base64)
            image = Image.open(io.BytesIO(image_data))

            # Generate filename if not provided
            if filename is None:
                timestamp = int(time.time() * 1000)
                filename = f"screenshot_{timestamp}.png"

            filepath = self.output_dir / filename

            # Save original image to file (keep full quality for local storage)
            image.save(filepath)

            # Create AI-optimized version for base64 and get scale factor
            ai_optimized_b64, scale_factor = self._compress_for_ai(image)

            logger.debug(f"Screenshot captured and saved: {filepath}, scale_factor: {scale_factor}")
            return (image, str(filepath), ai_optimized_b64, scale_factor)

        except Exception as e:
            raise ScreenshotCaptureError(f"Failed to capture full screenshot: {e}") from e

    def _compress_for_ai(self, image: Image.Image) -> Tuple[str, float]:
        """Compress image for AI processing to reduce tokens and latency.

        Applies:
        - JPEG compression at configurable quality
        - RGB conversion (removes alpha channel)
        - NO dimension scaling - keeps original dimensions for accurate coordinates

        Args:
            image: PIL Image to compress

        Returns:
            Tuple of (base64 encoded JPEG string, scale_factor which is always 1.0)
        """
        width, height = image.size
        
        # NO dimension scaling - keep original size for accurate AI coordinates
        scale_factor = 1.0

        # Convert to RGB (JPEG doesn't support alpha)
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')

        # Compress to JPEG (reduces file size without changing dimensions)
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=self.ai_jpeg_quality, optimize=True)
        compressed_data = buffer.getvalue()

        # Encode to base64
        compressed_b64 = base64.b64encode(compressed_data).decode('utf-8')

        logger.debug(f"AI image: {width}x{height}, compressed to {len(compressed_data)} bytes, {len(compressed_b64)} chars base64")
        return compressed_b64, scale_factor

    def capture_screenshot_to_file(self, filename: Optional[str] = None) -> Optional[str]:
        """Capture a screenshot and save to file.

        Args:
            filename: Optional filename for the screenshot

        Returns:
            Path to the saved screenshot file, or None if failed
        """
        try:
            if filename is None:
                timestamp = int(time.time() * 1000)
                filename = f"screenshot_{timestamp}.png"

            filepath = self.output_dir / filename

            # Capture and save screenshot
            image = self.capture_screenshot()
            image.save(filepath)

            logger.debug(f"Screenshot saved: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to capture screenshot to file: {e}")
            return None

    def capture_and_downscale(self) -> Image.Image:
        """Capture screenshot and downscale to maximum dimensions.

        Returns:
            Downscaled PIL Image object
        """
        image = self.capture_screenshot()
        return self._downscale_image(image)

    def _downscale_image(self, image: Image.Image) -> Image.Image:
        """Downscale image while maintaining aspect ratio.

        Args:
            image: PIL Image to downscale

        Returns:
            Downscaled PIL Image
        """
        width, height = image.size

        # Calculate scaling factor
        width_ratio = self.max_width / width
        height_ratio = self.max_height / height
        scale_factor = min(width_ratio, height_ratio, 1.0)  # Don't upscale

        if scale_factor >= 1.0:
            # No downscaling needed
            return image

        # Calculate new dimensions
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)

        # Use high-quality downscaling
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def capture_to_file(self, file_path: str, downscale: bool = True) -> None:
        """Capture screenshot and save to file.

        Args:
            file_path: Path to save the screenshot
            downscale: Whether to downscale the image
        """
        image = self.capture_and_downscale() if downscale else self.capture_screenshot()

        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        # Save image
        image.save(file_path)

    def capture_to_numpy(self, downscale: bool = True) -> np.ndarray:
        """Capture screenshot and return as numpy array.

        Args:
            downscale: Whether to downscale the image

        Returns:
            Numpy array in RGB format (height, width, 3)
        """
        image = self.capture_and_downscale() if downscale else self.capture_screenshot()

        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        return np.array(image)

    def get_image_info(self, image: Optional[Image.Image] = None) -> dict:
        """Get information about an image.

        Args:
            image: PIL Image object, or None to capture new screenshot

        Returns:
            Dictionary with image information
        """
        if image is None:
            image = self.capture_screenshot()

        return {
            'width': image.width,
            'height': image.height,
            'mode': image.mode,
            'format': image.format,
            'size_bytes': len(image.tobytes()) if hasattr(image, 'tobytes') else 0
        }

    def compare_images(self, image1: Image.Image, image2: Image.Image,
                      threshold: float = 0.1) -> Tuple[bool, float]:
        """Compare two images for similarity.

        Args:
            image1: First PIL Image
            image2: Second PIL Image
            threshold: Similarity threshold (0.0 = identical, 1.0 = completely different)

        Returns:
            Tuple of (is_similar, difference_score)
        """
        # Ensure same size
        if image1.size != image2.size:
            # Resize second image to match first
            image2 = image2.resize(image1.size, Image.Resampling.LANCZOS)

        # Convert to grayscale for comparison
        gray1 = image1.convert('L')
        gray2 = image2.convert('L')

        # Calculate difference
        diff = np.abs(np.array(gray1, dtype=np.float32) - np.array(gray2, dtype=np.float32))
        difference_score = np.mean(diff) / 255.0  # Normalize to 0-1

        is_similar = difference_score <= threshold

        return is_similar, difference_score

    def wait_for_stable_screen(self, stability_threshold: float = 0.05,
                              max_attempts: int = 10, delay: float = 0.5) -> Image.Image:
        """Wait for screen to become stable (no significant changes).

        Args:
            stability_threshold: Maximum difference score for stability
            max_attempts: Maximum number of capture attempts
            delay: Delay between captures in seconds

        Returns:
            Stable screenshot image

        Raises:
            ScreenshotCaptureError: If screen doesn't stabilize
        """
        previous_image = None

        for attempt in range(max_attempts):
            current_image = self.capture_and_downscale()

            if previous_image is not None:
                is_stable, difference = self.compare_images(previous_image, current_image)
                if is_stable:
                    logger.info(f"Screen stabilized after {attempt + 1} attempts")
                    return current_image

                logger.debug(f"Screen difference: {difference:.4f} (threshold: {stability_threshold})")

            previous_image = current_image

            if attempt < max_attempts - 1:
                time.sleep(delay)

        raise ScreenshotCaptureError(
            f"Screen did not stabilize within {max_attempts} attempts"
        )