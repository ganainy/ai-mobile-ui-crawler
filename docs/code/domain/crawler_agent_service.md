---
generated: true
file: src/mobile_crawler/domain/crawler_agent_service.py
---
# mobile_crawler.domain.crawler_agent_service

Internal crawler-agent service integration for Mobile Crawler.

Source: `src/mobile_crawler/domain/crawler_agent_service.py`

## Classes
- `CancelledErrorFilter`
- `CrawlerLogHandler`
- `CrawlerGoal`
- `CrawlerRunResult`
- `CrawlerAgentService`

## Imports
- [[code/config/config_manager|config.config_manager]]
- [[code/domain/action_verifier|domain.action_verifier]]
- [[code/domain/adb_action_executor|domain.adb_action_executor]]
- [[code/domain/context_guard|domain.context_guard]]
- [[code/domain/crawler_agent/agent/common/events|domain.crawler_agent.agent.common.events]]
- [[code/domain/crawler_agent/agent/droid/crawler_agent|domain.crawler_agent.agent.droid.crawler_agent]]
- [[code/domain/crawler_agent/agent/droid/events|domain.crawler_agent.agent.droid.events]]
- [[code/domain/crawler_agent/agent/executor/events|domain.crawler_agent.agent.executor.events]]
- [[code/domain/crawler_agent/agent/fast_agent/events|domain.crawler_agent.agent.fast_agent.events]]
- [[code/domain/crawler_agent/agent/manager/events|domain.crawler_agent.agent.manager.events]]
- [[code/domain/crawler_agent/config_manager/config_manager|domain.crawler_agent.config_manager.config_manager]]
- [[code/domain/errors|domain.errors]]
- [[code/domain/guided_scenarios_generator|domain.guided_scenarios_generator]]
- [[code/domain/models|domain.models]]
- [[code/domain/omni_parser_client|domain.omni_parser_client]]
- [[code/domain/prompt_builder|domain.prompt_builder]]
- [[code/domain/run_outcome|domain.run_outcome]]
- [[code/domain/stats_collector_span_processor|domain.stats_collector_span_processor]]
- [[code/domain/step_phase|domain.step_phase]]
- [[code/domain/step_phase_models|domain.step_phase_models]]
- [[code/domain/ui_context|domain.ui_context]]
- [[code/domain/ui_wait_predicate|domain.ui_wait_predicate]]
- [[code/infrastructure/ai_interaction_repository|infrastructure.ai_interaction_repository]]
- [[code/infrastructure/database|infrastructure.database]]
- [[code/infrastructure/step_phase_repository|infrastructure.step_phase_repository]]

## Imported by
- [[code/core/crawler_loop|core.crawler_loop]]
