---
author: claude
date: 2026-09-25
---
# Ctrl+C in a CLI crawl dumps tracebacks

User pressed Ctrl+C at a `--step-by-step` pause; got `Aborted!` followed by `AttributeError: 'NoneType' object has no attribute 'cleanup'` in `run_and_cleanup`, several "Task was destroyed but it is pending!", "Event loop is closed" and a contextvars `ValueError` from `workflows`.

## Cause
The KeyboardInterrupt surfaces out of `loop.run_until_complete` in `CrawlerLoop._run_async` while the crawl coroutine is suspended (waiting for Enter). `KeyboardInterrupt` is not an `Exception`, so `run()` skips its handlers but runs its `finally`, which sets `_crawler_agent_service = None`; `_run_async` then closes the loop. The still-suspended `run_and_cleanup` is closed at garbage collection: its `finally` finds the service gone, and every other task (video segment loop, workflow runner, step-event consumer, subprocess transports) is destroyed on a closed loop. Not specific to step-by-step: any Ctrl+C mid-crawl hits it.

## Change
- `core/crawler_loop.py` `_run_async`: runs the coroutine as a task; on KeyboardInterrupt sets `_cancel_requested`, cancels the task, runs the loop until it finishes (so `run_and_cleanup`'s cleanup, including its drain of pending tasks, happens on a live loop with the service still set), then re-raises so the CLI still aborts / the batch still records `user_stop`. A second Ctrl+C during that cleanup is not swallowed.
- Test `TestCrawlerLoopCtrlC` in `tests/core/test_crawler_loop.py`. core + cli tests green; not tried on the phone.

## Not done
- A single-package CLI crawl stopped with Ctrl+C still leaves the run row as RUNNING (only the batch path calls `mark_user_stopped`); pre-existing.
