---
generated: true
file: src/mobile_crawler/config/config_manager.py
---
# mobile_crawler.config.config_manager

Configuration manager with precedence: SQLite → environment variables → module defaults.

Source: `src/mobile_crawler/config/config_manager.py`

## Classes
- `ConfigManager`

## Functions
- `get_config`

## Imports
- [[code/config/defaults|config.defaults]]
- [[code/infrastructure/user_config_store|infrastructure.user_config_store]]

## Imported by
- [[code/cli/commands/config|cli.commands.config]]
- [[code/cli/commands/crawl|cli.commands.crawl]]
- [[code/config/_index|config]]
- [[code/core/crawler_loop|core.crawler_loop]]
- [[code/domain/crawler_agent_service|domain.crawler_agent_service]]
- [[code/domain/guided_scenarios_generator|domain.guided_scenarios_generator]]
- [[code/domain/input_dictionary|domain.input_dictionary]]
- [[code/domain/prompt_builder|domain.prompt_builder]]
- [[code/domain/traffic_capture_manager|domain.traffic_capture_manager]]
- [[code/domain/video_recording_manager|domain.video_recording_manager]]
- [[code/infrastructure/mobsf_manager|infrastructure.mobsf_manager]]
- [[code/ui/main_window|ui.main_window]]
