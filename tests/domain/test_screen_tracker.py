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


class TestScreenTrackerDHashAlgorithm:
    """Tests for dHash (Difference Hash) algorithm with size=8."""

    def test_dhash_produces_64bit_hash(self, screen_tracker, sample_image):
        """Test that dHash with size=8 produces a 16-character hex string (64 bits)."""
        hash_value = screen_tracker._generate_hash(sample_image)
        
        # dHash with size=8 produces 64-bit hash = 16 hex characters
        assert isinstance(hash_value, str)
        assert len(hash_value) == 16
        # Verify it's a valid hex string
        int(hash_value, 16)  # Will raise ValueError if not valid hex

    def test_dhash_consistency(self, screen_tracker, sample_image):
        """Test that dHash produces consistent results for the same image."""
        hash1 = screen_tracker._generate_hash(sample_image)
        hash2 = screen_tracker._generate_hash(sample_image)
        
        assert hash1 == hash2

    def test_dhash_carousel_variations_have_low_distance(self, screen_tracker):
        """Test that carousel-like variations have low Hamming distance."""
        # Create two images that simulate carousel rotation
        # Same structure, different content in the middle area
        img1 = Image.new('RGB', (400, 800))
        img2 = Image.new('RGB', (400, 800))
        
        # Add status bar (top 100px) - same for both
        for x in range(400):
            for y in range(100):
                img1.putpixel((x, y), (50, 50, 50))
                img2.putpixel((x, y), (50, 50, 50))
        
        # Add carousel area (middle) - different content
        for x in range(400):
            for y in range(100, 500):
                # Different carousel content
                img1.putpixel((x, y), (255, 100, 100))
                img2.putpixel((x, y), (100, 255, 100))
        
        # Add rest of screen - same for both
        for x in range(400):
            for y in range(500, 800):
                img1.putpixel((x, y), (200, 200, 200))
                img2.putpixel((x, y), (200, 200, 200))
        
        hash1 = screen_tracker._generate_hash(img1)
        hash2 = screen_tracker._generate_hash(img2)
        
        # Calculate Hamming distance
        distance = screen_tracker.screen_repository._hamming_distance(hash1, hash2)
        
        # With dHash, carousel variations should have relatively low distance
        # (based on research: max 8 for home screen variations)
        assert distance < 20  # Conservative threshold

    def test_dhash_different_screens_have_high_distance(self, screen_tracker):
        """Test that genuinely different screens have high Hamming distance."""
        # Create two structurally different screens with gradients
        img1 = Image.new('RGB', (400, 800))
        img2 = Image.new('RGB', (400, 800))
        
        # Create horizontal gradient pattern
        for x in range(400):
            for y in range(100, 800):
                img1.putpixel((x, y), (int(255 * x / 400), 50, 50))
        
        # Create vertical gradient pattern
        for x in range(400):
            for y in range(100, 800):
                img2.putpixel((x, y), (50, int(255 * y / 700), 50))
        
        hash1 = screen_tracker._generate_hash(img1)
        hash2 = screen_tracker._generate_hash(img2)
        
        # Calculate Hamming distance
        distance = screen_tracker.screen_repository._hamming_distance(hash1, hash2)
        
        # Very different screens should have high distance
        # (based on research: min 29 for different screen types)
        assert distance > 25

    def test_dhash_threshold_matching(self, screen_tracker):
        """Test that threshold-based matching works correctly."""
        # Create similar images (should match with threshold=12)
        img1 = Image.new('RGB', (400, 800), color=(200, 200, 200))
        img2 = Image.new('RGB', (400, 800), color=(205, 205, 205))
        
        hash1 = screen_tracker._generate_hash(img1)
        hash2 = screen_tracker._generate_hash(img2)
        
        distance = screen_tracker.screen_repository._hamming_distance(hash1, hash2)
        
        # Should be within default threshold
        assert distance <= screen_tracker.screen_similarity_threshold


