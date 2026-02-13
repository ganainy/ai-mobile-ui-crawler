# Internal Contracts

No external API changes. This feature modifies internal logic.

## ScreenTracker Interface

### `process_screen`

**Behavior Change**:
- Calculating hash uses `dhash(size=8)` instead of `phash(size=16)`.
- Similarity check uses configurable threshold (default 12) instead of hardcoded 5.

```python
def process_screen(self, image: Image, ...) -> ScreenState:
    """
    Process screen with improved deduplication.
    
    1. Generate dHash (64-bit)
    2. Query DB for screens with Hamming distance < config.screen_similarity_threshold
    3. If found: Return existing screen ID (is_new=False)
    4. If not found: Create new screen (is_new=True)
    """
```
