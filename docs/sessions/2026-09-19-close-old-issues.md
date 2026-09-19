---
author: claude
updated: 2026-09-19
---
# Close old issues #1 and #5

- #1 (`DatabaseManager.save_run_stats` missing): already fixed. `crawler_loop.py` uses `run_repository.update_run_stats`; the stats collector saves via `RunStatsRepository.save_run_stats`. Closed with comment.
- #5 (`ganainy/droidrun` fork not found): already fixed. Agent code is vendored in `domain/crawler_agent`; no droidrun dependency in `pyproject.toml` or `.venv312`. Closed with comment.
- Deleted stray pip output file `src/=0.4.26` (e180b92). `mobilerun` is only an optional guarded import in `tools/driver/cloud.py`.
