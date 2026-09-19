---
generated: true
file: src/mobile_crawler/domain/crawler_agent/tools/ui/provider.py
---
# mobile_crawler.domain.crawler_agent.tools.ui.provider

StateProvider — orchestrates fetching and parsing device state.

Source: `src/mobile_crawler/domain/crawler_agent/tools/ui/provider.py`

## Classes
- `StateProvider`
- `AndroidStateProvider`

## Functions
- `fetch_state_with_retry`

## Imports
- [[code/domain/adb_action_executor|domain.adb_action_executor]]
- [[code/domain/crawler_agent/tools/driver/base|domain.crawler_agent.tools.driver.base]]
- [[code/domain/crawler_agent/tools/filters/_index|domain.crawler_agent.tools.filters]]
- [[code/domain/crawler_agent/tools/formatters/_index|domain.crawler_agent.tools.formatters]]
- [[code/domain/crawler_agent/tools/omniparser_client|domain.crawler_agent.tools.omniparser_client]]
- [[code/domain/crawler_agent/tools/ui/state|domain.crawler_agent.tools.ui.state]]
- [[code/domain/crawler_agent/tools/ui/stealth_state|domain.crawler_agent.tools.ui.stealth_state]]
- [[code/domain/state_graph|domain.state_graph]]

## Imported by
- [[code/domain/crawler_agent/agent/action_context|domain.crawler_agent.agent.action_context]]
- [[code/domain/crawler_agent/agent/droid/crawler_agent|domain.crawler_agent.agent.droid.crawler_agent]]
- [[code/domain/crawler_agent/agent/fast_agent/fast_agent|domain.crawler_agent.agent.fast_agent.fast_agent]]
- [[code/domain/crawler_agent/agent/manager/manager_agent|domain.crawler_agent.agent.manager.manager_agent]]
- [[code/domain/crawler_agent/agent/manager/stateless_manager_agent|domain.crawler_agent.agent.manager.stateless_manager_agent]]
- [[code/domain/crawler_agent/tools/ui/_index|domain.crawler_agent.tools.ui]]
