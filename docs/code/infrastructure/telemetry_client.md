---
generated: true
file: src/mobile_crawler/infrastructure/telemetry_client.py
---
# mobile_crawler.infrastructure.telemetry_client

Reads a run's telemetry back from Phoenix or Langfuse, by the run's trace session id.

Source: `src/mobile_crawler/infrastructure/telemetry_client.py`

## Classes
- `TelemetrySummary`
- `TelemetryClient`
- `LangfuseTelemetryClient`
- `PhoenixTelemetryClient`

## Functions
- `fetch_run_telemetry`
- `build_telemetry_client_factory`

## Imported by
- [[code/cli/commands/crawl|cli.commands.crawl]]
- [[code/cli/commands/report|cli.commands.report]]
- [[code/domain/report_generator|domain.report_generator]]
- [[code/infrastructure/analysis_bundle|infrastructure.analysis_bundle]]
- [[code/ui/main_window|ui.main_window]]
