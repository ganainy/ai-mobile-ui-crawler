---
generated: true
file: src/mobile_crawler/domain/llm_errors.py
---
# mobile_crawler.domain.llm_errors

A failed AI model call, classified into a clear user-facing message.

Source: `src/mobile_crawler/domain/llm_errors.py`

## Classes
- `LLMCallError`

## Functions
- `is_fatal_llm_error`
- `classify_llm_error`
- `find_llm_call_error`
- `model_name`

## Imported by
- [[code/core/crawler_loop|core.crawler_loop]]
- [[code/domain/crawler_agent/agent/executor/executor_agent|domain.crawler_agent.agent.executor.executor_agent]]
- [[code/domain/crawler_agent/agent/manager/manager_agent|domain.crawler_agent.agent.manager.manager_agent]]
- [[code/domain/crawler_agent/agent/utils/inference|domain.crawler_agent.agent.utils.inference]]
- [[code/domain/crawler_agent_service|domain.crawler_agent_service]]
- [[code/domain/opencode_go|domain.opencode_go]]
- [[code/ui/main_window|ui.main_window]]
