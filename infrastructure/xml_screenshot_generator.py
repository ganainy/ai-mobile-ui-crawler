"""
XML Screenshot Generator - Creates synthetic screenshots from parsed element data.

This module generates wireframe images from parsed XML data when real screenshots
are unavailable (e.g., FLAG_SECURE apps). It draws colored rectangles with text labels
using the same parsed data that is sent to the AI.

This module is standalone and can be deleted without affecting the rest of the codebase.
To remove: 
1. Delete this file
2. Remove the import and call in screen_state_manager.py
"""

import re
import logging
from typing import Optional, List, Dict, Tuple, Any
from io import BytesIO

logger = logging.getLogger(__name__)

# Element type to color mapping (RGB)
ELEMENT_COLORS = {
    'Button': (66, 133, 244),      # Blue - buttons
    'ImageButton': (66, 133, 244), # Blue
    'TextView': (100, 100, 100),   # Dark gray - text
    'EditText': (52, 168, 83),     # Green - input fields
    'CheckBox': (251, 188, 4),     # Orange - checkboxes
    'Switch': (251, 188, 4),       # Orange
    'RadioButton': (251, 188, 4),  # Orange
    'ImageView': (156, 39, 176),   # Purple - images
    'RecyclerView': (200, 200, 200), # Light gray - containers
    'ScrollView': (200, 200, 200),
    'LinearLayout': (220, 220, 220),
    'FrameLayout': (220, 220, 220),
    'RelativeLayout': (220, 220, 220),
    'View': (180, 180, 180),       # Gray - generic views
    'default': (150, 150, 150),    # Default gray
}

# Minimum element size to draw (skip tiny elements)
MIN_ELEMENT_SIZE = 10


def generate_screenshot_from_xml(
    xml_content: str,
    screen_width: int = 1080,
    screen_height: int = 2400,
    background_color: Tuple[int, int, int] = (30, 30, 30),
) -> Optional[bytes]:
    """
    Generate a synthetic screenshot from XML page source.
    
    This is the main entry point that parses XML and generates the image.
    Uses the same parsing logic as xml_to_structured_json for consistency
    with what the AI sees.
    
    Args:
        xml_content: The Android XML page source
        screen_width: Width of the output image
        screen_height: Height of the output image
        background_color: Background color (RGB)
    
    Returns:
        PNG image bytes, or None if generation fails
    """
    if not xml_content:
        logger.warning("Empty XML content - cannot generate screenshot")
        return None
    
    try:
        # Parse elements using the shared parsing logic
        elements = _parse_elements_from_xml(xml_content)
        if not elements:
            logger.warning("No elements found in XML")
            return None
        
        return _generate_image_from_elements(
            elements, screen_width, screen_height, background_color
        )
        
    except Exception as e:
        logger.error(f"Error generating XML screenshot: {e}")
        return None


def generate_screenshot_from_elements(
    parsed_data: Dict[str, Any],
    screen_width: int = 1080,
    screen_height: int = 2400,
    background_color: Tuple[int, int, int] = (30, 30, 30),
) -> Optional[bytes]:
    """
    Generate a synthetic screenshot from pre-parsed element data.
    
    This uses the same data structure that xml_to_structured_json produces,
    ensuring what you see matches what the AI sees.
    
    Args:
        parsed_data: Dict with 'interactive' list and optional 'static' list
                    (same format as xml_to_structured_json output)
        screen_width: Width of the output image
        screen_height: Height of the output image
        background_color: Background color (RGB)
    
    Returns:
        PNG image bytes, or None if generation fails
    """
    if not parsed_data:
        logger.warning("Empty parsed data - cannot generate screenshot")
        return None
    
    try:
        # Convert parsed data to element list for drawing
        elements = []
        
        interactive_items = parsed_data.get('interactive', [])
        for item in interactive_items:
            elem = _convert_parsed_item_to_element(item, is_interactive=True)
            if elem:
                elements.append(elem)
        
        if not elements:
            logger.warning("No drawable elements in parsed data")
            return None
        
        return _generate_image_from_elements(
            elements, screen_width, screen_height, background_color
        )
        
    except Exception as e:
        logger.error(f"Error generating screenshot from parsed data: {e}")
        return None


def _convert_parsed_item_to_element(item: Dict[str, Any], is_interactive: bool = True) -> Optional[Dict]:
    """Convert a parsed item (from xml_to_structured_json) to drawable element format."""
    bounds = item.get('bounds', '')
    if not bounds:
        return None
    
    # Parse bounds "[x1,y1][x2,y2]"
    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
    if not match:
        return None
    
    x1, y1, x2, y2 = map(int, match.groups())
    width = x2 - x1
    height = y2 - y1
    
    if width < MIN_ELEMENT_SIZE or height < MIN_ELEMENT_SIZE:
        return None
    
    # Get display text (prefer text, then desc, then id)
    text = item.get('text', '') or item.get('desc', '')
    resource_id = item.get('id', '')
    if resource_id and '/' in resource_id:
        resource_id = resource_id.split('/')[-1]
    
    element_type = item.get('type', 'View')
    
    return {
        'x': x1,
        'y': y1,
        'width': width,
        'height': height,
        'text': text,
        'element_type': element_type,
        'resource_id': resource_id,
        'clickable': is_interactive,
    }


