# Phase 0 Research: Screen Deduplication Logic

**Date**: 2026-01-11
**Related Feature**: `004-fix-screen-deduplication`

## Research Goal
Determine the optimal hashing algorithm and parameters to correctly deduplicate screens with dynamic content (specifically rotating carousels on home screens) while preserving the ability to distinguish genuinely different screens.

## Methodology
Analyzed 10 actual screenshots from Run #88 (provided in bug report) using three different hashing approaches:
1. **Current Implementation**: `phash` (size 16 -> 256 bits)
2. **Reduced Detail**: `phash` (size 8 -> 64 bits)
3. **Difference Hash**: `dhash` (size 8 -> 64 bits)

Tested whether these algorithms could cluster the "Home Screen" variations (screenshots 0, 4, 5, 6, 7, 8) while separating them from "Search History" (1) and "Search Results" (2, 3, 9).

## Findings

### 1. Current Implementation (pHash, size=16) - **FAILED**
- **Home Screen Internal distances**: 2 to 104 (Hamming distance)
- **Home vs Search**: ~122
- **Issue**: The carousel rotation caused massive hash differences (up to 104 bits different out of 256).
- **Conclusion**: Too sensitive to content changes. Threshold `5` was hopelessly strict.

### 2. Reduced pHash (size=8) - **Inconclusive**
- **Home Screen Internal distances**: 0 to 18
- **Home vs Search**: 22 to 30
- **Issue**: The "Same Screen" max distance (18) and "Different Screen" min distance (22) were too close.
- **Risk**: High risk of false positives or negatives depending on threshold.

### 3. Difference Hash (dHash, size=8) - **SUCCESS**
- **Home Screen Internal distances**: 0 to 8
- **Home vs Search**: 32
- **Home vs Search Results**: 29
- **Separation**: Clear gap between "Same Screen" (max 8) and "Different Screen" (min 29).
- **Search Results (Different Queries)**: Distance 24. These are visually distinct content but same layout.

## Data Matrix (dHash size=8)

| Screen Type | vs Home | vs Self | vs Search |
|-------------|---------|---------|-----------|
| Home (6 vars)| -- | 0 - 8 | 32 |
| Search | 32 | 0 | -- |
| Results A | 29 | 0 | -- |
| Results B | 29 | 24 | -- |

## Decisions

### 1. Algorithm Change
**Decision**: Switch from `phash` (Perceptual Hash) to `dhash` (Difference Hash).
**Rationale**: `dhash` tracks gradients and structure better than frequency (pHash), making it more robust to "content replacement" like carousels where the structure (box) remains but pixels change.

### 2. Hash Size
**Decision**: Use `hash_size=8` (producing 64-bit hashes).
**Rationale**: 16 (256 bits) was noise-heavy. 8 provides sufficient structural resolution with cleaner separation.

### 3. Similarity Threshold
**Decision**: Set default `similarity_threshold` to **12** (Hamming distance).
**Rationale**:
- Covers known Home Screen variations (Max observed: 8)
- Well below different screen types (Min observed: 29)
- Keeps different Search Results (Dist 24) distinct, which is safer for exploration than merging them prematurely.

## Implementation Details

- **Dependency**: `imagehash.dhash` is already available in the library.
- **Configuration**: Add `similarity_threshold` to `CrawlerConfig`.
- **Backward Compatibility**:
  - `dhash` strings look the same (hex).
  - Existing DB hashes are `phash`.
  - **Strategy**: We cannot compare `phash` to `dhash`. We will start fresh for new runs (run_id specificity handles this). For *existing* runs, the viewer might look weird if we mix them, but this only affects *writing* new screens.
  - **Note**: The DB stores `composite_hash` as the unique key for lookup. Changing algorithm means new screens will just look "new" compared to old run screens, which is fine.

## Resolved Unknowns
- [x] Optimal hashing algo: dHash
- [x] Optimal size: 8 (64 bits)
- [x] Threshold: 12 (Hamming Distance)
