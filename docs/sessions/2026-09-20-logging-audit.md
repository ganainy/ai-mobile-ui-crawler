---
author: claude
date: 2026-09-20
---
# Logging audit and cleanup

- Grilled the scope with the user (all recommended answers taken): level contract, `log_level` wiring, report-first then apply, `on_debug_log` gets an optional `level`, live stats keep mining log text (messages frozen), LLM bodies at DEBUG, log once at the boundary, `exc_info` policy, all five additions, `[DEBUG]` prefix stripped.
- Root cause: `MainWindow._on_debug_log` hardcoded `LogLevel.DEBUG` for every `crawler_agent` record (that logger has `propagate=False` during a run).
- Report: [logging-audit.md](../logging-audit.md), with an "Applied" section listing what was done and what was not.
- Touched tests: `test_log_viewer.py` (default filter now INFO), `test_crawler_agent_service.py` (mock record `exc_info=None`); new `tests/domain/test_crawler_log_handler.py`.
- Uncommitted, on top of the user's existing dirty tree (`main_window.py`, `signal_adapter.py`, `crawler_event_listener.py`, `crawl.py`).
