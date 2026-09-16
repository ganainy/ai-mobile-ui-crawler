"""Element overlay renderer for UI element labels on screenshots."""

import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class ElementOverlayRenderer:
    """Renders indexed UI element labels onto screenshots."""

    # Color palette (cycling, same as OverlayRenderer for consistency)
    COLORS: list[str] = ["#00FF00", "#0088FF", "#FF8800", "#FF00FF", "#00FFFF"]

    def render(
        self,
        image: Image.Image,
        elements: list[dict],
        top_offset_px: int = 0,
    ) -> Image.Image:
        """Render element index labels onto an image.

        Args:
            image: Source image to render overlays on. May already have
                Status Bar Exclusion cropped off the top (ADR-0002) — pass
                the same top_offset_px used for that crop so bounds line up.
            elements: List of element dicts with 'index' and 'bounds' keys.
                      'bounds' is a string "x1,y1,x2,y2" in *absolute device*
                      pixel coordinates (see CONTEXT.md "Status Bar Exclusion").
            top_offset_px: Status Bar Exclusion pixels already cropped off
                the top of *image*. Subtracted from bounds before drawing so
                they land in image's (cropped) coordinate space instead of
                the device's absolute one.

        Returns:
            New image with element labels overlaid (in-memory, not saved).
        """
        if not elements:
            return image.copy()

        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)
        width, height = image.size

        for element in elements:
            index = element.get("index")
            bounds = element.get("bounds")

            if index is None or not bounds:
                continue

            # Parse bounds string "x1,y1,x2,y2"
            try:
                parts = bounds.split(",")
                if len(parts) != 4:
                    continue
                x1, y1, x2, y2 = map(int, parts)
            except (ValueError, AttributeError):
                # Skip elements with unparseable bounds
                continue

            if top_offset_px:
                y1 -= top_offset_px
                y2 -= top_offset_px

            # Validate bounds (skip invalid but don't fail the whole render)
            if x1 < 0 or y1 < 0 or x2 > width or y2 > height or x1 >= x2 or y1 >= y2:
                continue

            color = self.COLORS[(index - 1) % len(self.COLORS)]

            # Draw rectangle
            line_width = 4
            draw.rectangle([x1, y1, x2, y2], outline=color, width=line_width)

            # Draw index label with background box for legibility
            label = str(index)
            try:
                font = ImageFont.truetype("arialbd.ttf", 24)
            except Exception:
                font = ImageFont.load_default()

            label_bbox = draw.textbbox((0, 0), label, font=font)
            label_w = label_bbox[2] - label_bbox[0]
            label_h = label_bbox[3] - label_bbox[1]
            padding = 4

            # Black background box for label
            draw.rectangle(
                [x1 + 4, y1 + 4, x1 + label_w + padding * 2 + 4, y1 + label_h + padding * 2 + 4],
                fill="black"
            )
            draw.text((x1 + padding + 4, y1 + padding + 4), label, fill=color, font=font)

        return annotated
