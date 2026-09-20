---
author: claude
---
# Remove OCR

The user asked to remove everything OCR-related, UI and code, since it was unused.

## Findings
- `domain/grounding/` (EasyOCR + Set-of-Mark overlay) had no callers outside its own package. The Stats panel already showed "Avg OCR: n/a (OCR not used)".
- Live parsing is OmniParser and/or the a11y tree (`ui_parser_mode`: boost / omniparser / accessibility). OmniParser runs its own OCR inside the Docker image; that is untouched.

## Removed
- `domain/grounding/` package and `tests/domain/grounding/`; `easyocr` dependency in `pyproject.toml`.
- Stats panel "Avg OCR" label and `ocr_avg_ms` argument; `CrawlStatistics` OCR fields and `avg_ocr_time_ms`.
- `on_ocr_completed` / `ocr_completed` in the event listener, signal adapter, CLI listener and main window.
- `ocr_avg_ms` from `on_crawl_completed` (listener, adapter, CLI JSON event, main window, `crawler_loop.py`).
- `PromptBuilder.build_user_prompt` `ocr_grounding` parameter and suggested-input block; the "Set-of-Mark" section and `label_id` prompt lines in `prompts.py`.
- OCR wording in Settings tooltips, comments, and the `CONTEXT.md` Status Bar Exclusion entry.

## Left alone
- `ActionResult.label_id` in `models.py` and its uses in `state_graph.py` / `ai_monitor_panel.py` (dead but not OCR-named).
- Dockerfile PaddleOCR patch (OmniParser needs it).
- `PromptBuilder.build_user_prompt` still has no live callers; `app_package` is now unused there.

Full suite: 1471 passed, 7 skipped.
