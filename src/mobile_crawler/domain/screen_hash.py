"""Shared screen hashing utilities.

Extracted from ScreenTracker._generate_hash for reuse in both
screen dedup (ScreenTracker) and settle detection (UIWaitPredicate).
"""

import imagehash
from PIL import Image

# Status bar height excluded from hashing (top 100px).
# Prevents false positives from time/battery/notifications changes.
STATUS_BAR_HEIGHT = 100

# dHash size (64-bit hash).
DHASH_SIZE = 8

# Hamming distance threshold for "same screen" (12/64 bits ≈ 19%). Tuned for
# ScreenTracker dedup, where two visits of the same screen must tolerate
# incidental noise like clock/battery/notification changes.
HAMMING_THRESHOLD = 12

# Hamming distance threshold for "settled between two consecutive fast polls"
# (2/64 bits ≈ 3%). Much stricter than HAMMING_THRESHOLD: settle-detection
# compares screenshots only 150-300ms apart, so a still-animating screen
# (e.g. a slow scroll or fade) should read as different, not "the same screen".
SETTLE_HAMMING_THRESHOLD = 2


def compute_screen_hash(image: Image.Image) -> str:
    """Compute a perceptual hash for screen comparison.

    Uses dHash (Difference Hash) with size=8 (64-bit hash), robust to:
    - Scaling and aspect ratio changes
    - Minor color adjustments / brightness changes
    - Content replacement (e.g., carousel rotations)

    The status bar (top 100px) is excluded to prevent false positives
    from time/battery/notifications changes.

    Args:
        image: PIL Image to hash

    Returns:
        Hex string representation of the 64-bit perceptual hash
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    width, height = image.size
    if height > STATUS_BAR_HEIGHT:
        image = image.crop((0, STATUS_BAR_HEIGHT, width, height))

    dhash = imagehash.dhash(image, hash_size=DHASH_SIZE)
    return str(dhash)


def hamming_distance(hash_a: str, hash_b: str) -> int:
    """Compute Hamming distance between two hex hash strings.

    Args:
        hash_a: First hex hash string
        hash_b: Second hex hash string

    Returns:
        Number of differing bits
    """
    if len(hash_a) != len(hash_b):
        raise ValueError(f"Hash length mismatch: {len(hash_a)} != {len(hash_b)}")

    distance = 0
    for i in range(len(hash_a)):
        # XOR the hex digits and count set bits
        xor = int(hash_a[i], 16) ^ int(hash_b[i], 16)
        distance += bin(xor).count("1")

    return distance


def is_screen_stable(
    hash_a: str, hash_b: str, threshold: int = HAMMING_THRESHOLD
) -> bool:
    """Check if two screen hashes represent the same (stable) screen.

    Args:
        hash_a: First hex hash string
        hash_b: Second hex hash string
        threshold: Maximum Hamming distance to consider screens the same

    Returns:
        True if the screens are visually the same
    """
    return hamming_distance(hash_a, hash_b) <= threshold
