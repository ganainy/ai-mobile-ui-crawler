from typing import List
from PIL import Image, ImageDraw, ImageFont
from .dtos import OCRResult

class OverlayDrawer:
    """Draws visual markers on a screenshot to represent grounded elements."""
    
    def __init__(self, box_color=(255, 0, 0, 80), text_color=(255, 255, 255), font_size=24):
        self.box_color = box_color
        self.text_color = text_color
        self.font_size = font_size
        try:
            # Try to load a standard font
            self.font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            # Fallback to default
            self.font = ImageFont.load_default()

    def draw(self, image_path: str, results: List[OCRResult], output_path: str) -> str:
        """
        Draws boxes and numeric IDs on the image.
        Returns the path to the saved image.
        """
        with Image.open(image_path).convert("RGBA") as base:
            # Create an overlay layer for transparency
            overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            for i, res in enumerate(results, start=1):
                # res.box is (x_min, y_min, x_max, y_max)
                draw.rectangle(res.box, outline=(255, 0, 0, 255), fill=self.box_color, width=2)
                
                # Draw ID badge at the top-left of the box
                label = str(i)
                # Simple background for text to make it readable
                text_pos = (res.box[0], res.box[1])
                draw.text(text_pos, label, fill=self.text_color, font=self.font)
                
            # Composite base and overlay
            out = Image.alpha_composite(base, overlay).convert("RGB")
            out.save(output_path, "PNG")
            
        return output_path
