---
author: claude
updated: 2026-09-26
---
# Live Feed shows the cropped strips

User asked why the Live view still showed the top status bar and bottom nav bar despite the Status Bar / Bottom Bar Exclusion. Cause: the exclusion is applied in `AndroidDriver.screenshot()` (capture sent to hashing/AI, ADR-0002); the Live Feed is the raw scrcpy stream and never read those settings, so it was working as designed.

Change: the Live view is not cropped; `_LiveFeedView` paints a semi-transparent dark band labelled "Cropped" over the top and bottom exclusion strips (`set_exclusions`, `_paint_cropped_bands` in `ui/widgets/stats_dashboard.py`). `MainWindow` passes `top_bar_height` / `bottom_bar_height` when a run starts (`StatsDashboard.set_live_exclusions`), so changing the settings takes effect on the next run. Test added in `tests/ui/test_stats_dashboard.py` (green); not seen in the real GUI.

## Follow-up: a11y tree respects the exclusion

The Portal a11y tree covers the whole screen in absolute device px and was never trimmed (only OmniParser bboxes were offset for the crop), so the AI got status-bar and nav-bar elements the screenshot no longer showed. New `exclude_bars` (`domain/crawler_agent/tools/ui/a11y_exclusion.py`) drops nodes entirely inside the top strip (`bottom <= top_px`) or bottom strip (`top >= screen_h - bottom_px`); overlapping nodes and roots stay, and a dropped node's surviving children move up. `provider.get_state` applies it right after reading the tree, so the incomplete-tree checks see the trimmed tree too (node count / coverage are now measured on the visible area). Tests in `tests/domain/test_a11y_exclusion.py`; `tests/domain` green; not tried on the phone.
