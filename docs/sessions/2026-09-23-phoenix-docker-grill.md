---
author: claude
date: 2026-09-23
---
# Phoenix in Docker (design grill)

User asked whether the Phoenix tracing server should move to Docker like MobSF and OmniParser. Grilled the design; no code changed.

## Decided
- Phoenix becomes the third **Managed Service** (new `CONTEXT.md` term; Pre-run Warning entry reworded to use it).
- Auto-started like MobSF/OmniParser: GUI at launch + when tracing is turned on + blocking check before a crawl; CLI before a crawl. Only for a localhost `phoenix_url`; reuse a Phoenix already answering `/healthz`; port held by something else or failed start -> Pre-run Warning.
- Image pinned to `arizephoenix/phoenix:version-20.3.0`; `~/.phoenix` bind-mounted so old traces stay readable.
- GUI exit dialog gets a Phoenix checkbox; CLI leaves it running.
- `arize-phoenix` pip dependency to be dropped (keep `llama-index-callbacks-arize-phoenix`).

## Found on the way
- Default `mobsf_api_url` is `http://localhost:8001`, which is OmniParser's port; MobSF is published on 8000.

## Filed
- [#27](https://github.com/ganainy/ai-mobile-ui-crawler/issues/27) Phoenix as a Managed Service.
- [#28](https://github.com/ganainy/ai-mobile-ui-crawler/issues/28) MobSF default port.

## Open
- Whether SQLite over a Windows Docker bind mount holds up (fallback: named volume + one-time copy).
- Whether the callbacks package imports `phoenix` itself.
