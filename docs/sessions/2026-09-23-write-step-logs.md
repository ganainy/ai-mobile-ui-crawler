---
author: claude
updated: 2026-09-23
---
# Issue #24: the crawler writes step_logs again

## What
Nothing in `src/` wrote `step_logs` since the move to the agent loop, so the Analysis Bundle, the HTML report and the Summary stats were empty on real runs. `CrawlerAgentService` now writes one row per executed tool.

## Changes
- `domain/crawler_agent_service.py`:
  - `_write_step_log(event)`: called in `_handle_tool_execution_event` right after `_current_step_number` goes up and before the phase transitions, so the row has the same number as `step_phase_transitions` and `update_step_current_phase` finds it. Fields: `action_type` = tool name, `action_description` = tool result summary, `input_text` = `tool_args["text"]`, success, `error_message` = summary on failure, `action_duration_ms` = tool duration.
  - `_step_decision`: the latest Executor (`parsed_action["thought"]`, `executor_llm_ms`) or FastAgent (`thought`, `fast_agent_llm_ms`) decision, set in `_buffer_workflow_timing`. Reasoning goes on every tool of that decision (an Action Batch); the LLM time only on the first, so sums are not inflated.
  - `_dispatch_workflow_event(event)`: the event routing that was inline in the run's stream consumer, pulled out so tests go through the same path.
- `tests/domain/test_crawler_agent_step_logs.py`: real SQLite DB, events fed through `_dispatch_workflow_event`; checks the rows, that step numbers match the phase rows, FastAgent reasoning, and that the Analysis Bundle joins action fields with timing on one `steps.jsonl` line.

## Answers to the issue's open questions
- A step is one tool execution (matches `_current_step_number`).
- Screen ids: nothing in the agent loop assigns them (`ScreenTracker` is never instantiated), so `from_screen_id`/`to_screen_id` stay null and "unique screens" stays 0.
- `PromptBuilder` / `ExplorationJournal` are never instantiated in `src/`: dead readers, left alone.
- Screenshots: counters not unified (Fix 5 separated them on purpose). Code review found that, now that rows exist, joining screenshots by `step_number` put them on the wrong steps once a decision ran several tools (and the Executor's screenshot-less interaction overwrote the Manager's path in the dict). Fixed with `screenshots_by_step` in `infrastructure/analysis_bundle.py`, used by the bundle and `ReportGenerator`: a step gets the screenshot of the latest AI call between the previous step's timestamp and its own, so the first tool of a decision carries the screenshot and the rest of the batch none. Timing-only lines still match by number.

## Known gaps (from review)
- `ai_response_time_ms` is the Executor/FastAgent LLM time only; the Manager's time is in the step's `timing` (`manager_llm_ms`), not in this column.
- `action_description` is the tool result summary, not the Executor's planned description (the planned one is shared by a whole batch and would make "Repeated actions" count batches). On failure it equals `error_message`.
- Control tools (`complete`, `remember`, invalid-action fallbacks) go through the tool registry, so they get rows and count in success/failure stats.
- `current_phase` on every finished row ends as `capture` (the handler ends CHECKPOINT -> CAPTURE); pre-existing behaviour.
- CONTEXT.md says an Action Batch "counts as one step" (towards the step limit), while the phase rows and `step_logs` number each tool. Terminology not reconciled.

## Notes
- Tests in the worktree must run with `PYTHONPATH=src`: `pytest.ini` wins over `pyproject.toml`'s `pythonpath`, and `.venv312` has the main checkout's `src` installed, so without it the worktree's tests import `main`'s code.
- Not tried on a real crawl.
