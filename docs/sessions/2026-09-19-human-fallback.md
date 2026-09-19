---
author: claude
date: 2026-09-19
---
# Human Fallback (#10)

- `domain/human_fallback.py`: `HumanFallback.request(kind, message)` -> `FallbackOutcome` (answered / timed_out / disabled / declined). Qt-free; takes a `HumanPrompter` callable. Every skip sets `skipped_reason` ("authentication skipped: ...") for #11 to record on the run.
- `ui/human_fallback_dialog.py`: `QtHumanPrompter` is called from the crawl thread, emits a queued signal, dialog is shown with `open()` (non-blocking), thread waits on an Event with the timeout and closes the dialog on expiry.
- Settings: "Human Fallback" group (checkbox + timeout minutes, default 5) in `settings_panel.py`, keys `human_fallback_enabled` / `human_fallback_timeout_minutes`.
- Not yet wired: #11 must construct `HumanFallback(HumanFallbackConfig.from_store(store), QtHumanPrompter(main_window))` and write `skipped_reason` into the run's Stop Reason / notes.
- Commit note: `settings_panel.py` also carries uncommitted #6/#8 hunks, so it was left out of the #10 commit like in #8.
