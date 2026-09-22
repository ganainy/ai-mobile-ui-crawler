---
author: claude
updated: 2026-09-23
---
# Issue #22: phase Timing Breakdown in the analysis bundle

## What
The GUI's StepDetailWidget shows a Timing Breakdown per step (phase totals, a11y/OmniParser/LLM sub-durations, Manager validation retries) read from `step_phase_transitions`. `report` never exported it. Now the Analysis Bundle does.

## Changes
- `domain/step_phase_models.py`: `build_timing_breakdown(transitions)`, a pure, Qt-free version of the GUI's `_build_timing_breakdown` (same rows), returning `total_step_duration_ms`, `phases` (`{phase, metric, duration_ms}`; metric is `phase total` or a sub-phase key like `a11y_ms`), `validation_retry_count`, `validation_retries`; `None` when a step has no timing data.
- `infrastructure/analysis_bundle.py`:
  - `steps.jsonl`: every line gains `timing` (the breakdown above, or `null`).
  - `run.json`: new `step_phase_transitions` with the raw rows (same "raw data lives in run.json" convention).
  - `analysis.md` and the HTML report (shared sections): new "Timing breakdown" section with avg/max per phase+metric across steps, the retry count and up to 10 retries (`step N attempt M: reason`). Omitted when the run has no phase rows.
- The GUI's `_build_timing_breakdown` in `ai_monitor_panel.py` was left alone (GUI changes out of scope), so the logic is duplicated for now; the GUI could import the domain function later.

## Review fixes (before commit)
- Spec review found that nothing in `src/` writes `step_logs` (only tests call `create_step_log`), so on a real run `steps.jsonl` was empty and the per-step `timing` never appeared. `steps.jsonl` now has one line per step number in `step_logs` ∪ phase transitions; a step with timing but no `step_logs` row gets the same keys with nulls plus `timing`. Its `screenshot` stays null: `ai_interactions` numbers steps with a different counter (`_ai_call_step_number`) than the phase rows (`_current_step_number`), so they can drift.
- Non-numeric/null sub-phase values are skipped instead of crashing the whole report.
- Left as judgement calls: timing is a plain dict, not a dataclass; `_sections` parameter list grew.

## Open
- `step_logs` never being written by the crawler is a pre-existing gap: `steps.jsonl` action fields, "Failed steps"/"Repeated actions" sections and the Summary step counts are empty for real runs. Worth its own issue.
- Point the GUI's `_build_timing_breakdown` at `build_timing_breakdown` (follow-up).

## Status
Committed on worktree branch `issue-22-phase-timing` (off local `main` d150245); not yet merged into `main`. Tests in `tests/domain/test_run_report_bundle.py`; full suite green before the review fixes (1562 passed, 7 skipped), report tests green after. No typechecker in `.venv312`. Not checked against a real run's database.
