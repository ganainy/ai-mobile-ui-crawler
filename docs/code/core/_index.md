---
generated: partial
---
# mobile_crawler.core

<!-- summary:start -->
Crawl orchestration: crawl controller, state machine, main crawler loop, stuck/pre-crawl checks, run logging and runtime stats.
<!-- summary:end -->

## Modules
- [[code/core/crawl_controller|core.crawl_controller]] - Crawl controller for pause/resume/stop controls.
- [[code/core/crawl_state_machine|core.crawl_state_machine]] - Crawl state machine for managing crawler lifecycle.
- [[code/core/crawler_event_listener|core.crawler_event_listener]] - Protocol for crawler event listeners.
- [[code/core/crawler_loop|core.crawler_loop]] - Crawler-agent-backed crawl lifecycle wrapper.
- [[code/core/log_sinks|core.log_sinks]] - Log sinks for multi-sink logging architecture.
- [[code/core/logging_service|core.logging_service]] - Logging service with multi-sink architecture.
- [[code/core/portal_actions|core.portal_actions]] - Blocking Portal check / enable / install helpers, shared by the Settings panel and the CLI.
- [[code/core/pre_crawl_validator|core.pre_crawl_validator]] - Pre-crawl validation for ensuring all requirements are met.
- [[code/core/pre_run_warnings|core.pre_run_warnings]] - Pre-run warnings: problems that do not stop a crawl but make it worse than the settings promise.
- [[code/core/run_stats_recorder|core.run_stats_recorder]] - Run Stats recording: fills a RuntimeStatsCollector from crawler events and saves it to run_stats.
- [[code/core/run_stats_sections|core.run_stats_sections]] - Qt-free layout and formatting of a persisted run_stats record.
- [[code/core/runtime_stats_collector|core.runtime_stats_collector]] - Runtime statistics collector for crawl sessions.
- [[code/core/stale_run_cleaner|core.stale_run_cleaner]] - Stale run cleanup for recovering crashed crawl sessions.
- [[code/core/stuck_detector|core.stuck_detector]] - Stuck detector for identifying when crawler is stuck on the same screen.
