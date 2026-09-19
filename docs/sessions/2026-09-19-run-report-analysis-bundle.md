---
author: claude
date: 2026-09-19
---
# Run Report + Analysis Bundle (grilling, then implementation of #6)

Goal: test the crawler on ~10 health apps and feed each run's data to an AI for improvement analysis.

## Grilling findings
`RunExporter` existed but was unused; the HTML `ReportGenerator` was manual only (no auto-report setting); no stop reason or guided-scenario progress was stored; Phoenix/Langfuse were write-only and no trace id was saved per run.

## Decisions
One merged report action (HTML + `analysis/` bundle); auto after each run via a default-on checkbox plus manual button/CLI; migration for `stop_reason` / `guided_progress_json` / `trace_id`; telemetry fetched only on manual generation; `RunExporter` deleted. `CONTEXT.md` gained Run Report, Analysis Bundle, Stop Reason. Spec filed as issue #6.

## What was built (all test-first)
- **Schema**: `runs.stop_reason`, `guided_progress_json`, `trace_id` (base table + migration); `RunRepository.update_run_stats(stop_reason=, guided_progress_json=)`, `update_trace_id`.
- **Run-time recording**: `domain/run_outcome.py` (`derive_stop_reason`: user_stop / step_limit / duration_limit / agent_finished / error: msg; `build_guided_progress`). `CrawlerAgentService.trace_session_id` (`run-<id>-<hex8>`) is set as the tracing session id, and `apply_session_context` now applies to Phoenix as well as Langfuse. `final_state` carries `stop_kind` and `guided_progress`.
- **Guided progress caveat**: the agent has no per-scenario "done" signal, so the snapshot stores the configured scenarios plus the agent's last plan and subgoal.
- **Config snapshot**: `domain/run_config_snapshot.py`, allowlisted keys only (no secrets), written to `<session>/data/config_snapshot.json` at run start, best effort.
- **Bundle**: `infrastructure/analysis_bundle.py` (`AnalysisBundleWriter`) writes `analysis/analysis.md`, `steps.jsonl`, `run.json`. Sections (`ReportSection` in `reporting/contracts.py`) are shared with the HTML template: Outcome, Summary, Config, Guided scenarios, Repeated actions, Failed steps, AI usage, Telemetry. HTML uses `| e` on section text.
- **Telemetry**: `infrastructure/telemetry_client.py`: `LangfuseTelemetryClient` (`GET /api/public/traces?sessionId=`, Basic Auth) and `PhoenixTelemetryClient` (`GET /v1/projects/{p}/spans`, filtered on `session.id`). Never raises; statuses ok / pending / unreachable / no_trace_id / not_configured. Provider is read from the run's config snapshot.
- **Triggers**: `CrawlerLoop(report_generator=)` generates after each run when `auto_generate_report_after_run` (default True) is on; Settings has a "Generate report after each run" checkbox; the run-history button and CLI `report` generate with telemetry; CLI `crawl --no-report` opts out. The fake `--format pdf|html` option was removed.
- `RunExporter` and its test deleted.

## Not verified
- Phoenix and Langfuse response shapes come from their docs, not a live server; tests use canned responses. Check against a real server before relying on the numbers.
- Langfuse trace objects carry latency and cost but not token counts, so tokens come from the Phoenix path or the local AI-usage section.
- The HTML `report_run_<id>.json` sibling written by `JinjaReportGenerator` still exists next to `analysis/run.json`.
- Two `test_wire_observers_*` tests fail on a clean `HEAD` too (pre-existing).
