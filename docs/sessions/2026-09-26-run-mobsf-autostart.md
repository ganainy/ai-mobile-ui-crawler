---
author: claude
updated: 2026-09-26
---
# Run MobSF button starts the container

Run History's "Run MobSF" failed with "Cannot connect to MobSF server at http://localhost:8000" when the container was down. `MobSFAnalysisWorker.run` (`ui/widgets/run_history_view.py`) now calls `MobSFDockerService(mobsf_api_url).prepare()` first (same start + API-key discovery as GUI launch and the CLI), in the worker thread so the UI stays responsive; a start failure is reported as "Could not start MobSF: ...". Only when `enable_mobsf_analysis` is on (otherwise `analyze_run` already refuses). Tests added in `tests/ui/test_run_history_view.py`; file green; not tried against real Docker.

Second follow-up: Run MobSF opens a non-modal `MobSFProgressDialog` (status line + read-only live log fed by the scan's `log_callback` via the worker's `log_message` signal, "Close" button that leaves the analysis running). It closes itself when the scan finishes or fails, then the existing result/error message box appears. Tests added; not seen in the real GUI.
