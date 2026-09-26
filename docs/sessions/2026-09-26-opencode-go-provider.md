---
author: claude
updated: 2026-09-26
---
# OpenCode Go provider (#30)

Implemented the design from [the grill](2026-09-26-opencode-go-provider-grill.md).

- `domain/opencode_go.py`: base URL, default model `kimi-k3`, id-prefix filter, vision flag, `OpenCodeGoLimitError`, 429 detection.
- `acall_with_retries` raises the limit error at once (no retries) when the LLM's `api_base` is OpenCode Go and the status is 429; other providers keep retrying.
- `OpenAILike` defaults to a 3900-token context window, so `context_window=128000` is passed with `api_base`.
- Vision is off by default in the agent config, so "text-only" needed no change; the model list only flags the one vision id.
- Key check posts a one-token chat call (no key endpoint; `/models` is public). 429 still counts as "Key works".
- Wired: service config, guided scenarios, model selector, settings panel, main window, pre-crawl validator, CLI help, `docs/cli.md`, README.

Not tried: a real subscription, the GUI, whether `kimi-k3` handles the agent prompts.

## Follow-up: "Key rejected"
The user's console log showed the Test call arrived as product `go` on `/inference/go/openai/v1/chat/completions` and returned 400 `inference_failed` (kimi-k3, max_tokens 1). The key was valid; the check mapped 400 to "Key rejected". Fixed: only 401/403 reject, 400 counts as accepted, max_tokens 16. The cause of the 400 is not known.
