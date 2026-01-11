# API Contracts: Fix Settings Persistence

**Feature**: 001-fix-settings-persistence  
**Date**: 2026-01-11  
**Status**: N/A

## Overview

This feature does not expose any external APIs. It modifies internal widget classes and their interaction with the existing `UserConfigStore` class.

---

## Internal Interface Changes

### Widget Constructor Signatures

The following widget classes will have modified constructor signatures:

#### DeviceSelector

```python
# Before
def __init__(self, device_detection: DeviceDetection, parent=None)

# After
def __init__(
    self, 
    device_detection: DeviceDetection, 
    config_store: "UserConfigStore",
    parent=None
)
```

#### AppSelector

```python
# Before
def __init__(self, appium_driver: AppiumDriver, parent=None)

# After
def __init__(
    self, 
    appium_driver: AppiumDriver, 
    config_store: "UserConfigStore",
    parent=None
)
```

#### AIModelSelector

```python
# Before
def __init__(
    self, 
    provider_registry: ProviderRegistry, 
    vision_detector: VisionDetector, 
    parent=None
)

# After
def __init__(
    self, 
    provider_registry: ProviderRegistry, 
    vision_detector: VisionDetector,
    config_store: "UserConfigStore",
    parent=None
)
```

---

## No REST/GraphQL/RPC Contracts

This is a desktop application with no network API surface. All persistence is local SQLite storage accessed through the `UserConfigStore` class.
