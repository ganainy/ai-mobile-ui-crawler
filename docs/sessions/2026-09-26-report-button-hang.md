---
author: claude
updated: 2026-09-26
---
# Generate Report button hang

- Cause: `RunHistoryView._on_generate_report_clicked` called `report_generator.generate(run_id, fetch_telemetry=True)` on the UI thread; the telemetry fetch (Phoenix/Langfuse) blocks on the network, freezing the window.
- Fix: new `ReportWorker(QThread)` in `ui/widgets/run_history_view.py` (same pattern as `MobSFAnalysisWorker`); button shows "Generating..." and is disabled meanwhile, success/failure dialogs come from worker signals.
- Checkbox: already exists, Settings > "Generate report after each run" (`auto_generate_report_after_run`, default on), honoured by `CrawlerLoop._generate_report`; nothing added.
- Tests: `tests/ui/test_run_history_view.py` green (worker waits added, new off-UI-thread test). Not tried in the real GUI.
