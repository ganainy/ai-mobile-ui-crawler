---
author: claude
updated: 2026-09-23
---
# Issue #16: CLI `crawl --step-by-step`

## What
The GUI's step-by-step mode (`CrawlerLoop.set_step_by_step_enabled` + "Next Step") had no CLI equivalent. `crawl --step-by-step` now pauses after each agent step, prints what that step did, and waits for Enter.

## Changes
- Summary content: the agent pauses *after* a step (droid `handle_executor_result` / FastAgent), so the summary is the paused step's results, not the next action (which isn't decided yet).
- `CrawlerAgentService`: `_record_step_action` turns each `ToolExecutionEvent` into an `ActionResult` (tool name, success, summary, duration); `_surface_step_pause` emits the new listener event `on_step_paused(run_id, step_number, actions)` before the `paused_step` state change, then resets the list.
- `CrawlerEventListener.on_step_paused` added (default no-op). `SignalAdapter.on_step_paused` only gained an optional `actions` param so it doesn't raise. Side effect: the GUI's existing, previously dead `_on_step_paused` handler now fires, logging "Step N finished. Paused for review."
- New `cli/console_reader.py` `ConsoleReader`: the single-stdin-reader logic pulled out of `TerminalHumanPrompter` (#14), shared by the prompter and the step console so an abandoned Human Fallback read can't race the step pause for the user's Enter.
- New `cli/step_by_step_console.py` `StepByStepConsole`: duck-typed listener; prints the summary to stderr (stdout is the JSON event stream) and waits for Enter on a background thread (the handler runs on the agent's event-loop thread), then calls `CrawlerLoop.advance_step`. EOF on stdin advances, so a non-interactive run can't hang.
- `crawl`: `--step-by-step` flag enables the mode and adds the console before `run`.

## Review fixes (before commit f91e9b6)
- `_surface_step_pause` emitted `on_step_paused` before the `paused_step` state change; an immediate advance (buffered Enter, EOF) was dropped by `advance_step`'s state guard and the workflow hung. Now the state changes first (tested).
- `_record_step_action` grew `_step_actions` all run long when step-by-step was off; it now records only while the mode is on.

## Status
Committed as f91e9b6, with only this issue's hunks (another session was editing `crawl.py` / `test_crawl_command.py` at the same time; its work is left uncommitted). Full suite green. No typechecker in `.venv312`. Not tried on a real device or terminal.
