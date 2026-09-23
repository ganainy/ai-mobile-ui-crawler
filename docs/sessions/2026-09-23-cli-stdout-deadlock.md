---
author: claude
date: 2026-09-23
---
# CLI crawl hung on first stderr line (stdout capture deadlock)

**Report:** CLI crawl (run 181) printed a doubled `[stdout] {... [stderr] ...}` debug_log line, then did nothing; Ctrl+C printed "Aborted!" but never returned to the shell.

**Causes:**
- User input: `--device` ended `._tc` instead of `._tcp` (adb "device not found"), and `--package fitness`` with no space before the PowerShell backtick put a newline into the package name (`target_package` ended in `\n`).
- Bug: `capture_stdout_to_ui` wraps stdout/stderr during a crawl; `_LineCapturingStream.write` called its callback while holding a non-reentrant lock. In the CLI the callback is `JSONEventListener.on_debug_log`, which `print`s to the same wrapped stdout, so a captured line was re-captured and the nested write blocked on the lock forever. The stuck thread kept the process alive after Ctrl+C. GUI unaffected (its callback does not print).

**Fix:** `core/log_sinks.py`: callbacks run outside the lock, and a thread-local flag makes writes made from inside a callback go only to the real stream (no re-capture, shared by the stdout and stderr wrappers). Regression test `test_callback_that_prints_does_not_deadlock_or_recapture` (hung before the fix). `tests/core` + `tests/cli` green.

**Not done:** not re-run on the phone. Uncommitted.
