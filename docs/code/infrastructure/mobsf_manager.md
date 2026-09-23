---
generated: true
file: src/mobile_crawler/infrastructure/mobsf_manager.py
---
# mobile_crawler.infrastructure.mobsf_manager

MobSF Manager for APK analysis.

Source: `src/mobile_crawler/infrastructure/mobsf_manager.py`

## Classes
- `MobSFAnalysisResult`
- `MobSFManager`

## Functions
- `extract_api_key_from_logs`
- `find_api_key_file`
- `api_key_write_path`
- `save_api_key_file`

## Imports
- [[code/config/config_manager|config.config_manager]]
- [[code/config/defaults|config.defaults]]
- [[code/domain/run_folder_layout|domain.run_folder_layout]]
- [[code/infrastructure/adb_client|infrastructure.adb_client]]
- [[code/infrastructure/database|infrastructure.database]]
- [[code/infrastructure/run_repository|infrastructure.run_repository]]
- [[code/infrastructure/session_folder_manager|infrastructure.session_folder_manager]]

## Imported by
- [[code/cli/commands/mobsf_scan|cli.commands.mobsf_scan]]
- [[code/core/crawler_loop|core.crawler_loop]]
- [[code/core/pre_crawl_validator|core.pre_crawl_validator]]
- [[code/infrastructure/mobsf_docker|infrastructure.mobsf_docker]]
- [[code/ui/main_window|ui.main_window]]
- [[code/ui/widgets/run_history_view|ui.widgets.run_history_view]]
