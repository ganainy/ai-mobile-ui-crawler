---
generated: true
file: src/mobile_crawler/core/crawler_loop.py
---
# mobile_crawler.core.crawler_loop

Crawler-agent-backed crawl lifecycle wrapper.

Source: `src/mobile_crawler/core/crawler_loop.py`

## Classes
- `CrawlerLoop`

## Imports
- [[code/config/config_manager|config.config_manager]]
- [[code/core/crawl_state_machine|core.crawl_state_machine]]
- [[code/core/crawler_event_listener|core.crawler_event_listener]]
- [[code/core/log_sinks|core.log_sinks]]
- [[code/domain/adb_action_executor|domain.adb_action_executor]]
- [[code/domain/crawler_agent_service|domain.crawler_agent_service]]
- [[code/domain/errors|domain.errors]]
- [[code/domain/traffic_capture_manager|domain.traffic_capture_manager]]
- [[code/domain/video_recording_manager|domain.video_recording_manager]]
- [[code/infrastructure/mobsf_manager|infrastructure.mobsf_manager]]
- [[code/infrastructure/run_repository|infrastructure.run_repository]]
- [[code/infrastructure/session_folder_manager|infrastructure.session_folder_manager]]

## Imported by
- [[code/cli/commands/crawl|cli.commands.crawl]]
- [[code/ui/main_window|ui.main_window]]
