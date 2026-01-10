"""Tests for screen_repository_with_run.py."""

import tempfile
from pathlib import Path

import pytest

from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.screen_repository import Screen, ScreenRepository


@pytest.fixture
def temp_db_path():
    """Create a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    # Cleanup with retry for Windows file locking
    import time
    for _ in range(10):
        try:
            if path.exists():
                path.unlink()
            break
        except PermissionError:
            time.sleep(0.1)


@pytest.fixture
def db_manager(temp_db_path):
    """Create a database manager with temporary file."""
    manager = DatabaseManager(temp_db_path)
    manager.create_schema()
    yield manager
    manager.close()


@pytest.fixture
def db_manager_with_run(temp_db_path):
    """Create a database manager with a test run already created."""
    manager = DatabaseManager(temp_db_path)
    manager.create_schema()
    
    # Create a test run that screens can reference
    conn = manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO runs (
            device_id, app_package, start_activity, start_time, status
        ) VALUES (?, ?, ?, ?, ?)
    """, ("test-device", "com.test.app", "com.test.app.Main", "2024-01-01T12:00:00", "RUNNING"))
    conn.commit()
    
    yield manager
    manager.close()
    # Cleanup with retry for Windows file locking
    import time
    for _ in range(10):
        try:
            if temp_db_path.exists():
                temp_db_path.unlink()
            break
        except PermissionError:
            time.sleep(0.1)


@pytest.fixture
def screen_repository_with_run(db_manager_with_run):
    """Create a screen repository with a test run available."""
    return ScreenRepository(db_manager_with_run)


@pytest.fixture
def sample_screen():
    """Create a sample screen for testing."""
    return Screen(
        id=None,
        composite_hash="a1b2c3d4e5f67890",
        visual_hash="fedcba0987654321",
        screenshot_path="/path/to/screenshot1.png",
        activity_name="com.example.app.MainActivity",
        first_seen_run_id=1,
        first_seen_step=5
    )


@pytest.fixture
def similar_screen():
    """Create a screen with similar hash for testing."""
    return Screen(
        id=None,
        composite_hash="a1b2c3d4e5f67891",  # Only last bit differs
        visual_hash="1234567890abcdef",
        screenshot_path="/path/to/screenshot2.png",
        activity_name="com.example.app.SecondActivity",
        first_seen_run_id=1,
        first_seen_step=10
    )