def _parse_elements_from_xml(xml_content: str) -> List[Dict]:
    """
    Parse XML content and extract element information.
    
    This uses regex parsing to extract bounds, text, and other attributes
    for drawing. For consistency, consider using xml_to_structured_json
    and generate_screenshot_from_elements instead.
    
    Returns a list of dicts with: x, y, width, height, text, element_type, resource_id
    """
    elements = []
    
    # Regex patterns
    bounds_pattern = r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
    text_pattern = r'text="([^"]*)"'
    content_desc_pattern = r'content-desc="([^"]*)"'
    resource_id_pattern = r'resource-id="([^"]*)"'
    class_pattern = r'class="([^"]*)"'
    clickable_pattern = r'clickable="(true|false)"'
    
    # Split by element tags
    element_chunks = re.split(r'(?=<[^/])', xml_content)
    
    for chunk in element_chunks:
        if not chunk.strip():
            continue
            
        bounds_match = re.search(bounds_pattern, chunk)
        if not bounds_match:
            continue
            
        x1, y1, x2, y2 = map(int, bounds_match.groups())
        width = x2 - x1
        height = y2 - y1
        
        if width < MIN_ELEMENT_SIZE or height < MIN_ELEMENT_SIZE:
            continue
        
        # Extract text
        text = ""
        text_match = re.search(text_pattern, chunk)
        if text_match and text_match.group(1):
            text = text_match.group(1)
        else:
            desc_match = re.search(content_desc_pattern, chunk)
            if desc_match and desc_match.group(1):
                text = desc_match.group(1)
        
        # Extract resource-id
        resource_id = ""
        id_match = re.search(resource_id_pattern, chunk)
        if id_match:
            resource_id = id_match.group(1)
            if '/' in resource_id:
                resource_id = resource_id.split('/')[-1]
        
        # Extract element type
        element_type = "View"
        class_match = re.search(class_pattern, chunk)
        if class_match:
            full_class = class_match.group(1)
            element_type = full_class.split('.')[-1]
        
        # Check if clickable
        clickable = False
        clickable_match = re.search(clickable_pattern, chunk)
        if clickable_match:
            clickable = clickable_match.group(1) == "true"
        
        elements.append({
            'x': x1,
            'y': y1,
            'width': width,
            'height': height,
            'text': text,
            'element_type': element_type,
            'resource_id': resource_id,
            'clickable': clickable,
        })
    
    return elements


def _generate_image_from_elements(
    elements: List[Dict],
    screen_width: int,
    screen_height: int,
    background_color: Tuple[int, int, int],
) -> Optional[bytes]:
    """Generate the actual image from element list."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("PIL/Pillow not installed - cannot generate XML screenshot")
        return None
    
    # Create image
    img = Image.new('RGB', (screen_width, screen_height), background_color)
    draw = ImageDraw.Draw(img)
    
    # Try to load fonts
    try:
        font = ImageFont.truetype("arial.ttf", 24)
        small_font = ImageFont.truetype("arial.ttf", 18)
    except:
        font = ImageFont.load_default()
        small_font = font
    
    # Sort elements by area (largest first) so smaller elements are drawn on top
    elements.sort(key=lambda e: (e['width'] * e['height']), reverse=True)
    
    # Draw elements
    for elem in elements:
        _draw_element(draw, elem, font, small_font)
    
    # Add header
    draw.rectangle([(0, 0), (screen_width, 40)], fill=(50, 50, 50))
    draw.text((10, 8), "🔒 XML-based Layout (FLAG_SECURE)", fill=(255, 200, 100), font=font)
    
    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def _draw_element(
    draw: 'ImageDraw.Draw',
    elem: Dict,
    font: 'ImageFont.FreeTypeFont',
    small_font: 'ImageFont.FreeTypeFont'
) -> None:
    """Draw a single element as a rectangle with text label."""
    x, y = elem['x'], elem['y']
    w, h = elem['width'], elem['height']
    element_type = elem['element_type']
    text = elem['text']
    resource_id = elem['resource_id']
    clickable = elem['clickable']
    
    # Get color based on element type
    color = ELEMENT_COLORS.get(element_type, ELEMENT_COLORS['default'])
    
    # Make clickable elements brighter
    if clickable:
        color = tuple(min(c + 40, 255) for c in color)
    
    # Draw rectangle outline
    outline_width = 2 if clickable else 1
    draw.rectangle(
        [(x, y), (x + w, y + h)],
        outline=color,
        width=outline_width
    )
    
    # Prepare label text
    label = ""
    if text:
        label = text[:40] + "..." if len(text) > 40 else text
    elif resource_id:
        label = f"[{resource_id}]"
    
    # Draw label if element is large enough
    if label and w > 60 and h > 30:
        # Truncate to fit
        max_chars = max(5, (w - 20) // 10)
        if len(label) > max_chars:
            label = label[:max_chars-2] + ".."
        
        # Center text in element
        try:
            bbox = draw.textbbox((0, 0), label, font=small_font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        except:
            text_w, text_h = len(label) * 10, 20
        
        text_x = x + (w - text_w) // 2
        text_y = y + (h - text_h) // 2
        
        # Draw text with SOLID background for readability (prevents overlap bleeding)
        padding = 6
        draw.rectangle(
            [(text_x - padding, text_y - padding), 
             (text_x + text_w + padding, text_y + text_h + padding)],
            fill=(30, 30, 30, 255),  # Fully opaque dark background
            outline=(100, 100, 100), # Subtle outline
            width=1
        )
        draw.text((text_x, text_y), label, fill=(255, 255, 255), font=small_font)
    
    # Draw element type indicator for buttons
    if element_type in ('Button', 'ImageButton') and w > 20 and h > 20:
        dot_x = x + 5
        dot_y = y + 5
        draw.ellipse([(dot_x, dot_y), (dot_x + 8, dot_y + 8)], fill=color)
