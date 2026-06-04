# Contracts: UiAutomator2 Crash Detection and Recovery

**Feature**: 023-uiautomator-crash-recovery  
**Date**: 2026-01-15

## Overview

This feature does not introduce external API contracts. All interfaces are internal Python classes and methods.

## Internal Interfaces

### UiAutomatorRecoveryManager

```python
class UiAutomatorRecoveryManager:
    """Manages UiAutomator2 crash detection and recovery."""
    
    def __init__(
        self,
        appium_driver: AppiumDriver,
        max_attempts: int = 3,
        delay_seconds: float = 3.0
    ) -> None: ...
    
    def is_uiautomator2_crash(self, error: Exception) -> bool:
        """Check if error indicates UiAutomator2 crash."""
        ...
    
    def attempt_recovery(self) -> RecoveryResult:
        """Attempt to restart UiAutomator2 and restore session."""
        ...
    
    def should_retry(self) -> bool:
        """Check if another recovery attempt is allowed."""
        ...
    
    def reset_for_new_step(self) -> None:
        """Reset attempt counter for new crawl step."""
        ...
```

### Event Contracts

See `data-model.md` for event parameter specifications.
