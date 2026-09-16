# Bug: `run_stats` save fails with `FOREIGN KEY constraint failed`

## Symptom

```
[ERROR] mobile_crawler.infrastructure.run_stats_repository: Failed to save run_stats for run_id=139: FOREIGN KEY constraint failed
[ERROR] mobile_crawler.core.runtime_stats_collector: Failed to save runtime stats for run 139: FOREIGN KEY constraint failed
```

Every crawl run's end-of-run stats save fails, or fails intermittently, with this
exception. `RunStatsRepository.save_run_stats()` (`src/mobile_crawler/infrastructure/run_stats_repository.py:24`)
catches, logs, and re-raises; `RuntimeStatsCollector.save()` (`src/mobile_crawler/core/runtime_stats_collector.py:635`)
catches that and returns `False`, so the run's stats are silently dropped from `crawler.db`.

## Root cause

`run_stats` has **two** foreign keys (`src/mobile_crawler/infrastructure/migrations/001_initial_schema.sql:144-145`):

```sql
FOREIGN KEY (run_id) REFERENCES runs(id),
FOREIGN KEY (most_visited_screen_id) REFERENCES screens(id)
```

`PRAGMA foreign_keys=ON` is set in `DatabaseManager` (`src/mobile_crawler/infrastructure/database.py:36`), so both are enforced.

`most_visited_screen_id` is populated by `RuntimeStatsCollector.record_screen_visit()`
(`src/mobile_crawler/core/runtime_stats_collector.py:340-359`), which just stores whatever
`screen_id` it's handed — it never validates that the id exists in the real `screens` table.

The caller, `MainWindow._on_screenshot_captured_stats()` (`src/mobile_crawler/ui/main_window.py:1620-1623`),
does **not** pass a real `screens.id`. It fabricates one on the spot:

```python
screen_id = hash(screen_hash or step_number) if screen_hash else step_number
self._runtime_stats_collector.record_screen_visit(screen_id=screen_id, navigation_depth=step_number)
```

- `screen_hash` is a perceptual hash string computed locally in this method via `imagehash.phash(img)`
  (`main_window.py:1602-1618`) — a completely separate identity system from the project's real
  screen-dedup pipeline (`ScreenTracker` + `ScreenRepository`, `src/mobile_crawler/domain/screen_tracker.py`,
  which writes actual rows to the `screens` table with dHash-based composite hashes).
- `hash(screen_hash)` is Python's builtin `hash()` on a string — with hash randomization enabled
  (the default), this returns a large, effectively random 64-bit signed int on every process run.
  It has **no relationship** to any `screens.id` primary key.
- The fallback path (`hash(step_number)`) happens to equal `step_number` itself (`hash()` is the
  identity function for small ints), so it can coincidentally look valid for early steps, which is
  why the failure is intermittent rather than 100% reproducible.

So whenever a screen becomes the "most visited" one in a run (`most_visited_screen_count` update
at `runtime_stats_collector.py:356-359`), `most_visited_screen_id` gets set to this fabricated,
essentially-random integer. When `save()` inserts the row, SQLite checks it against `screens(id)`,
finds no match, and raises `FOREIGN KEY constraint failed`.

Confirmed this field is otherwise dead: `most_visited_screen_id` is never read back or displayed
anywhere in the UI (`grep` across `src/` only shows it in the collector, the repository's generic
`SELECT *`/round-trip, the schema, and tests) — it's write-only today, so nulling it out loses no
working feature.

Note: `ScreenTracker` (the class that actually owns real `screens.id` values) is **not
instantiated anywhere in `src/`** currently — only in its own tests and an old spec under
`specs/004-fix-screen-deduplication/`. It appears to be unwired/orphaned relative to the live
crawl loop, which is a separate architectural gap from this bug.

## Fix options

**Option A — minimal, safe, recommended for this fix:**
Stop fabricating a fake `screen_id` for stats purposes. In
`main_window.py:_on_screenshot_captured_stats`, don't pass a synthesized id to
`record_screen_visit()`'s `most_visited_screen_id`-tracking role. Concretely:
- Keep using the local perceptual hash (or something derived from it) as the key for the
  in-memory `_screen_visit_counts` dict used to compute `most_visited_screen_count` /
  `unique_screens_visited` — those are just counts, no FK involved.
- Do **not** let that fabricated key flow into the persisted `most_visited_screen_id` column.
  Simplest: in `RuntimeStats.to_db_dict()` (`runtime_stats_collector.py:105`), drop/omit
  `most_visited_screen_id` (or always write `None`), since there is currently no reliable way to
  map to a real `screens.id` from this code path. Update `RuntimeStats.from_db_dict()` accordingly
  (leave it defaulting to `None`) and add/adjust tests in `tests/core/test_runtime_stats_collector.py`.

**Option B — proper fix, larger scope:**
Wire the real `ScreenTracker`/`ScreenRepository` screen ids into the crawl loop so a genuine
`screens.id` is available at `_on_screenshot_captured_stats` time (e.g. thread it through the
`screenshot_captured` signal or look it up via `ScreenRepository` using the existing dHash-based
composite hash), then pass that real id to `record_screen_visit()`. This restores
`most_visited_screen_id` as a meaningful, working feature but requires wiring `ScreenTracker` into
the live pipeline (it's currently orphaned — see note above), which is out of scope for just
fixing the crash.

**Recommendation:** ship Option A now to stop the data loss / log spam; file Option B as a
follow-up if "most visited screen by DB id" is actually wanted as a feature.

## Files to touch (Option A)

- `src/mobile_crawler/ui/main_window.py` (~line 1620-1623): stop deriving `most_visited_screen_id`
  from `hash(screen_hash or step_number)`.
- `src/mobile_crawler/core/runtime_stats_collector.py`:
  - `record_screen_visit()` (line 340): decide whether `most_visited_screen_id` should still be
    tracked in-memory (fine) vs. persisted (should become `None`/omitted).
  - `to_db_dict()` (line 105) / `from_db_dict()` (line 189): stop round-tripping a fabricated id
    through the FK'd column.
- `tests/core/test_runtime_stats_collector.py`: update any assertions on `most_visited_screen_id`.

## How to verify the fix

1. Run a crawl session long enough that some screen is revisited (so
   `most_visited_screen_count` updates at least once).
2. Confirm no `FOREIGN KEY constraint failed` error appears in logs for `run_stats_repository` /
   `runtime_stats_collector`.
3. Confirm a `run_stats` row exists for the run (`SELECT * FROM run_stats WHERE run_id = <id>`).
4. Run existing `tests/core/test_runtime_stats_collector.py` and
   `tests/domain/test_crawler_agent_service.py` suites.
