"""Repository for managing discovered screens in crawler.db."""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from mobile_crawler.infrastructure.database import DatabaseManager


@dataclass
class Screen:
    """Data class representing a discovered screen state."""
    id: Optional[int]
    composite_hash: str  # Perceptual hash for similarity comparison
    visual_hash: str     # Alternative hash (e.g., for exact matching)
    screenshot_path: Optional[str]
    activity_name: Optional[str]
    first_seen_run_id: int
    first_seen_step: int


class ScreenRepository:
    """Repository for CRUD operations on screens table with perceptual hashing."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository with database manager.

        Args:
            db_manager: DatabaseManager instance for crawler.db
        """
        self.db_manager = db_manager

    def create_screen(self, screen: Screen) -> int:
        """Create a new screen and return its ID.

        Args:
            screen: Screen object (id will be ignored)

        Returns:
            The ID of the newly created screen
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO screens (
                composite_hash, visual_hash, screenshot_path, activity_name,
                first_seen_run_id, first_seen_step
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            screen.composite_hash,
            screen.visual_hash,
            screen.screenshot_path,
            screen.activity_name,
            screen.first_seen_run_id,
            screen.first_seen_step
        ))

        screen_id = cursor.lastrowid
        conn.commit()
        return screen_id

    def get_screen(self, screen_id: int) -> Optional[Screen]:
        """Get a screen by ID.

        Args:
            screen_id: The screen ID to retrieve

        Returns:
            Screen object if found, None otherwise
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM screens WHERE id = ?", (screen_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_screen(row)

    def get_screen_by_hash(self, composite_hash: str) -> Optional[Screen]:
        """Get a screen by its composite hash.

        Args:
            composite_hash: The composite hash to search for

        Returns:
            Screen object if found, None otherwise
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM screens WHERE composite_hash = ?", (composite_hash,))
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_screen(row)

    def get_screens_by_run(self, run_id: int) -> List[Screen]:
        """Get all screens discovered in a specific run.

        Args:
            run_id: The run ID to get screens for

        Returns:
            List of Screen objects discovered in the run
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        # Get screens that were first seen in this run
        # OR screens that were visited in step_logs for this run
        cursor.execute("""
            SELECT DISTINCT s.* FROM screens s
            LEFT JOIN step_logs sl ON (sl.to_screen_id = s.id OR sl.from_screen_id = s.id)
            WHERE s.first_seen_run_id = ? OR sl.run_id = ?
            ORDER BY s.id
        """, (run_id, run_id))

        screens = []
        for row in cursor.fetchall():
            screens.append(self._row_to_screen(row))

        return screens

    def update_screen(self, screen: Screen) -> bool:
        """Update an existing screen.

        Args:
            screen: Screen object with updated values (must have valid id)

        Returns:
            True if screen was updated, False if not found
        """
        if screen.id is None:
            return False

        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE screens SET
                composite_hash = ?, visual_hash = ?, screenshot_path = ?,
                activity_name = ?, first_seen_run_id = ?, first_seen_step = ?
            WHERE id = ?
        """, (
            screen.composite_hash,
            screen.visual_hash,
            screen.screenshot_path,
            screen.activity_name,
            screen.first_seen_run_id,
            screen.first_seen_step,
            screen.id
        ))

        updated = cursor.rowcount > 0
        conn.commit()
        return updated

    def delete_screen(self, screen_id: int) -> bool:
        """Delete a screen.

        Note: This may affect step_logs and transitions that reference this screen.
        Use with caution - consider the foreign key constraints.

        Args:
            screen_id: The screen ID to delete

        Returns:
            True if screen was deleted, False if not found
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM screens WHERE id = ?", (screen_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted

    def find_similar_screens(self, composite_hash: str, max_distance: int = 5) -> List[Tuple[Screen, int]]:
        """Find screens similar to the given hash using Hamming distance.

        Args:
            composite_hash: The hash to compare against
            max_distance: Maximum Hamming distance (default 5 as per spec)

        Returns:
            List of (Screen, distance) tuples for screens within max_distance
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        # Get all screens - for a real implementation, you might want to optimize this
        # with database functions or pre-computed indexes, but for simplicity we'll
        # calculate distances in Python
        cursor.execute("SELECT * FROM screens")
        rows = cursor.fetchall()

        similar_screens = []
        for row in rows:
            existing_hash = row["composite_hash"]
            distance = self._hamming_distance(composite_hash, existing_hash)

            if distance <= max_distance:
                screen = self._row_to_screen(row)
                similar_screens.append((screen, distance))

        # Sort by distance (closest first)
        similar_screens.sort(key=lambda x: x[1])
        return similar_screens

    def get_screens_by_run(self, run_id: int) -> List[Screen]:
        """Get all screens first discovered in a specific run.

        Args:
            run_id: The run ID to filter by

        Returns:
            List of screens first seen in the specified run
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM screens WHERE first_seen_run_id = ? ORDER BY first_seen_step",
            (run_id,)
        )
        rows = cursor.fetchall()

        return [self._row_to_screen(row) for row in rows]

    def get_screens_by_activity(self, activity_name: str) -> List[Screen]:
        """Get all screens with a specific activity name.

        Args:
            activity_name: The activity name to filter by

        Returns:
            List of screens with the specified activity
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM screens WHERE activity_name = ? ORDER BY first_seen_run_id, first_seen_step",
            (activity_name,)
        )
        rows = cursor.fetchall()

        return [self._row_to_screen(row) for row in rows]

    def get_screen_count(self) -> int:
        """Get total number of screens in the database.

        Returns:
            Total count of screens
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM screens")
        return cursor.fetchone()[0]

    def get_unique_activities(self) -> List[str]:
        """Get list of unique activity names.

        Returns:
            List of unique activity names (non-null)
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT activity_name FROM screens
            WHERE activity_name IS NOT NULL
            ORDER BY activity_name
        """)
        rows = cursor.fetchall()

        return [row["activity_name"] for row in rows]

    def _hamming_distance(self, hash1: str, hash2: str) -> int:
        """Calculate Hamming distance between two hashes.

        Args:
            hash1: First hash string
            hash2: Second hash string

        Returns:
            Hamming distance (number of differing bits)
        """
        # Convert hex strings to binary for comparison
        # Assuming hashes are hexadecimal strings
        try:
            bin1 = bin(int(hash1, 16))[2:].zfill(len(hash1) * 4)
            bin2 = bin(int(hash2, 16))[2:].zfill(len(hash2) * 4)
        except ValueError:
            # If conversion fails, fall back to string comparison
            # This handles cases where hashes might not be pure hex
            return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))

        # Ensure both binary strings are the same length
        max_len = max(len(bin1), len(bin2))
        bin1 = bin1.zfill(max_len)
        bin2 = bin2.zfill(max_len)

        return sum(b1 != b2 for b1, b2 in zip(bin1, bin2))

    def _row_to_screen(self, row) -> Screen:
        """Convert a database row to a Screen object.

        Args:
            row: SQLite Row object

        Returns:
            Screen object
        """
        return Screen(
            id=row["id"],
            composite_hash=row["composite_hash"],
            visual_hash=row["visual_hash"],
            screenshot_path=row["screenshot_path"],
            activity_name=row["activity_name"],
            first_seen_run_id=row["first_seen_run_id"],
            first_seen_step=row["first_seen_step"]
        )

    def count_unique_screens_for_run(self, run_id: int) -> int:
        """Count unique screens discovered in a specific run."""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(DISTINCT id) 
            FROM screens 
            WHERE first_seen_run_id = ?
        """, (run_id,))
        
        row = cursor.fetchone()
        return row[0] if row else 0

    def get_latest_screen_for_run(self, run_id: int) -> Optional[Screen]:
        """Get the most recently discovered screen for a run."""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM screens 
            WHERE first_seen_run_id = ? 
            ORDER BY first_seen_step DESC 
            LIMIT 1
        """, (run_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return self._row_to_screen(row)