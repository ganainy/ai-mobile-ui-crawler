---
generated: true
file: src/mobile_crawler/core/pre_run_warnings.py
---
# mobile_crawler.core.pre_run_warnings

Pre-run warnings: problems that do not stop a crawl but make it worse than the settings promise.

Source: `src/mobile_crawler/core/pre_run_warnings.py`

## Classes
- `PreRunWarning`

## Functions
- `collect_pre_run_warnings`

## Imports
- [[code/domain/crawler_agent/agent/utils/tracing_setup|domain.crawler_agent.agent.utils.tracing_setup]]
- [[code/domain/crawler_agent/portal|domain.crawler_agent.portal]]
- [[code/infrastructure/phoenix_docker|infrastructure.phoenix_docker]]

## Imported by
- [[code/cli/commands/crawl|cli.commands.crawl]]
- [[code/ui/main_window|ui.main_window]]
