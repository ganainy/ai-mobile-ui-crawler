---
author: claude
date: 2026-09-19
---
# Executor MAX_TOKENS crash (run 171)

- Symptom: crawl ended after 0 steps; executor LLM (`gemini-3.8-flash`) returned `Response was terminated early: MAX_TOKENS` on all 3 retries, each cut off a few words into "### Thought ###".
- Cause (likely): `llm_profiles` in `crawler_agent_service.py` capped executor at `max_tokens=512`. Gemini thinking tokens count against the output limit, so the visible answer was truncated. Not confirmed by inspecting the API response.
- Fix: manager 2048 -> 8192, executor 512 -> 4096, app_opener 512 -> 2048.
- Verified working by the user on a real run. If it recurs, set a low thinking level/budget for the executor instead.
- Side note: `inference.py` retries identical requests on MAX_TOKENS, so retries can never help.
