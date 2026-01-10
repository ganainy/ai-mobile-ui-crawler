# Widget Signal Contracts

**Feature**: 001-wire-gui-widgets  
**Date**: 2026-01-10

## Overview

This feature uses internal Qt signals rather than external APIs. Below are the signal/slot contracts between widgets.

## Signal Definitions

### DeviceSelector Signals

```python
# Emitted when user selects a device
device_selected = Signal(object)  # AndroidDevice

# Usage in MainWindow:
self.device_selector.device_selected.connect(self._on_device_selected)

def _on_device_selected(self, device: AndroidDevice):
    self._selected_device = device
    self.app_selector.set_device(device.device_id)
    self._update_start_button_state()
```

### AppSelector Signals

```python
# Emitted when user selects an app
app_selected = Signal(str)  # package_name

# Usage in MainWindow:
self.app_selector.app_selected.connect(self._on_app_selected)

def _on_app_selected(self, package: str):
    self._selected_package = package
    self._update_start_button_state()
```

### AIModelSelector Signals

```python
# Emitted when user selects provider and model
model_selected = Signal(str, str)  # provider, model

# Usage in MainWindow:
self.ai_selector.model_selected.connect(self._on_model_selected)

def _on_model_selected(self, provider: str, model: str):
    self._ai_provider = provider
    self._ai_model = model
    self._update_start_button_state()
```

### CrawlControlPanel Signals

```python
start_requested = Signal()
pause_requested = Signal()
resume_requested = Signal()
stop_requested = Signal()

# Usage in MainWindow:
self.control_panel.start_requested.connect(self._start_crawl)
self.control_panel.pause_requested.connect(self._pause_crawl)
self.control_panel.resume_requested.connect(self._resume_crawl)
self.control_panel.stop_requested.connect(self._stop_crawl)
```

### QtSignalAdapter Signals (from CrawlerLoop)

```python
# Progress signals
step_started = Signal(int, int)           # run_id, step_number
step_completed = Signal(int, int, int, float)  # run_id, step_number, actions, duration_ms
crawl_completed = Signal(int, int, float, str)  # run_id, steps, duration_ms, reason

# Logging signals
screenshot_captured = Signal(int, int, str)
action_executed = Signal(int, int, int, object)
error_occurred = Signal(int, int, object)

# State signals
state_changed = Signal(int, str, str)  # run_id, old_state, new_state
```

## Slot Signatures (MainWindow)

```python
def _on_device_selected(self, device: AndroidDevice) -> None
def _on_app_selected(self, package: str) -> None
def _on_model_selected(self, provider: str, model: str) -> None
def _start_crawl(self) -> None
def _pause_crawl(self) -> None
def _resume_crawl(self) -> None
def _stop_crawl(self) -> None
def _on_step_completed(self, run_id: int, step: int, actions: int, duration: float) -> None
def _on_crawl_completed(self, run_id: int, steps: int, duration: float, reason: str) -> None
def _update_start_button_state(self) -> None
```
