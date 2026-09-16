"""Tests for screen_hash shared utilities."""

import pytest
from PIL import Image

from mobile_crawler.domain.screen_hash import (
    HAMMING_THRESHOLD,
    STATUS_BAR_HEIGHT,
    compute_screen_hash,
    hamming_distance,
    is_screen_stable,
)


class TestComputeScreenHash:
    def test_returns_hex_string(self):
        """Hash is a 16-char hex string (64-bit dHash)."""
        img = Image.new("RGB", (1080, 1920), color="blue")
        result = compute_screen_hash(img)
        assert isinstance(result, str)
        assert len(result) == 16
        int(result, 16)  # raises if not valid hex

    def test_same_image_same_hash(self):
        """Identical images produce identical hashes."""
        img = Image.new("RGB", (1080, 1920), color="red")
        assert compute_screen_hash(img) == compute_screen_hash(img)

    def test_different_images_different_hash(self):
        """Images with different structure produce different hashes."""
        from PIL import ImageDraw

        img1 = Image.new("RGB", (1080, 1920), color="white")
        img2 = Image.new("RGB", (1080, 1920), color="white")
        draw1 = ImageDraw.Draw(img1)
        draw2 = ImageDraw.Draw(img2)
        # Draw different shapes in the content area (below status bar)
        draw1.rectangle([100, 200, 400, 500], fill="red")
        draw2.rectangle([600, 800, 900, 1100], fill="blue")
        assert compute_screen_hash(img1) != compute_screen_hash(img2)

    def test_status_bar_cropped(self):
        """Status bar (top 100px) is excluded from hashing."""
        # An image that is entirely one color except the status bar
        img = Image.new("RGB", (1080, 1920), color="white")
        # Paint the status bar a different color
        for y in range(STATUS_BAR_HEIGHT):
            for x in range(1080):
                img.putpixel((x, y), (255, 0, 0))

        # The hash should match a plain white image (status bar excluded)
        plain = Image.new("RGB", (1080, 1920), color="white")
        assert compute_screen_hash(img) == compute_screen_hash(plain)

    def test_small_image_no_crop(self):
        """Images with height <= STATUS_BAR_HEIGHT are not cropped."""
        img = Image.new("RGB", (100, 50), color="green")
        # Should not raise
        result = compute_screen_hash(img)
        assert isinstance(result, str)
        assert len(result) == 16

    def test_rgba_converted_to_rgb(self):
        """RGBA images are converted to RGB before hashing."""
        img = Image.new("RGBA", (1080, 1920), color=(255, 0, 0, 128))
        result = compute_screen_hash(img)
        assert isinstance(result, str)
        assert len(result) == 16


class TestHammingDistance:
    def test_identical_hashes_zero_distance(self):
        assert hamming_distance("0000", "0000") == 0
        assert hamming_distance("ffff", "ffff") == 0

    def test_completely_different(self):
        """0000 vs ffff = 16 bits different (4 hex digits * 4 bits)."""
        assert hamming_distance("0000", "ffff") == 16

    def test_one_bit_difference(self):
        """0001 vs 0000 = 1 bit different."""
        assert hamming_distance("0000", "0001") == 1

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="Hash length mismatch"):
            hamming_distance("000", "0000")


class TestIsScreenStable:
    def test_identical_hashes_are_stable(self):
        assert is_screen_stable("0000", "0000") is True

    def test_one_bit_difference_is_stable(self):
        """1 bit difference is within default threshold of 12."""
        assert is_screen_stable("0000", "0001") is True

    def test_large_difference_is_unstable(self):
        assert is_screen_stable("0000", "ffff") is False

    def test_custom_threshold(self):
        assert is_screen_stable("0000", "0001", threshold=0) is False
        assert is_screen_stable("0000", "0001", threshold=1) is True

    def test_default_threshold_is_12(self):
        """Verify the default threshold constant."""
        assert HAMMING_THRESHOLD == 12