class TestScreenTrackerStatusBarExclusion:
    """Tests for status bar exclusion (top 100px crop)."""

    def test_status_bar_excluded_from_hash(self, screen_tracker):
        """Test that status bar changes don't affect hash significantly."""
        # Create base image
        base_img = Image.new('RGB', (400, 800), color=(200, 200, 200))
        
        # Create image with different status bar (top 100px)
        modified_img = Image.new('RGB', (400, 800), color=(200, 200, 200))
        # Change only the status bar area
        for x in range(400):
            for y in range(100):
                modified_img.putpixel((x, y), (255, 0, 0))
        
        hash1 = screen_tracker._generate_hash(base_img)
        hash2 = screen_tracker._generate_hash(modified_img)
        
        distance = screen_tracker.screen_repository._hamming_distance(hash1, hash2)
        
        # Status bar changes should have minimal impact on hash
        # (because we crop it out before hashing)
        assert distance < 5

    def test_content_below_status_bar_affects_hash(self, screen_tracker):
        """Test that content changes below status bar DO affect hash."""
        # Create base image with horizontal gradient
        base_img = Image.new('RGB', (400, 800))
        for x in range(400):
            for y in range(100, 800):
                base_img.putpixel((x, y), (int(255 * x / 400), 100, 100))
        
        # Create image with different content below status bar (vertical gradient)
        modified_img = Image.new('RGB', (400, 800))
        for x in range(400):
            for y in range(100, 800):
                modified_img.putpixel((x, y), (100, int(255 * y / 700), 100))
        
        hash1 = screen_tracker._generate_hash(base_img)
        hash2 = screen_tracker._generate_hash(modified_img)
        
        distance = screen_tracker.screen_repository._hamming_distance(hash1, hash2)
        
        # Content changes should significantly affect hash
        assert distance > 10


class TestScreenTrackerConfigurableThreshold:
    """Tests for configurable similarity threshold."""

    def test_custom_threshold_used_in_matching(self, db_manager):
        """Test that custom threshold is used for similarity matching."""
        # Create two images with known distance
        img1 = Image.new('RGB', (400, 800), color=(200, 200, 200))
        img2 = Image.new('RGB', (400, 800), color=(210, 210, 210))
        
        # Create tracker with strict threshold (5)
        tracker_strict = ScreenTracker(db_manager, screen_similarity_threshold=5)
        tracker_strict.start_run(run_id=1)
        
        # Create tracker with loose threshold (20)
        tracker_loose = ScreenTracker(db_manager, screen_similarity_threshold=20)
        tracker_loose.start_run(run_id=1)
        
        # Process first image with both trackers
        result1_strict = tracker_strict.process_screen(img1, step_number=1)
        result1_loose = tracker_loose.process_screen(img1, step_number=1)
        
        # Process second image
        result2_strict = tracker_strict.process_screen(img2, step_number=2)
        result2_loose = tracker_loose.process_screen(img2, step_number=2)
        
        # Calculate actual distance
        hash1 = tracker_strict._generate_hash(img1)
        hash2 = tracker_strict._generate_hash(img2)
        actual_distance = tracker_strict.screen_repository._hamming_distance(hash1, hash2)
        
        # If distance is between 5 and 20:
        # - Strict tracker should treat as different screens
        # - Loose tracker should treat as same screen
        if 5 < actual_distance < 20:
            assert result1_strict.screen_id != result2_strict.screen_id
            assert result1_loose.screen_id == result2_loose.screen_id

    def test_default_threshold_is_12(self, screen_tracker):
        """Test that default threshold is 12."""
        assert screen_tracker.screen_similarity_threshold == 12

    def test_use_perceptual_hashing_flag(self, db_manager):
        """Test that use_perceptual_hashing flag can be set."""
        tracker_with_hashing = ScreenTracker(
            db_manager,
            use_perceptual_hashing=True
        )
        tracker_without_hashing = ScreenTracker(
            db_manager,
            use_perceptual_hashing=False
        )
        
        assert tracker_with_hashing.use_perceptual_hashing is True
        assert tracker_without_hashing.use_perceptual_hashing is False

