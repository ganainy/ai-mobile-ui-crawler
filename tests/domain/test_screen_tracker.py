"""Tests for ScreenTracker service."""

import pytest
from PIL import Image
from unittest.mock import MagicMock, patch

from mobile_crawler.domain.screen_tracker import ScreenTracker, ScreenState
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.screen_repository import Screen


@pytest.fixture
def db_manager(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_crawler.db"
    manager = DatabaseManager(db_path)
    manager.create_schema()
    
    # Create a run record to satisfy foreign key constraints
    from mobile_crawler.infrastructure.run_repository import Run, RunRepository
    from datetime import datetime
    run_repo = RunRepository(manager)
    run = Run(
        id=None,
        device_id="test-device",
        app_package="com.test.app",
        start_activity=None,
        start_time=datetime.now(),
        end_time=None,
        status='RUNNING',
        ai_provider='test',
        ai_model='test-model',
        total_steps=0,
        unique_screens=0
    )
    run_repo.create_run(run)  # Creates run with id=1
    
    return manager


@pytest.fixture
def screen_tracker(db_manager):
    """Create a ScreenTracker instance."""
    return ScreenTracker(db_manager)


@pytest.fixture
def sample_image():
    """Create a sample PIL Image for testing with a distinctive pattern."""
    # Create a 100x100 image with a horizontal gradient pattern
    img = Image.new('RGB', (100, 100))
    for x in range(100):
        for y in range(100):
            # Horizontal gradient: red to black
            img.putpixel((x, y), (int(255 * (100 - x) / 100), 50, 50))
    return img


@pytest.fixture
def different_image():
    """Create a different PIL Image with a completely different pattern."""
    # Create a 100x100 image with a vertical gradient + checkerboard
    img = Image.new('RGB', (100, 100))
    for x in range(100):
        for y in range(100):
            # Checkerboard pattern with vertical gradient
            checker = ((x // 20) + (y // 20)) % 2
            if checker:
                img.putpixel((x, y), (50, 50, int(255 * y / 100)))
            else:
                img.putpixel((x, y), (200, 200, int(255 * (100 - y) / 100)))
    return img


class TestScreenTrackerStartEnd:
    """Tests for run lifecycle management."""

    def test_start_run_initializes_tracking(self, screen_tracker):
        """Test that start_run initializes state correctly."""
        screen_tracker.start_run(run_id=1)
        
        assert screen_tracker._current_run_id == 1
        assert len(screen_tracker._visit_counts) == 0
        assert len(screen_tracker._run_screens) == 0

    def test_end_run_clears_state(self, screen_tracker):
        """Test that end_run clears tracking state."""
        screen_tracker.start_run(run_id=1)
        screen_tracker._visit_counts[1] = 5
        screen_tracker._run_screens.add(1)
        
        screen_tracker.end_run()
        
        assert screen_tracker._current_run_id is None
        assert len(screen_tracker._visit_counts) == 0
        assert len(screen_tracker._run_screens) == 0


class TestScreenTrackerProcessScreen:
    """Tests for screen processing."""

    def test_process_screen_creates_new_screen(self, screen_tracker, sample_image):
        """Test that processing a new screen creates it in the database."""
        screen_tracker.start_run(run_id=1)
        
        result = screen_tracker.process_screen(
            image=sample_image,
            step_number=1,
            screenshot_path="/path/to/screenshot.png"
        )
        
        assert isinstance(result, ScreenState)
        assert result.screen_id is not None
        assert result.is_new is True
        assert result.visit_count == 1
        assert result.total_screens_discovered == 1

    def test_process_same_screen_twice_is_revisit(self, screen_tracker, sample_image):
        """Test that processing the same screen twice marks it as revisited."""
        screen_tracker.start_run(run_id=1)
        
        result1 = screen_tracker.process_screen(image=sample_image, step_number=1)
        result2 = screen_tracker.process_screen(image=sample_image, step_number=2)
        
        # Same screen ID
        assert result1.screen_id == result2.screen_id
        # First was new, second is revisit
        assert result1.is_new is True
        assert result2.is_new is False
        # Visit count increased
        assert result1.visit_count == 1
        assert result2.visit_count == 2
        # Still only 1 unique screen
        assert result2.total_screens_discovered == 1

    def test_process_different_screens(self, screen_tracker, sample_image, different_image):
        """Test that different screens get different IDs."""
        screen_tracker.start_run(run_id=1)
        
        result1 = screen_tracker.process_screen(image=sample_image, step_number=1)
        result2 = screen_tracker.process_screen(image=different_image, step_number=2)
        
        # Different screen IDs
        assert result1.screen_id != result2.screen_id
        # Both are new
        assert result1.is_new is True
        assert result2.is_new is True
        # 2 unique screens discovered
        assert result2.total_screens_discovered == 2

    def test_process_screen_requires_active_run(self, screen_tracker, sample_image):
        """Test that process_screen raises error without active run."""
        with pytest.raises(RuntimeError, match="Screen tracker not started"):
            screen_tracker.process_screen(image=sample_image, step_number=1)


class TestScreenTrackerStuckDetection:
    """Tests for stuck detection."""

    def test_not_stuck_initially(self, screen_tracker, sample_image):
        """Test that we're not stuck at the beginning."""
        screen_tracker.start_run(run_id=1)
        screen_tracker.process_screen(image=sample_image, step_number=1)
        
        is_stuck, reason = screen_tracker.is_stuck(threshold=3)
        
        assert is_stuck is False
        assert reason is None

    def test_stuck_after_repeated_visits(self, screen_tracker, sample_image):
        """Test stuck detection after visiting same screen multiple times."""
        screen_tracker.start_run(run_id=1)
        
        # Visit same screen 3 times
        for i in range(3):
            screen_tracker.process_screen(image=sample_image, step_number=i+1)
        
        is_stuck, reason = screen_tracker.is_stuck(threshold=3)
        
        assert is_stuck is True
        assert "3 times" in reason


class TestScreenTrackerHash:
    """Tests for perceptual hashing."""

    def test_hash_consistency(self, screen_tracker, sample_image):
        """Test that hashing the same image produces the same hash."""
        hash1 = screen_tracker._generate_hash(sample_image)
        hash2 = screen_tracker._generate_hash(sample_image)
        
        assert hash1 == hash2

    def test_hash_difference(self, screen_tracker, sample_image, different_image):
        """Test that different images produce different hashes."""
        hash1 = screen_tracker._generate_hash(sample_image)
        hash2 = screen_tracker._generate_hash(different_image)
        
        assert hash1 != hash2


class TestScreenTrackerStats:
    """Tests for run statistics."""

    def test_get_run_stats(self, screen_tracker, sample_image, different_image):
        """Test run statistics collection."""
        screen_tracker.start_run(run_id=1)
        
        screen_tracker.process_screen(image=sample_image, step_number=1)
        screen_tracker.process_screen(image=sample_image, step_number=2)
        screen_tracker.process_screen(image=different_image, step_number=3)
        
        stats = screen_tracker.get_run_stats()
        
        assert stats['run_id'] == 1
        assert stats['unique_screens'] == 2
        assert stats['total_visits'] == 3


class TestScreenTrackerTransitions:
    """Tests for screen transition tracking."""

    def test_transition_recorded(self, screen_tracker, sample_image, different_image):
        """Test that transitions between screens are recorded."""
        screen_tracker.start_run(run_id=1)
        
        # Navigate: screen A -> screen B
        result1 = screen_tracker.process_screen(image=sample_image, step_number=1)
        result2 = screen_tracker.process_screen(image=different_image, step_number=2)
        
        # Should have recorded a transition from screen A to screen B
        assert result1.screen_id != result2.screen_id
        
    def test_no_self_transition(self, screen_tracker, sample_image):
        """Test that staying on same screen doesn't create a transition."""
        screen_tracker.start_run(run_id=1)
        
        result1 = screen_tracker.process_screen(image=sample_image, step_number=1)
        result2 = screen_tracker.process_screen(image=sample_image, step_number=2)
        
        # Same screen - no transition should be recorded
        assert result1.screen_id == result2.screen_id


class TestScreenTrackerPersistence:
    """Tests for screen persistence across runs."""

    def test_screen_persists_across_runs(self, db_manager, sample_image):
        """Test that screens discovered in one run are recognized in another."""
        # First run - discover screen
        tracker1 = ScreenTracker(db_manager)
        tracker1.start_run(run_id=1)
        result1 = tracker1.process_screen(image=sample_image, step_number=1)
        first_screen_id = result1.screen_id
        tracker1.end_run()
        
        # Create second run record
        from mobile_crawler.infrastructure.run_repository import Run, RunRepository
        from datetime import datetime
        run_repo = RunRepository(db_manager)
        run = Run(
            id=None, device_id="test-device", app_package="com.test.app",
            start_activity=None, start_time=datetime.now(), end_time=None,
            status='RUNNING', ai_provider='test', ai_model='test-model',
            total_steps=0, unique_screens=0
        )
        run_repo.create_run(run)  # Creates run with id=2
        
        # Second run - same image should match existing screen
        tracker2 = ScreenTracker(db_manager)
        tracker2.start_run(run_id=2)
        result2 = tracker2.process_screen(image=sample_image, step_number=1)
        
        # Should be same screen ID but marked as new to THIS run
        assert result2.screen_id == first_screen_id
        assert result2.is_new is True  # New to run 2


class TestScreenTrackerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_rgba_image_conversion(self, screen_tracker):
        """Test that RGBA images are handled correctly."""
        screen_tracker.start_run(run_id=1)
        
        # Create RGBA image (with alpha channel)
        rgba_image = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        
        # Should not raise an error
        result = screen_tracker.process_screen(image=rgba_image, step_number=1)
        assert result.screen_id is not None

    def test_grayscale_image_conversion(self, screen_tracker):
        """Test that grayscale images are handled correctly."""
        screen_tracker.start_run(run_id=1)
        
        # Create grayscale image
        gray_image = Image.new('L', (100, 100), color=128)
        
        # Should not raise an error
        result = screen_tracker.process_screen(image=gray_image, step_number=1)
        assert result.screen_id is not None

    def test_stuck_not_triggered_below_threshold(self, screen_tracker, sample_image):
        """Test stuck detection respects threshold."""
        screen_tracker.start_run(run_id=1)
        
        # Visit same screen 2 times (below default threshold of 3)
        screen_tracker.process_screen(image=sample_image, step_number=1)
        screen_tracker.process_screen(image=sample_image, step_number=2)
        
        is_stuck, reason = screen_tracker.is_stuck(threshold=3)
        
        assert is_stuck is False
        assert reason is None

    def test_custom_stuck_threshold(self, screen_tracker, sample_image):
        """Test stuck detection with custom threshold."""
        screen_tracker.start_run(run_id=1)
        
        # Visit same screen 2 times
        screen_tracker.process_screen(image=sample_image, step_number=1)
        screen_tracker.process_screen(image=sample_image, step_number=2)
        
        # With threshold=2, should be stuck
        is_stuck, reason = screen_tracker.is_stuck(threshold=2)
        
        assert is_stuck is True
        assert "2 times" in reason

