#!/usr/bin/env python3
"""
Screenshot annotation service for marking action coordinates on screenshots.
"""

import json
import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class ScreenshotAnnotator:
    """
    Service that annotates screenshots with action coordinates from the database.
    
    Reads step data from the crawl database and draws markers at tap locations
    on the corresponding screenshots.
    """
    
    # Annotation styling
    MARKER_COLOR = (255, 0, 0)  # Red
    MARKER_OUTLINE_COLOR = (255, 255, 255)  # White outline
    MARKER_RADIUS = 20
    MARKER_WIDTH = 4
    TEXT_COLOR = (255, 255, 255)  # White
    TEXT_BG_COLOR = (255, 0, 0, 200)  # Semi-transparent red
    
    def __init__(self):
        """Initialize the screenshot annotator."""
        pass
    
    def annotate_session(
        self, 
        session_dir: Path,
        output_dir: Optional[Path] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Annotate all screenshots in a session with action coordinates.
        
        Args:
            session_dir: Path to the session directory
            output_dir: Optional output directory for annotated screenshots.
                       Defaults to session_dir/annotated_screenshots
        
        Returns:
            Tuple of (success, result_data)
            result_data contains: annotated_count, skipped_count, output_dir, errors
        """
        result = {
            "annotated_count": 0,
            "skipped_count": 0,
            "output_dir": None,
            "errors": []
        }
        
        try:
            session_path = Path(session_dir)
            if not session_path.exists():
                result["errors"].append(f"Session directory not found: {session_dir}")
                return False, result
            
            # Find database
            db_dir = session_path / "database"
            if not db_dir.exists():
                result["errors"].append(f"Database directory not found: {db_dir}")
                return False, result
            
            db_files = list(db_dir.glob("*.db"))
            if not db_files:
                result["errors"].append(f"No database files found in: {db_dir}")
                return False, result
            
            db_path = db_files[0]  # Use first database found
            
            # Find screenshots directory
            screenshots_dir = session_path / "screenshots"
            if not screenshots_dir.exists():
                result["errors"].append(f"Screenshots directory not found: {screenshots_dir}")
                return False, result
            
            # Set output directory
            if output_dir is None:
                output_dir = session_path / "annotated_screenshots"
            result["output_dir"] = str(output_dir)
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get step data from database
            step_data = self._get_step_data(db_path)
            if not step_data:
                result["errors"].append("No step data found in database")
                return False, result
            
            # Process each screenshot
            screenshot_files = list(screenshots_dir.glob("*.png"))
            
            for screenshot_path in screenshot_files:
                try:
                    annotated = self._annotate_screenshot(
                        screenshot_path, 
                        step_data, 
                        output_dir
                    )
                    if annotated:
                        result["annotated_count"] += 1
                    else:
                        result["skipped_count"] += 1
                except Exception as e:
                    result["errors"].append(f"Error processing {screenshot_path.name}: {e}")
                    result["skipped_count"] += 1
            
            success = result["annotated_count"] > 0
            return success, result
            
        except Exception as e:
            logger.error(f"Error annotating session: {e}", exc_info=True)
            result["errors"].append(str(e))
            return False, result
    
    def _get_step_data(self, db_path: Path) -> Dict[int, Dict[str, Any]]:
        """
        Get step data from the database.
        
        Args:
            db_path: Path to the SQLite database
            
        Returns:
            Dictionary mapping step_number to step data with coordinates
        """
        step_data = {}
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT step_number, run_id, action_description, mapped_action_json, from_screen_id
                FROM steps_log
                WHERE mapped_action_json IS NOT NULL
                ORDER BY step_number ASC
            """)
            
            rows = cursor.fetchall()
            
            for row in rows:
                step_number, run_id, action_desc, mapped_json, from_screen_id = row
                
                if not mapped_json:
                    continue
                
                try:
                    mapped_data = json.loads(mapped_json)
                    
                    # Extract coordinates
                    coords = self._extract_coordinates(mapped_data)
                    
                    if coords:
                        step_data[step_number] = {
                            "run_id": run_id,
                            "action": mapped_data.get("action", ""),
                            "action_description": action_desc,
                            "target_identifier": mapped_data.get("target_identifier", ""),
                            "coordinates": coords,
                            "from_screen_id": from_screen_id
                        }
                except json.JSONDecodeError:
                    continue
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error reading database: {e}")
        
        return step_data
    
    def _extract_coordinates(self, mapped_data: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        """
        Extract tap coordinates from mapped action data.
        
        Tries multiple sources:
        1. target_bounding_box (if present)
        2. OCR results matching target_identifier
        
        Args:
            mapped_data: The mapped action JSON data
            
        Returns:
            Tuple of (x, y) center coordinates, or None if not found
        """
        # Try target_bounding_box first
        bbox = mapped_data.get("target_bounding_box")
        if bbox:
            coords = self._bbox_to_center(bbox)
            if coords:
                return coords
        
        # Try to find coordinates from OCR results
        target_id = mapped_data.get("target_identifier", "")
        ocr_results = mapped_data.get("ocr_results", [])
        
        if target_id and target_id.startswith("ocr_") and ocr_results:
            try:
                # Extract index from ocr_X format
                idx = int(target_id.split("_")[1])
                if 0 <= idx < len(ocr_results):
                    ocr_item = ocr_results[idx]
                    bounds = ocr_item.get("bounds")
                    if bounds and len(bounds) == 4:
                        # bounds is [x_min, y_min, x_max, y_max]
                        x = (bounds[0] + bounds[2]) // 2
                        y = (bounds[1] + bounds[3]) // 2
                        return (x, y)
            except (ValueError, IndexError):
                pass
        
        # Try to match target_id text to OCR results
        if target_id and ocr_results:
            for ocr_item in ocr_results:
                ocr_text = ocr_item.get("text", "")
                ocr_id = ocr_item.get("id", "")
                
                # Check if target matches OCR text or ID
                if target_id == ocr_id or target_id.lower() in ocr_text.lower():
                    bounds = ocr_item.get("bounds")
                    if bounds and len(bounds) == 4:
                        x = (bounds[0] + bounds[2]) // 2
                        y = (bounds[1] + bounds[3]) // 2
                        return (x, y)
        
        return None
    
    def _bbox_to_center(self, bbox: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        """
        Convert a bounding box to center coordinates.
        
        Args:
            bbox: Bounding box with top_left and bottom_right keys
            
        Returns:
            Tuple of (x, y) center coordinates
        """
        try:
            if isinstance(bbox, dict):
                top_left = bbox.get("top_left", [])
                bottom_right = bbox.get("bottom_right", [])
                
                if len(top_left) >= 2 and len(bottom_right) >= 2:
                    x = (top_left[0] + bottom_right[0]) // 2
                    y = (top_left[1] + bottom_right[1]) // 2
                    return (x, y)
        except Exception:
            pass
        return None
    
    def _annotate_screenshot(
        self, 
        screenshot_path: Path, 
        step_data: Dict[int, Dict[str, Any]],
        output_dir: Path
    ) -> bool:
        """
        Annotate a single screenshot with action coordinates.
        
        Args:
            screenshot_path: Path to the screenshot file
            step_data: Dictionary of step data with coordinates
            output_dir: Output directory for annotated image
            
        Returns:
            True if screenshot was annotated, False otherwise
        """
        # Parse filename to extract step number
        # Format: screen_run{run_id}_step{step}_{hash}.png
        filename = screenshot_path.name
        
        match = re.match(r"screen_run(\d+)_step(\d+)_", filename)
        if not match:
            # Try legacy format: screen_{num}_{hash}.png
            return False
        
        run_id = int(match.group(1))
        step_number = int(match.group(2))
        
        # Get step data for this step
        data = step_data.get(step_number)
        if not data:
            return False
        
        coords = data.get("coordinates")
        if not coords:
            return False
        
        # Load and annotate image
        try:
            img = Image.open(screenshot_path).convert("RGBA")
            
            # Create overlay for semi-transparent elements
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            x, y = coords
            
            # Draw outer circle (white outline)
            outer_radius = self.MARKER_RADIUS + 2
            draw.ellipse(
                [x - outer_radius, y - outer_radius, x + outer_radius, y + outer_radius],
                outline=self.MARKER_OUTLINE_COLOR,
                width=self.MARKER_WIDTH + 2
            )
            
            # Draw inner circle (red)
            draw.ellipse(
                [x - self.MARKER_RADIUS, y - self.MARKER_RADIUS, 
                 x + self.MARKER_RADIUS, y + self.MARKER_RADIUS],
                outline=self.MARKER_COLOR,
                width=self.MARKER_WIDTH
            )
            
            # Draw cross in center
            cross_size = self.MARKER_RADIUS // 2
            draw.line(
                [x - cross_size, y, x + cross_size, y],
                fill=self.MARKER_COLOR,
                width=2
            )
            draw.line(
                [x, y - cross_size, x, y + cross_size],
                fill=self.MARKER_COLOR,
                width=2
            )
            
            # Add action label
            action = data.get("action", "tap")
            target = data.get("target_identifier", "")
            label = f"Step {step_number}: {action}"
            if target and len(target) < 30:
                label += f" → {target}"
            
            # Draw label with background
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except (IOError, OSError):
                font = ImageFont.load_default()
            
            # Get text size
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Position label above the marker
            label_x = max(5, min(x - text_width // 2, img.width - text_width - 5))
            label_y = max(5, y - self.MARKER_RADIUS - text_height - 10)
            
            # Draw background rectangle
            padding = 4
            draw.rectangle(
                [label_x - padding, label_y - padding,
                 label_x + text_width + padding, label_y + text_height + padding],
                fill=self.TEXT_BG_COLOR
            )
            
            # Draw text
            draw.text((label_x, label_y), label, fill=self.TEXT_COLOR, font=font)
            
            # Composite overlay onto original image
            img = Image.alpha_composite(img, overlay)
            
            # Convert back to RGB for saving as PNG
            img = img.convert("RGB")
            
            # Save annotated image
            output_path = output_dir / f"annotated_{filename}"
            img.save(output_path, "PNG")
            
            logger.info(f"Annotated {filename} with coordinates ({x}, {y})")
            return True
            
        except Exception as e:
            logger.error(f"Error annotating {filename}: {e}")
            return False
    
    def annotate_screenshots_from_path(
        self, 
        screenshots_dir: str, 
        db_path: str,
        output_dir: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Annotate screenshots using explicit paths.
        
        Convenience method for CLI usage.
        
        Args:
            screenshots_dir: Path to screenshots directory
            db_path: Path to the database file
            output_dir: Optional output directory
            
        Returns:
            Tuple of (success, result_data)
        """
        result = {
            "annotated_count": 0,
            "skipped_count": 0,
            "output_dir": None,
            "errors": []
        }
        
        try:
            screenshots_path = Path(screenshots_dir)
            db_file = Path(db_path)
            
            if not screenshots_path.exists():
                result["errors"].append(f"Screenshots directory not found: {screenshots_dir}")
                return False, result
            
            if not db_file.exists():
                result["errors"].append(f"Database not found: {db_path}")
                return False, result
            
            # Set output directory
            if output_dir:
                out_path = Path(output_dir)
            else:
                out_path = screenshots_path.parent / "annotated_screenshots"
            
            out_path.mkdir(parents=True, exist_ok=True)
            result["output_dir"] = str(out_path)
            
            # Get step data
            step_data = self._get_step_data(db_file)
            if not step_data:
                result["errors"].append("No step data with coordinates found in database")
                return False, result
            
            # Process screenshots
            screenshot_files = list(screenshots_path.glob("*.png"))
            
            for screenshot_path in screenshot_files:
                try:
                    annotated = self._annotate_screenshot(screenshot_path, step_data, out_path)
                    if annotated:
                        result["annotated_count"] += 1
                    else:
                        result["skipped_count"] += 1
                except Exception as e:
                    result["errors"].append(f"Error processing {screenshot_path.name}: {e}")
                    result["skipped_count"] += 1
            
            success = result["annotated_count"] > 0
            return success, result
            
        except Exception as e:
            logger.error(f"Error annotating screenshots: {e}", exc_info=True)
            result["errors"].append(str(e))
            return False, result
