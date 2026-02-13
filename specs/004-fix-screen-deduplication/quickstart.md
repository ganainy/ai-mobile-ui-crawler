# Quickstart: Testing Screen Deduplication

## Prerequisites

- Python 3.11+
- `pip install imagehash pillow`

## Configuration

To adjust the sensitivity, modify `config/config.json` (or equivalent):

```json
{
  "screen_similarity_threshold": 12
}
```

- **Lower (e.g., 5)**: Stricter. Minor changes (carousel) might be treated as new screens.
- **Higher (e.g., 20)**: Looser. Different screens (Settings vs Profile) might be merged.
- **Default (12)**: Optimized for avoiding carousel false positives while separating distinct screens.

## verifying the Fix

1. Run the crawler on an app with a carousel (or use the test script).
2. Check `crawler.log` for lines like:
   `Found similar screen {id} (distance: 4)`
3. Verify that the unique screen count in the run report is lower than before for the same duration.
