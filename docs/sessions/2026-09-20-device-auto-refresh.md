---
author: claude
date: 2026-09-20
---
# Device selector: auto-retry at startup, last-used selection

**Problem:** GUI showed the "No Devices Found" dialog on start; a manual Refresh then found the device (first adb query came back empty).

**Changes** (`ui/widgets/device_selector.py`, `ui/main_window.py`):
- New `DeviceSelector.auto_refresh()` (used at startup): retries up to 3 times, 1.5 s apart, before showing the no-devices warning or detection-error dialog. Manual Refresh still reports immediately.
- Selection order after a refresh: current selection, then `last_device_id` from the config store, then the first device.
- Bug fixed on the way: `combo.clear()`/`addItem()` fired `_on_device_changed`, which deleted or overwrote `last_device_id`. It is now read before repopulating and never deleted on an empty combo.

**Tests:** `TestAutoRefresh` in `tests/ui/test_device_selector.py`; `tests/ui` all pass. Not tried on a real device.
