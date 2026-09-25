---
author: claude
date: 2026-09-25
---
# Readable crawl logs (CLI and GUI)

User pasted a run-188 CLI log (`--log-level DEBUG`) and asked for readable debug logs in both the GUI and the CLI.

## Why the log was so noisy
Every crawler_agent log line reached stdout up to four times:
1. The default `CLILogHandler` on the `crawler_agent` logger (rich console) printed it raw.
2. `capture_stdout_to_ui` captured that print and emitted it as a `[stdout] ...` debug_log event.
3. `CrawlerLogHandler` (added by `configure_run_logging` next to the console handler) emitted the record itself.
4. `JSONEventListener` printed that event to `sys.stdout`, which was the capturing stream at that point, so it came back as `[stdout] {"event": "debug_log", ...}`. The thread-local guard in `_LineCapturingStream` only stops re-capture inside a capture callback, not events emitted directly.

Streamed LLM output (`extra={"stream": True}`) also produced one event per chunk, so Manager responses were split mid-sentence.

## Changes
- `JSONEventListener` and the new `PrettyEventListener` write to the stream that was stdout when they were created, not the capturing stream (fixes 4).
- `configure_run_logging` replaces the `crawler_agent` handlers with the run handler, and `clear_run_logging` puts them back (fixes 1–2).
- `CrawlerLogHandler` buffers `stream` records and emits one joined message at `stream_end`.
- `crawl --format auto|pretty|json`, new `cli/event_printer.py`. Pretty prints `HH:MM:SS label message` with continuation lines indented, step separators, one-line AI response and action summaries. AI request, screenshot and state events show only at DEBUG. `[stdout]`/`[stderr]` mirrors are dropped (they already appeared raw on the terminal). Auto means pretty on a TTY, JSON otherwise, so pipes and `CliRunner` tests keep JSON. The `batch_completed` JSON line is printed only with JSON output.
- `LogCleaner` moved from `ui/` to `core/` so the pretty printer shares the GUI's ANSI stripping, noise filter and dedup. Its `Attempting to import module: ...` pattern never matched (it expected a colon right after "import"), so it's fixed.

## Not done / open
- Stdout capture still echoes to the terminal: `TerminalHumanPrompter` prints prompts with `print`/`input` on stdout, so turning the echo off would hide them. Library prints still show raw.
- Not tried in a real crawl. Worth checking a DEBUG run in a terminal and in the GUI log panel.
