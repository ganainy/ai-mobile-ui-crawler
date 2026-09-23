---
author: claude
date: 2026-09-23
---
# MobSF scorecard lists broke post-run MobSF stats and the Run Report

Run 183 (Fit, 53 steps) ended with:
- `MobSF analysis failed: int() argument must be ... not 'list'`
- `Run report generation failed: 'list' object has no attribute 'keys'`

## Cause
Real MobSF v4 output (checked on run 183's JSON report): `appsec.high` / `warning` / `info` / `secure` / `hotspot` are lists of `{title, description, section}`; `appsec.security_score` is an int; top-level `files` is a list of paths.

- `CrawlerLoop._run_mobsf_analysis` did `int(scorecard["high"])` on the list. The scan itself succeeded; only the stats event was lost.
- `JsonMobSFParser` was written against an invented shape (top-level `security_score`, `findings` dict, `files` dict), covered only by a test using that invented shape. `list(files.keys())` crashed the whole Run Report.

## Fix
- `mobsf_scorecard_summary(scorecard) -> (score, high, medium, low)` in `core/crawler_loop.py`: counts lists, still accepts plain counts and `medium`/`low` names.
- Parser reads score and high/warning findings from `appsec`; `files` works as list or dict.
- Tests: `tests/unit/test_mobsf_scorecard_counts.py`, rewritten `tests/unit/reporting/test_parsers.py` using the real shape.

## Verified
- Parser on run 183's report: score 51, 1 high, 46 medium, 2235 files; summary `(51.0, 1, 46, 2)`.
- `mobile-crawler report 183` now writes `run_report.html` (Phoenix telemetry fetch timed out, unrelated).
- Unit suite green. Not re-run in a live crawl.

## Not done
"Traffic capture not started by this manager ... Cannot stop/pull" is a follow-on of a failed start; the start message is emitted earlier in the log and was not in the pasted output.
