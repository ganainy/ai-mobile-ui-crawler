"""Coordinate overlay rendering for mobile-crawler screenshots."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

logger = logging.getLogger(__name__)

class OverlayRenderer:
    """Renders coordinate overlays onto images."""
    
    # Color palette for actions (0-indexed)
    COLORS: List[str] = ["#00FF00", "#0088FF", "#FF8800", "#FF00FF", "#00FFFF"]
    ERROR_COLOR: str = "#FF0000"
    
    def render_overlays(
        self,
        image: Image.Image,
        actions: List[Dict[str, Any]],
        image_dimensions: Optional[Tuple[int, int]] = None
    ) -> Image.Image:
        """
        Render bounding box overlays onto an image.
        
        Args:
            image: Source image to render overlays on
            actions: List of action dicts with 'target_bounding_box' key
            image_dimensions: Optional (width, height) for bounds checking
        
        Returns:
            New image with overlays rendered
        """
        if not actions:
            return image.copy()
            
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)
        width, height = image_dimensions or image.size
        
        for i, action in enumerate(actions):
            bbox = action.get('target_bounding_box')
            if not bbox:
                continue
                
            top_left = bbox.get('top_left')
            bottom_right = bbox.get('bottom_right')
            if not top_left or not bottom_right:
                continue
                
            x1, y1 = top_left
            x2, y2 = bottom_right
            
            # Validate coordinates
            is_valid = self._validate_bbox(x1, y1, x2, y2, width, height)
            color = self.COLORS[i % len(self.COLORS)] if is_valid else self.ERROR_COLOR
            
            # Draw rectangle with thicker lines for high-res visibility
            line_width = 6 if is_valid else 8
            draw.rectangle([x1, y1, x2, y2], outline=color, width=line_width)
            
            # Draw center point (larger for high-res)
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            r = 12  # Larger radius for visibility
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

            # Draw action index label with larger font
            label = str(i + 1)
            try:
                # Try to load a bold font with larger size for high-res
                font = ImageFont.truetype("arialbd.ttf", 28)
            except Exception:
                font = ImageFont.load_default()
                
            # Draw a larger background for visibility
            label_bbox = draw.textbbox((0, 0), label, font=font)
            label_w, label_h = label_bbox[2] - label_bbox[0], label_bbox[3] - label_bbox[1]
            padding = 6
            draw.rectangle([x1 + 4, y1 + 4, x1 + label_w + padding*2 + 4, y1 + label_h + padding*2 + 4], fill="black")
            draw.text((x1 + padding + 4, y1 + padding + 4), label, fill=color, font=font)
            
        return annotated

    def _validate_bbox(self, x1: int, y1: int, x2: int, y2: int, width: int, height: int) -> bool:
        """Check if bounding box is within image bounds."""
        if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
            return False
        if x1 >= x2 or y1 >= y2:
            return False
        return True
    
    def save_annotated(
        self,
        image: Image.Image,
        actions: List[Dict[str, Any]],
        original_path: str
    ) -> str:
        """
        Render overlays and save annotated image to disk.
        
        Args:
            image: Source image
            actions: List of action dicts
            original_path: Path to original screenshot
        
        Returns:
            Path to saved annotated image
        """
        if not actions:
            return ""
            
        try:
            annotated = self.render_overlays(image, actions)
            
            # Create annotated path
            path = Path(original_path)
            annotated_path = path.parent / f"{path.stem}_annotated{path.suffix}"
            
            annotated.save(annotated_path)
            logger.debug(f"Saved annotated screenshot: {annotated_path}")
            return str(annotated_path)
        except Exception as e:
            logger.error(f"Failed to save annotated screenshot: {e}")
            return ""
