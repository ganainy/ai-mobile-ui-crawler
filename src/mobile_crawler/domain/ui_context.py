"""UI context management with OmniParser fallback."""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class UIContextManager:
    """Manages UI context retrieval with a11y + OmniParser fallback."""

    def __init__(self, db_connection, omni_client):
        self.db = db_connection
        self.omni_client = omni_client
        self._prev_a11y: Optional[List[Dict]] = None

    async def get_context(self, droidrun_tools, phone_state: Dict[str, Any]) -> Dict[str, Any]:
        """Get UI context for current screen."""
        state = await droidrun_tools.get_state()
        a11y_elements = state.get("a11y_tree", [])
        screen_key = self._get_screen_key(phone_state)
        cache_status = self._get_cache_status(screen_key)

        if cache_status == "trusted":
            self._prev_a11y = a11y_elements
            return {"source": "a11y", "a11y": a11y_elements, "issues": []}

        if cache_status == "needs_omni":
            cached = self._get_cached_omni(screen_key)
            if cached:
                return {"source": "merged", "a11y": a11y_elements, "omni": cached, "issues": ["cached_omni"]}

        issues = self._quick_a11y_check(a11y_elements, self._prev_a11y)

        if not issues:
            self._set_cache_status(screen_key, "trusted")
            self._prev_a11y = a11y_elements
            return {"source": "a11y", "a11y": a11y_elements, "issues": []}

        logger.info(f"A11y issues for {screen_key}: {issues}")
        fmt, image_bytes = await droidrun_tools.take_screenshot()
        omni_elements = self.omni_client.parse(image_bytes)

        unmatched = self._find_unmatched_interactables(omni_elements, a11y_elements)
        uncovered = self._find_uncovered_regions(omni_elements, a11y_elements)

        self._cache_omni_result(screen_key, omni_elements)
        self._set_cache_status(screen_key, "needs_omni")
        self._prev_a11y = a11y_elements

        return {
            "source": "merged",
            "a11y": a11y_elements,
            "omni": omni_elements,
            "issues": issues,
            "unmatched_interactables": unmatched,
            "uncovered_regions": uncovered,
        }

    def _get_screen_key(self, phone_state: Dict[str, Any]) -> str:
        package = phone_state.get("current_app", {}).get("package", "unknown")
        activity = phone_state.get("current_app", {}).get("activity", "unknown")
        return hashlib.md5(f"{package}:{activity}".encode()).hexdigest()

    def _quick_a11y_check(self, a11y: List[Dict], prev_a11y: Optional[List[Dict]]) -> List[str]:
        """Run cheap validation checks on a11y tree."""
        issues = []
        if len(a11y) < 5:
            issues.append("too_sparse")
        if not any(el.get("interactivity") or el.get("clickable") for el in a11y):
            issues.append("nothing_clickable")
        if prev_a11y is not None and prev_a11y != [] and a11y == prev_a11y:
            issues.append("a11y_stale")
        return issues

    def _find_unmatched_interactables(self, omni: List[Dict], a11y: List[Dict], iou_threshold: float = 0.3) -> List[Dict]:
        """Find OmniParser interactable elements with no a11y match."""
        def get_bbox(el: Dict) -> Optional[List[float]]:
            return el.get("bbox")

        def bbox_iou(box1: List[float], box2: List[float]) -> float:
            if not box1 or not box2:
                return 0.0
            x1 = max(box1[0], box2[0])
            y1 = max(box1[1], box2[1])
            x2 = min(box1[2], box2[2])
            y2 = min(box1[3], box2[3])
            intersection = max(0, x2 - x1) * max(0, y2 - y1)
            area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
            area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
            union = area1 + area2 - intersection
            return intersection / union if union > 0 else 0

        unmatched = []
        for omni_el in omni:
            if not omni_el.get("interactivity"):
                continue
            omni_bbox = get_bbox(omni_el)
            if not omni_bbox:
                continue
            matched = any(bbox_iou(omni_bbox, get_bbox(a11y_el)) > iou_threshold for a11y_el in a11y if get_bbox(a11y_el))
            if not matched:
                unmatched.append(omni_el)
        return unmatched

    def _find_uncovered_regions(self, omni: List[Dict], a11y: List[Dict], grid: int = 4) -> List[List[float]]:
        """Find screen regions where OmniParser sees things but a11y is blind."""
        uncovered = []
        for row in range(grid):
            for col in range(grid):
                cell = [col / grid, row / grid, (col + 1) / grid, (row + 1) / grid]

                def in_cell(bbox: List[float]) -> bool:
                    if not bbox:
                        return False
                    cx = (bbox[0] + bbox[2]) / 2
                    cy = (bbox[1] + bbox[3]) / 2
                    return cell[0] <= cx <= cell[2] and cell[1] <= cy <= cell[3]

                has_omni = any(in_cell(el.get("bbox", [])) for el in omni)
                has_a11y = any(in_cell(el.get("bbox", [])) for el in a11y)
                if has_omni and not has_a11y:
                    uncovered.append(cell)
        return uncovered

    def _get_cache_status(self, screen_key: str) -> Optional[str]:
        try:
            row = self.db.execute(
                "SELECT status FROM omni_parser_cache WHERE screen_key = ? ORDER BY last_accessed_at DESC LIMIT 1",
                (screen_key,)
            ).fetchone()
            return row["status"] if row else None
        except Exception:
            return None

    def _set_cache_status(self, screen_key: str, status: str) -> None:
        try:
            self.db.execute(
                """INSERT OR REPLACE INTO omni_parser_cache 
                   (screen_key, backend, elements_json, created_at, last_accessed_at, access_count)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (screen_key, self.omni_client.backend.value, "[]",
                 datetime.now().isoformat(), datetime.now().isoformat(), 1)
            )
            self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to set cache status: {e}")

    def _get_cached_omni(self, screen_key: str) -> Optional[List[Dict]]:
        try:
            row = self.db.execute(
                "SELECT elements_json FROM omni_parser_cache WHERE screen_key = ? ORDER BY last_accessed_at DESC LIMIT 1",
                (screen_key,)
            ).fetchone()
            if row and row["elements_json"]:
                self.db.execute(
                    "UPDATE omni_parser_cache SET last_accessed_at = ?, access_count = access_count + 1 WHERE screen_key = ?",
                    (datetime.now().isoformat(), screen_key)
                )
                self.db.commit()
                return json.loads(row["elements_json"])
        except Exception:
            pass
        return None

    def _cache_omni_result(self, screen_key: str, elements: List[Dict]) -> None:
        try:
            self.db.execute(
                """INSERT OR REPLACE INTO omni_parser_cache 
                   (screen_key, backend, elements_json, created_at, last_accessed_at, access_count)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (screen_key, self.omni_client.backend.value,
                 json.dumps(elements), datetime.now().isoformat(),
                 datetime.now().isoformat(), 1)
            )
            self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to cache OmniParser result: {e}")

    def cleanup_old_cache(self, ttl_days: int = 30) -> int:
        cutoff = (datetime.now() - timedelta(days=ttl_days)).isoformat()
        cursor = self.db.execute("DELETE FROM omni_parser_cache WHERE last_accessed_at < ?", (cutoff,))
        self.db.commit()
        return cursor.rowcount
