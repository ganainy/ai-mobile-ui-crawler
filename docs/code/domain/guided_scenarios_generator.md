---
generated: true
file: src/mobile_crawler/domain/guided_scenarios_generator.py
---
# mobile_crawler.domain.guided_scenarios_generator

Generates a Guided Scenarios list for an app from its App Web Profile.

Source: `src/mobile_crawler/domain/guided_scenarios_generator.py`

## Classes
- `GuidedScenariosResult`

## Functions
- `guided_scenarios_config_key`
- `guided_scenarios_url_override_config_key`
- `generate_guided_scenarios`

## Imports
- [[code/config/config_manager|config.config_manager]]
- [[code/domain/crawler_agent/agent/utils/inference|domain.crawler_agent.agent.utils.inference]]
- [[code/domain/crawler_agent/agent/utils/llm_picker|domain.crawler_agent.agent.utils.llm_picker]]
- [[code/infrastructure/app_web_profile_resolver|infrastructure.app_web_profile_resolver]]

## Imported by
- [[code/cli/commands/scenarios|cli.commands.scenarios]]
- [[code/domain/crawler_agent_service|domain.crawler_agent_service]]
- [[code/domain/run_config_snapshot|domain.run_config_snapshot]]
- [[code/ui/main_window|ui.main_window]]
