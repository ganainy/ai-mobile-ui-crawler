# Data Model: Wire Up GUI Widgets

**Feature**: 001-wire-gui-widgets  
**Date**: 2026-01-10

## Entities

No new entities required. This feature wires existing components together.

### Existing Entities Used

#### CrawlSession (Runtime State - Not Persisted)

Managed by MainWindow to track current crawl configuration:

```
CrawlSession:
  - device: AndroidDevice (from DeviceSelector)
  - app_package: str (from AppSelector)
  - ai_provider: str (from AIModelSelector)
  - ai_model: str (from AIModelSelector)
  - run_id: int (from RunRepository after start)
  - state: CrawlState (from CrawlStateMachine)
```

#### Existing Persisted Entities

From `domain/models.py`:
- `Run`: Persisted crawl run record
- `StepLog`: Persisted step execution log
- `AIInteraction`: Persisted AI call record

From `infrastructure/device_detection.py`:
- `AndroidDevice`: Device information (not persisted)

## State Transitions

### Widget Enable/Disable State

```
State: UNCONFIGURED
  - DeviceSelector: enabled
  - AppSelector: disabled
  - AIModelSelector: enabled
  - Start button: disabled

State: DEVICE_SELECTED (device chosen)
  - DeviceSelector: enabled
  - AppSelector: enabled (loads packages)
  - AIModelSelector: enabled
  - Start button: disabled

State: READY (device + app + AI configured)
  - DeviceSelector: enabled
  - AppSelector: enabled
  - AIModelSelector: enabled
  - Start button: ENABLED

State: RUNNING (crawl active)
  - DeviceSelector: disabled
  - AppSelector: disabled
  - AIModelSelector: disabled
  - Start button: disabled
  - Pause button: enabled
  - Stop button: enabled

State: PAUSED
  - Resume button: visible, enabled
  - Pause button: hidden
  - Stop button: enabled

State: STOPPED
  - All selectors: enabled
  - Start button: enabled (if still configured)
  - Pause/Resume/Stop: disabled
```

## Validation Rules

1. **Device Selection**: Must have at least one available device
2. **App Selection**: Must select a valid package from device
3. **AI Configuration**: Provider and model must be set; API key validated
4. **Start Crawl**: All above conditions met + Appium server running
