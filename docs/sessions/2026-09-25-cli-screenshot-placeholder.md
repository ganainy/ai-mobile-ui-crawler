---
author: claude
date: 2026-09-25
---
# CLI: no base64 screenshot in `ai_request_sent`

User asked what the long `/9j/4AAQ...` string in the CLI's `ai_request_sent` JSON line was: the step's JPEG screenshot, base64-encoded by `CrawlerAgentService` into `request_data["user_prompt"]` for the AI Monitor panel. It is attached even when vision is off (default `vision: False`); `vision_enabled` in the same event says whether the model actually got the image.

## Change
- `cli/commands/crawl.py`: `JSONEventListener.on_ai_request_sent` prints a copy of `request_data` whose `user_prompt.screenshot` is `[BASE64_SCREENSHOT_REMOVED]` (same placeholder as the Analysis Bundle). The shared dict is not modified, so GUI/stats listeners are unaffected. Empty or non-JSON prompts are printed unchanged. The screenshot is still on disk and in `screenshot_captured`.
- Tests: `TestJSONEventListenerAiRequest` in `tests/cli/test_crawl_command.py`. `tests/cli` green; not tried in a real crawl.

## Side note
Screenshot bytes are JPEG but saved as `step_NNNN.png`; not changed.
