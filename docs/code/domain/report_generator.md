---
generated: true
file: src/mobile_crawler/domain/report_generator.py
---
# mobile_crawler.domain.report_generator

Enhanced HTML/JSON report generator for crawl runs.

Source: `src/mobile_crawler/domain/report_generator.py`

## Classes
- `ReportGenerator`

## Imports
- [[code/domain/run_config_snapshot|domain.run_config_snapshot]]
- [[code/infrastructure/ai_interaction_repository|infrastructure.ai_interaction_repository]]
- [[code/infrastructure/analysis_bundle|infrastructure.analysis_bundle]]
- [[code/infrastructure/database|infrastructure.database]]
- [[code/infrastructure/run_repository|infrastructure.run_repository]]
- [[code/infrastructure/step_log_repository|infrastructure.step_log_repository]]
- [[code/infrastructure/telemetry_client|infrastructure.telemetry_client]]
- [[code/reporting/correlator|reporting.correlator]]
- [[code/reporting/generator|reporting.generator]]
- [[code/reporting/parsers/mobsf_parser|reporting.parsers.mobsf_parser]]
- [[code/reporting/parsers/pcap_parser|reporting.parsers.pcap_parser]]

## Imported by
- [[code/cli/commands/crawl|cli.commands.crawl]]
- [[code/cli/commands/report|cli.commands.report]]
- [[code/ui/main_window|ui.main_window]]
- [[code/ui/widgets/run_history_view|ui.widgets.run_history_view]]