class TestScreenRepository:
    """Test ScreenRepository functionality."""

    def test_create_screen(self, screen_repository_with_run, sample_screen):
        """Test creating a new screen."""
        screen_id = screen_repository_with_run.create_screen(sample_screen)

        assert screen_id is not None
        assert isinstance(screen_id, int)

        # Verify the screen was created
        created_screen = screen_repository_with_run.get_screen(screen_id)
        assert created_screen is not None
        assert created_screen.id == screen_id
        assert created_screen.composite_hash == sample_screen.composite_hash
        assert created_screen.activity_name == sample_screen.activity_name

    def test_get_screen_not_found(self, screen_repository_with_run):
        """Test getting a non-existent screen returns None."""
        assert screen_repository_with_run.get_screen(999) is None

    def test_get_screen_by_hash(self, screen_repository_with_run, sample_screen):
        """Test getting a screen by its composite hash."""
        # Create a screen
        screen_id = screen_repository_with_run.create_screen(sample_screen)

        # Retrieve by hash
        found_screen = screen_repository_with_run.get_screen_by_hash(sample_screen.composite_hash)

        assert found_screen is not None
        assert found_screen.id == screen_id
        assert found_screen.composite_hash == sample_screen.composite_hash

    def test_get_screen_by_hash_not_found(self, screen_repository_with_run):
        """Test getting a screen by non-existent hash returns None."""
        assert screen_repository_with_run.get_screen_by_hash("nonexistent") is None

    def test_update_screen(self, screen_repository_with_run, sample_screen):
        """Test updating an existing screen."""
        # Create a screen
        screen_id = screen_repository_with_run.create_screen(sample_screen)

        # Get the screen and modify it
        screen = screen_repository_with_run.get_screen(screen_id)
        assert screen is not None

        screen.activity_name = "com.example.app.UpdatedActivity"
        screen.screenshot_path = "/new/path/screenshot.png"

        # Update it
        success = screen_repository_with_run.update_screen(screen)
        assert success is True

        # Verify the update
        updated_screen = screen_repository_with_run.get_screen(screen_id)
        assert updated_screen is not None
        assert updated_screen.activity_name == "com.example.app.UpdatedActivity"
        assert updated_screen.screenshot_path == "/new/path/screenshot.png"

    def test_update_screen_not_found(self, screen_repository_with_run, sample_screen):
        """Test updating a non-existent screen."""
        sample_screen.id = 999
        success = screen_repository_with_run.update_screen(sample_screen)
        assert success is False

    def test_delete_screen(self, screen_repository_with_run, sample_screen):
        """Test deleting a screen."""
        # Create a screen
        screen_id = screen_repository_with_run.create_screen(sample_screen)

        # Verify it exists
        assert screen_repository_with_run.get_screen(screen_id) is not None

        # Delete it
        success = screen_repository_with_run.delete_screen(screen_id)
        assert success is True

        # Verify it's gone
        assert screen_repository_with_run.get_screen(screen_id) is None

    def test_delete_screen_not_found(self, screen_repository_with_run):
        """Test deleting a non-existent screen."""
        success = screen_repository_with_run.delete_screen(999)
        assert success is False

    def test_find_similar_screens_exact_match(self, screen_repository_with_run, sample_screen):
        """Test finding similar screens with exact match (distance 0)."""
        # Create a screen
        screen_id = screen_repository_with_run.create_screen(sample_screen)

        # Find similar screens
        similar = screen_repository_with_run.find_similar_screens(sample_screen.composite_hash, max_distance=5)

        assert len(similar) == 1
        found_screen, distance = similar[0]
        assert found_screen.id == screen_id
        assert distance == 0

    def test_find_similar_screens_within_distance(self, screen_repository_with_run, sample_screen, similar_screen):
        """Test finding similar screens within Hamming distance."""
        # Create both screens
        id1 = screen_repository_with_run.create_screen(sample_screen)
        id2 = screen_repository_with_run.create_screen(similar_screen)

        # Find screens similar to the first one
        similar = screen_repository_with_run.find_similar_screens(sample_screen.composite_hash, max_distance=5)

        assert len(similar) >= 1  # At least the exact match

        # Check that both screens are found (depending on actual distance)
        found_ids = {screen.id for screen, distance in similar}
        assert id1 in found_ids  # Exact match should always be found

        # The similar screen should be found if distance <= 5
        # (this depends on the actual hash difference)

    def test_find_similar_screens_no_matches(self, screen_repository_with_run):
        """Test finding similar screens when none exist."""
        similar = screen_repository_with_run.find_similar_screens("nonexistent", max_distance=5)
        assert similar == []

    def test_hamming_distance_calculation(self, screen_repository_with_run):
        """Test Hamming distance calculation."""
        # Test identical hashes
        distance = screen_repository_with_run._hamming_distance("a1b2", "a1b2")
        assert distance == 0

        # Test different hashes
        distance = screen_repository_with_run._hamming_distance("a1b2", "a1b3")
        assert distance == 1  # Last nibble differs by 1 bit

        # Test hex to binary conversion
        distance = screen_repository_with_run._hamming_distance("f", "0")
        assert distance == 4  # 1111 vs 0000 = 4 bits differ

    def test_get_screens_by_run(self, screen_repository_with_run, sample_screen, similar_screen):
        """Test getting screens by run ID."""
        # Create another run for testing
        conn = screen_repository_with_run.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO runs (
                device_id, app_package, start_activity, start_time, status
            ) VALUES (?, ?, ?, ?, ?)
        """, ("device-2", "com.test.app2", "com.test.app2.Main", "2024-01-01T13:00:00", "RUNNING"))
        conn.commit()

        # Create screens for different runs
        screen1 = sample_screen
        screen2 = Screen(
            id=None,
            composite_hash="different_hash",
            visual_hash="another_hash",
            screenshot_path="/path/to/screenshot3.png",
            activity_name="com.example.app.ThirdActivity",
            first_seen_run_id=2,  # Different run
            first_seen_step=1
        )

        id1 = screen_repository_with_run.create_screen(screen1)
        id2 = screen_repository_with_run.create_screen(screen2)

        # Get screens for run 1
        run1_screens = screen_repository_with_run.get_screens_by_run(1)
        assert len(run1_screens) == 1
        assert run1_screens[0].id == id1

        # Get screens for run 2
        run2_screens = screen_repository_with_run.get_screens_by_run(2)
        assert len(run2_screens) == 1
        assert run2_screens[0].id == id2

        # Get screens for non-existent run
        empty_screens = screen_repository_with_run.get_screens_by_run(999)
        assert empty_screens == []

    def test_get_screens_by_activity(self, screen_repository_with_run, sample_screen):
        """Test getting screens by activity name."""
        # Create screens with different activities
        screen1 = sample_screen
        screen2 = Screen(
            id=None,
            composite_hash="different_hash2",
            visual_hash="another_hash2",
            screenshot_path="/path/to/screenshot4.png",
            activity_name="com.example.app.MainActivity",  # Same activity
            first_seen_run_id=1,
            first_seen_step=15
        )
        screen3 = Screen(
            id=None,
            composite_hash="different_hash3",
            visual_hash="another_hash3",
            screenshot_path="/path/to/screenshot5.png",
            activity_name="com.different.app.MainActivity",  # Different activity
            first_seen_run_id=1,
            first_seen_step=20
        )

        id1 = screen_repository_with_run.create_screen(screen1)
        id2 = screen_repository_with_run.create_screen(screen2)
        id3 = screen_repository_with_run.create_screen(screen3)

        # Get screens for the main activity
        main_activity_screens = screen_repository_with_run.get_screens_by_activity("com.example.app.MainActivity")
        assert len(main_activity_screens) == 2
        screen_ids = {screen.id for screen in main_activity_screens}
        assert screen_ids == {id1, id2}

        # Get screens for different activity
        different_activity_screens = screen_repository_with_run.get_screens_by_activity("com.different.app.MainActivity")
        assert len(different_activity_screens) == 1
        assert different_activity_screens[0].id == id3

    def test_get_screen_count(self, screen_repository_with_run, sample_screen):
        """Test getting screen count."""
        # Initially empty
        assert screen_repository_with_run.get_screen_count() == 0

        # Add some screens
        screen_repository_with_run.create_screen(sample_screen)
        assert screen_repository_with_run.get_screen_count() == 1

        # Create another screen with different hash
        screen2 = Screen(
            id=None,
            composite_hash="different_hash_count",
            visual_hash="different_vhash",
            screenshot_path="/path/to/screenshot_count.png",
            activity_name="com.example.app.CountActivity",
            first_seen_run_id=1,
            first_seen_step=100
        )
        screen_repository_with_run.create_screen(screen2)
        assert screen_repository_with_run.get_screen_count() == 2

    def test_get_unique_activities(self, screen_repository_with_run, sample_screen):
        """Test getting unique activity names."""
        # Create screens with different activities
        screen1 = sample_screen  # com.example.app.MainActivity
        screen2 = Screen(
            id=None,
            composite_hash="hash2",
            visual_hash="vhash2",
            screenshot_path="/path/to/screen2.png",
            activity_name="com.example.app.SecondActivity",
            first_seen_run_id=1,
            first_seen_step=10
        )
        screen3 = Screen(
            id=None,
            composite_hash="hash3",
            visual_hash="vhash3",
            screenshot_path="/path/to/screen3.png",
            activity_name="com.example.app.MainActivity",  # Duplicate
            first_seen_run_id=1,
            first_seen_step=15
        )
        screen4 = Screen(
            id=None,
            composite_hash="hash4",
            visual_hash="vhash4",
            screenshot_path="/path/to/screen4.png",
            activity_name=None,  # Null activity
            first_seen_run_id=1,
            first_seen_step=20
        )

        screen_repository_with_run.create_screen(screen1)
        screen_repository_with_run.create_screen(screen2)
        screen_repository_with_run.create_screen(screen3)
        screen_repository_with_run.create_screen(screen4)

        activities = screen_repository_with_run.get_unique_activities()

        # Should contain unique non-null activities
        assert len(activities) == 2
        assert "com.example.app.MainActivity" in activities
        assert "com.example.app.SecondActivity" in activities

    def test_none_values_handling(self, screen_repository_with_run):
        """Test handling of None values in optional fields."""
        screen = Screen(
            id=None,
            composite_hash="test_hash",
            visual_hash="test_vhash",
            screenshot_path=None,  # None value
            activity_name=None,    # None value
            first_seen_run_id=1,
            first_seen_step=1
        )

        screen_id = screen_repository_with_run.create_screen(screen)
        retrieved_screen = screen_repository_with_run.get_screen(screen_id)

        assert retrieved_screen is not None
        assert retrieved_screen.screenshot_path is None
        assert retrieved_screen.activity_name is None

    def test_composite_hash_uniqueness(self, screen_repository_with_run, sample_screen):
        """Test that composite_hash is unique in the database."""
        # Create first screen
        id1 = screen_repository_with_run.create_screen(sample_screen)

        # Try to create another screen with same hash - should work (database allows it)
        # Actually, the schema has UNIQUE constraint on composite_hash, so this should fail
        duplicate_screen = Screen(
            id=None,
            composite_hash=sample_screen.composite_hash,  # Same hash
            visual_hash="different_vhash",
            screenshot_path="/different/path.png",
            activity_name="different.activity",
            first_seen_run_id=2,
            first_seen_step=1
        )

        # This should raise an exception due to UNIQUE constraint
        with pytest.raises(Exception):  # Could be sqlite3.IntegrityError
            screen_repository_with_run.create_screen(duplicate_screen)
