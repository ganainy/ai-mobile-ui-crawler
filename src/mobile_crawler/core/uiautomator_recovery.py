"""
UiAutomator2 crash detection and recovery management.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

# Error patterns that indicate a UiAutomator2 instrumentation crash
UIAUTOMATOR2_CRASH_PATTERNS: List[str] = [
    "instrumentation process is not running",
    "cannot be proxied to UiAutomator2 server",
    "UiAutomator2 server is not running",
    "session is either terminated or not started",
    "UiAutomator2 is not available",
]

def is_uiautomator2_crash(error: Exception) -> bool:
    """
    Check if the given exception indicates a UiAutomator2 crash.
    
    Args:
        error: The exception to check.
        
    Returns:
        True if the error message matches any of the crash patterns, False otherwise.
    """
    error_msg = str(error).lower()
    return any(pattern.lower() in error_msg for pattern in UIAUTOMATOR2_CRASH_PATTERNS)

@dataclass
class RecoveryConfig:
    """Configuration for UiAutomator2 crash recovery."""
    max_restart_attempts: int = 3
    restart_delay_seconds: float = 3.0
    emit_events: bool = True

@dataclass
class RecoveryState:
    """Tracks recovery attempts within a crawl step."""
    max_attempts: int = 3
    delay_seconds: float = 3.0
    current_attempts: int = 0
    last_recovery_time: Optional[datetime] = None
    
    def should_retry(self) -> bool:
        """Check if another recovery attempt is allowed."""
        return self.current_attempts < self.max_attempts
        
    def record_attempt(self) -> None:
        """Record a recovery attempt."""
        self.current_attempts += 1
        self.last_recovery_time = datetime.now()
        
    def reset(self) -> None:
        """Reset the attempt counter for a new step."""
        self.current_attempts = 0

@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    success: bool
    attempt_number: int
    duration_ms: float
    error_message: Optional[str] = None

class UiAutomatorRecoveryManager:
    """Manages UiAutomator2 crash detection and recovery."""
    
    def __init__(
        self,
        appium_driver: "AppiumDriver",
        config: Optional[RecoveryConfig] = None
    ):
        """
        Initialize the recovery manager.
        
        Args:
            appium_driver: The Appium driver instance to use for restarts.
            config: Optional recovery configuration.
        """
        self.appium_driver = appium_driver
        self.config = config or RecoveryConfig()
        self.state = RecoveryState(
            max_attempts=self.config.max_restart_attempts,
            delay_seconds=self.config.restart_delay_seconds
        )
        
    def is_uiautomator2_crash(self, error: Exception) -> bool:
        """Helper to check if an error is a crash."""
        return is_uiautomator2_crash(error)
        
    def attempt_recovery(self) -> RecoveryResult:
        """
        Attempt to restart UiAutomator2 and restore the session.
        
        Returns:
            RecoveryResult indicating success or failure.
        """
        start_time = time.time()
        self.state.record_attempt()  # Record the attempt
        attempt_number = self.state.current_attempts
        
        logger.warning(
            f"UiAutomator2 crash detected. Attempting recovery {attempt_number}/{self.state.max_attempts}..."
        )
        
        try:
            # The actual restart logic is in AppiumDriver
            self.appium_driver.restart_uiautomator2(delay_seconds=self.state.delay_seconds)
            
            duration_ms = (time.time() - start_time) * 1000
            
            logger.info(f"UiAutomator2 recovered successfully in {duration_ms:.0f}ms.")
            return RecoveryResult(
                success=True,
                attempt_number=attempt_number,
                duration_ms=duration_ms
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"Recovery attempt {attempt_number} failed: {error_msg}")
            
            return RecoveryResult(
                success=False,
                attempt_number=attempt_number,
                duration_ms=duration_ms,
                error_message=error_msg
            )
            
    def should_retry(self) -> bool:
        """Check if another recovery attempt is allowed."""
        return self.state.should_retry()
        
    def reset_for_new_step(self) -> None:
        """Reset weights and counters for a new step."""
        self.state.reset()
