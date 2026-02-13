import pytest
from unittest.mock import MagicMock
from selenium.common.exceptions import WebDriverException
from mobile_crawler.core.uiautomator_recovery import (
    is_uiautomator2_crash,
    RecoveryState,
    RecoveryConfig,
    UiAutomatorRecoveryManager
)

def test_is_uiautomator2_crash_detects_instrumentation_error():
    """Crash pattern should be detected for instrumentation error."""
    error = WebDriverException("The instrumentation process is not running (probably crashed)")
    assert is_uiautomator2_crash(error) is True

def test_is_uiautomator2_crash_detects_proxy_error():
    """Crash pattern should be detected for proxy error."""
    error = WebDriverException("cannot be proxied to UiAutomator2 server because the instrumentation process is not running")
    assert is_uiautomator2_crash(error) is True

def test_is_uiautomator2_crash_ignores_regular_errors():
    """Regular errors should not be flagged as crashes."""
    error = WebDriverException("An element could not be located on the page using the given search parameters.")
    assert is_uiautomator2_crash(error) is False
    
    error2 = Exception("General python error")
    assert is_uiautomator2_crash(error2) is False

def test_recovery_state_should_retry_within_limits():
    """Should allow retries up to max_attempts."""
    state = RecoveryState(max_attempts=3)
    assert state.should_retry() is True
    
    state.record_attempt() # 1
    assert state.should_retry() is True
    
    state.record_attempt() # 2
    assert state.should_retry() is True
    
    state.record_attempt() # 3
    assert state.should_retry() is False

def test_recovery_state_resets_on_success():
    """Counter should reset after a successful recovery/action."""
    state = RecoveryState(max_attempts=3)
    state.record_attempt()
    state.record_attempt()
    assert state.current_attempts == 2
    
    state.reset()
    assert state.current_attempts == 0
    assert state.should_retry() is True

def test_recovery_state_reset_manual():
    """Manual reset should clear attempts."""
    state = RecoveryState(max_attempts=3)
    state.record_attempt()
    state.reset()
    assert state.current_attempts == 0

def test_recovery_respects_max_attempts():
    """Verify that should_retry correctly enforces max_attempts."""
    state = RecoveryState(max_attempts=2)
    assert state.should_retry() is True
    
    state.record_attempt() # Attempt 1
    assert state.current_attempts == 1
    assert state.should_retry() is True
    
    state.record_attempt() # Attempt 2
    assert state.current_attempts == 2
    assert state.should_retry() is False

def test_recovery_manager_uses_config_values():
    """Verify that RecoveryManager correctly initializes state from config."""
    config = RecoveryConfig(max_restart_attempts=5, restart_delay_seconds=10.0)
    mock_driver = MagicMock()
    manager = UiAutomatorRecoveryManager(mock_driver, config)
    
    assert manager.state.max_attempts == 5
    assert manager.state.delay_seconds == 10.0
