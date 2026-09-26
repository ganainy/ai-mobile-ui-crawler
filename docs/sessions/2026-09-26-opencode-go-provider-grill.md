---
author: claude
updated: 2026-09-26
---
# OpenCode Go provider grill

Goal: use the OpenCode Go subscription (opencode.ai/go) as an AI Provider. Outcome: design agreed, issue #30 filed (`ready-for-agent`), `CONTEXT.md` gained **AI Provider**. No code changed.

## Facts found
- Base URL `https://opencode.ai/zen/go/v1`; `/models` is public and lists ids only (no modalities or endpoint family).
- Three endpoint families by model: `chat/completions` (GLM, Kimi, DeepSeek, LongCat, Hy), `responses` (GPT Luna, Grok, Muse Spark), Anthropic `messages` (MiniMax, Qwen).
- Only `deepseek-v4-flash-vision-exp` takes images.
- Limits: 20% of monthly per 5 h, 50% weekly, 100% monthly; blocked past that unless "Use balance" is on. Error format undocumented.
- The crawler has no 429/rate-limit handling today.

## Decisions
- Named provider "OpenCode Go" with its own key + Test button, fixed base URL, via `OpenAILike`.
- Used by crawl, Guided Scenarios, CLI `--provider`; not Jev.
- Live `/models`, filtered to the `chat/completions` family by id prefix; other families hidden for now.
- One model for all agent roles; default `kimi-k3` (untested).
- Text-only except the one vision id.
- Limit error -> run ends with a named message; no retry.
- No ADR.
