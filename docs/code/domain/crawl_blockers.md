---
generated: true
file: src/mobile_crawler/domain/crawl_blockers.py
---
# mobile_crawler.domain.crawl_blockers

Things outside the crawler that make a crawl impossible, classified into a clear user-facing message.

Source: `src/mobile_crawler/domain/crawl_blockers.py`

## Classes
- `CrawlBlockedError`

## Functions
- `screenshot_blocked_error`
- `device_lost_error`
- `is_blank_screenshot`
- `find_crawl_blocked_error`

## Imported by
- [[code/core/crawler_loop|core.crawler_loop]]
- [[code/domain/crawler_agent/tools/driver/android|domain.crawler_agent.tools.driver.android]]
- [[code/domain/crawler_agent/tools/ui/provider|domain.crawler_agent.tools.ui.provider]]
- [[code/domain/crawler_agent_service|domain.crawler_agent_service]]
- [[code/ui/main_window|ui.main_window]]
