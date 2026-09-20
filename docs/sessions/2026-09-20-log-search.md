---
author: claude
---
# Log search + OmniParser timing log level

- `ui/widgets/log_viewer.py`: search box, Regex checkbox and shown/total label. Filtering is `_passes_filters` (level + search) used by both live append and `_rebuild_display`; invalid regex shows a red border and matches everything.
- `domain/crawler_agent/tools/ui/provider.py`: OmniParser timing log `logger.debug` -> `logger.info`.
- Verified with an offscreen Qt smoke script only; no unit tests added.
