"""Screen tracking service for detecting unique and repeated screens."""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import imagehash
from PIL import Image

from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.screen_repository import Screen, ScreenRepository

logger = logging.getLogger(__name__)


@dataclass
class ScreenState:
    """Represents the current screen state with metadata."""
    screen_id: int
    composite_hash: str
    is_new: bool  # True if this screen was just discovered
    visit_count: int  # How many times we've seen this screen in this run
    total_screens_discovered: int  # Total unique screens in this run


class ScreenTracker:
    """Tracks screen states using perceptual hashing for deduplication.
    
    Uses imagehash library to generate perceptual hashes that are robust
    to minor visual differences (animations, time changes, etc.).
    
    The Hamming distance threshold of 5 allows for ~5% visual difference
    before screens are considered different.
    """

    # Maximum Hamming distance for screens to be considered the same
    SIMILARITY_THRESHOLD = 5

    def __init__(self, db_manager: DatabaseManager):
        """Initialize screen tracker.
        
        Args:
            db_manager: Database manager for persistence
        """
        self.db_manager = db_manager
        self.screen_repository = ScreenRepository(db_manager)
        
        # Track visit counts per screen ID for the current run
        self._visit_counts: dict[int, int] = {}
        
        # Track screens discovered in the current run
        self._run_screens: set[int] = set()
        
        # Current run ID
        self._current_run_id: Optional[int] = None
        
        # Previous screen ID for transition tracking
        self._previous_screen_id: Optional[int] = None

    def start_run(self, run_id: int) -> None:
        """Start tracking for a new run.
        
        Args:
            run_id: The run ID to track
        """
        self._current_run_id = run_id
        self._visit_counts.clear()
        self._run_screens.clear()
        self._previous_screen_id = None
        logger.info(f"Screen tracker started for run {run_id}")

    def end_run(self) -> None:
        """End tracking for the current run."""
        logger.info(
            f"Screen tracker ended for run {self._current_run_id}. "
            f"Discovered {len(self._run_screens)} unique screens."
        )
        self._current_run_id = None
        self._visit_counts.clear()
        self._run_screens.clear()
        self._previous_screen_id = None

    def process_screen(
        self,
        image: Image.Image,
        step_number: int,
        screenshot_path: Optional[str] = None,
        activity_name: Optional[str] = None
    ) -> ScreenState:
        """Process a screen capture and track its state.
        
        Args:
            image: PIL Image of the screenshot
            step_number: Current step number
            screenshot_path: Optional path to the saved screenshot
            activity_name: Optional Android activity name
            
        Returns:
            ScreenState with screen ID, novelty info, and visit count
        """
        if self._current_run_id is None:
            raise RuntimeError("Screen tracker not started. Call start_run() first.")
        
        # Generate perceptual hash
        composite_hash = self._generate_hash(image)
        logger.debug(f"Generated hash for step {step_number}: {composite_hash}")
        
        # Check for existing similar screen
        existing_screen = self._find_similar_screen(composite_hash)
        
        if existing_screen:
            # Existing screen - update visit count
            screen_id = existing_screen.id
            is_new = screen_id not in self._run_screens
            
            # Track this screen in the current run
            self._run_screens.add(screen_id)
            
            # Update visit count
            self._visit_counts[screen_id] = self._visit_counts.get(screen_id, 0) + 1
            
            logger.debug(
                f"Matched existing screen {screen_id} "
                f"(new to run: {is_new}, visits: {self._visit_counts[screen_id]})"
            )
        else:
            # New screen - create it
            screen = Screen(
                id=None,
                composite_hash=composite_hash,
                visual_hash=composite_hash,  # Use same hash for now
                screenshot_path=screenshot_path,
                activity_name=activity_name,
                first_seen_run_id=self._current_run_id,
                first_seen_step=step_number
            )
            screen_id = self.screen_repository.create_screen(screen)
            is_new = True
            
            # Track this screen
            self._run_screens.add(screen_id)
            self._visit_counts[screen_id] = 1
            
            logger.info(f"Discovered new screen {screen_id} at step {step_number}")
        
        # Track transition if we have a previous screen
        if self._previous_screen_id is not None and self._previous_screen_id != screen_id:
            self._record_transition(self._previous_screen_id, screen_id)
        
        # Update previous screen
        self._previous_screen_id = screen_id
        
        return ScreenState(
            screen_id=screen_id,
            composite_hash=composite_hash,
            is_new=is_new,
            visit_count=self._visit_counts[screen_id],
            total_screens_discovered=len(self._run_screens)
        )

    def _generate_hash(self, image: Image.Image) -> str:
        """Generate a perceptual hash for the image.
        
        Uses pHash (perceptual hash) which is robust to:
        - Scaling and aspect ratio changes
        - Minor color adjustments
        - Brightness changes
        - Small visual differences (time, animations)
        
        Args:
            image: PIL Image to hash
            
        Returns:
            Hex string representation of the perceptual hash
        """
        # Convert to RGB if necessary (imagehash works best with RGB)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Generate perceptual hash (pHash)
        # pHash uses DCT to identify similar images even with minor changes
        phash = imagehash.phash(image, hash_size=16)
        
        return str(phash)

    def _find_similar_screen(self, composite_hash: str) -> Optional[Screen]:
        """Find an existing screen with similar hash.
        
        Args:
            composite_hash: Hash to search for
            
        Returns:
            Matching Screen if found, None otherwise
        """
        # First try exact match (most common case)
        exact_match = self.screen_repository.get_screen_by_hash(composite_hash)
        if exact_match:
            return exact_match
        
        # Then try fuzzy match with Hamming distance
        similar_screens = self.screen_repository.find_similar_screens(
            composite_hash, 
            max_distance=self.SIMILARITY_THRESHOLD
        )
        
        if similar_screens:
            # Return the closest match
            closest_screen, distance = similar_screens[0]
            logger.debug(f"Found similar screen with distance {distance}")
            return closest_screen
        
        return None

    def _record_transition(self, from_screen_id: int, to_screen_id: int) -> None:
        """Record a screen transition.
        
        Args:
            from_screen_id: Source screen ID
            to_screen_id: Destination screen ID
        """
        if self._current_run_id is None:
            return
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Try to update existing transition count, or insert new one
        cursor.execute("""
            INSERT INTO transitions (run_id, from_screen_id, to_screen_id, action_type, count)
            VALUES (?, ?, ?, 'auto', 1)
            ON CONFLICT (run_id, from_screen_id, to_screen_id, action_type)
            DO UPDATE SET count = count + 1
        """, (self._current_run_id, from_screen_id, to_screen_id))
        
        conn.commit()
        logger.debug(f"Recorded transition: {from_screen_id} -> {to_screen_id}")

    def get_run_stats(self) -> dict:
        """Get current run statistics.
        
        Returns:
            Dictionary with screen tracking stats
        """
        return {
            "run_id": self._current_run_id,
            "unique_screens": len(self._run_screens),
            "total_visits": sum(self._visit_counts.values()),
            "most_visited_screen": max(
                self._visit_counts.items(), 
                key=lambda x: x[1],
                default=(None, 0)
            ),
        }

    def get_current_screen_id(self) -> Optional[int]:
        """Get the current screen ID.
        
        Returns:
            Current screen ID or None if not set
        """
        return self._previous_screen_id

    def get_visit_count(self, screen_id: int) -> int:
        """Get visit count for a specific screen in current run.
        
        Args:
            screen_id: Screen ID to check
            
        Returns:
            Number of visits to this screen
        """
        return self._visit_counts.get(screen_id, 0)

    def is_stuck(self, threshold: int = 3) -> Tuple[bool, Optional[str]]:
        """Detect if the crawler is stuck on the same screen.
        
        Args:
            threshold: Number of consecutive visits to consider stuck
            
        Returns:
            Tuple of (is_stuck, reason)
        """
        if self._previous_screen_id is None:
            return False, None
        
        visit_count = self._visit_counts.get(self._previous_screen_id, 0)
        
        if visit_count >= threshold:
            return True, f"Same screen visited {visit_count} times consecutively"
        
        return False, None
