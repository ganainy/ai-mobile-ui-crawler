---
author: claude
date: 2026-09-23
---
# Screen matching: per-app scope, threshold 8

Item 1 of [handoff-2026-09-23](../handoff-2026-09-23.md). Follows [run stats / screen ids](2026-09-23-run-stats-screens-warnings.md).

## Measurement (run 179, 36 screenshots, closest-match like `ScreenTracker`)
| Threshold | Screens | Notes |
|---|---|---|
| 12 (old) | 16 | Four different onboarding questions (steps 5, 8, 16, 21: goals / barriers / meal planning / activity level) got one id; "what can we call you?" and "how tall are you?" got one id |
| 8 | 20 | No false merges found by eye; ticked box / typed text still the same screen |
| 6 | 23 | Typing "30" into the age field (6 bits) becomes a new screen |

State changes on one screen moved the hash 1-6 bits; same-layout different questions were 10-12 bits apart. The old "clock/battery noise" reason for 12 no longer applies since the status bar is cropped (ADR-0002).

## Changes
- `HAMMING_THRESHOLD` 12 -> 8 (`domain/screen_hash.py`); `ScreenTracker` and `find_similar_screens` default to it; config default `screen_similarity_threshold` also 8 (that key is still not read by anything; `CrawlerAgentService` uses the tracker default).
- `screens.app_package` added. `ScreenTracker` looks up `runs.app_package` for the run on the first processed screen and passes it to `get_screen_by_hash` / `find_similar_screens`, which filter by it (no package given = all screens, as before). Matching is per app across runs.
- Old `UNIQUE(composite_hash)` would block two apps owning the same hash, so `DatabaseManager._migrate_screens_app_package` rebuilds the table with `UNIQUE(app_package, composite_hash)` (foreign keys off during the rebuild, ids kept), backfilling the package from `runs`. Runs once (skips when the column exists).
- `CONTEXT.md` **Screen** updated.

## Verified
- New tests: repo per-app filtering, same hash in two apps, uniqueness within one app, migration from the old table (backfill, idempotent), tracker gives a new id for the same image in another app's run. Full suite green.
- Real `crawler.db` migrated (backup `%APPDATA%/mobile-crawler/crawler.db.bak-2026-09-23`): 2 screens got `com.myfitnesspal.android`, `foreign_key_check` and `integrity_check` clean.
- Not tried in a crawl.

## Left
- Structural signal (activity + a11y tree shape) deferred until Portal's a11y service works.
