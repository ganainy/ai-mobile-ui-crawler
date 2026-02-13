# Data Model: Screen Deduplication

## Schema Changes

No database schema changes required. `crawler.db` `screens` table remains compatible.

## Configuration Models

### CrawlerConfig

Updated with new fields:

```python
@dataclass
class CrawlerConfig:
    # ... existing fields ...
    screen_similarity_threshold: int = 12  # Hamming distance threshold (default: 12)
    use_perceptual_hashing: bool = True     # Toggle for using dHash vs exact match (default: True)
```

## Internal Entities

### ScreenTracker

Updated hashing strategy:

- **Input**: `PIL.Image`
- **Algorithm**: `imagehash.dhash(image, hash_size=8)`
- **Output**: 64-bit Hex String (e.g., "8f3e2a...")

### ScreenRepository

Updated lookup query logic:

- **Method**: `find_similar_screens(hash, threshold)`
- **Logic**: Retrieve candidates -> Calculate Hamming Distance -> Filter by `threshold`
