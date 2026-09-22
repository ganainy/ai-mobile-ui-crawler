---
generated: true
file: src/mobile_crawler/infrastructure/run_repository.py
---
# mobile_crawler.infrastructure.run_repository

Repository for managing crawl runs in crawler.db.

Source: `src/mobile_crawler/infrastructure/run_repository.py`

## Classes
- `Run`
- `RunRepository`

## Imports
- [[code/domain/errors|domain.errors]]
- [[code/infrastructure/database|infrastructure.database]]

## Imported by
- [[code/cli/commands/crawl|cli.commands.crawl]]
- [[code/cli/commands/delete|cli.commands.delete]]
- [[code/cli/commands/list|cli.commands.list]]
- [[code/cli/commands/stats|cli.commands.stats]]
- [[code/core/crawler_loop|core.crawler_loop]]
- [[code/core/stale_run_cleaner|core.stale_run_cleaner]]
- [[code/domain/report_generator|domain.report_generator]]
- [[code/domain/traffic_capture_manager|domain.traffic_capture_manager]]
- [[code/infrastructure/analysis_bundle|infrastructure.analysis_bundle]]
- [[code/infrastructure/mobsf_manager|infrastructure.mobsf_manager]]
- [[code/infrastructure/session_folder_manager|infrastructure.session_folder_manager]]
- [[code/ui/main_window|ui.main_window]]
- [[code/ui/widgets/run_history_view|ui.widgets.run_history_view]]
