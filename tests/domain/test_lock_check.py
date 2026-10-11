"""A foreign foreground that is really the lock screen stops the run with a clear error."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from tests.domain.test_droidrun_target_package_guards import android_state_provider  # noqa: F401


@pytest.mark.asyncio
async def test_locked_device_raises(android_state_provider):  # noqa: F811
    provider, _ = android_state_provider
    mock_adb = Mock()
    mock_adb.get_current_package.return_value = "com.android.systemui"
    mock_adb.ensure_device_ready_for_crawl.return_value = SimpleNamespace(
        success=False, keyguard_locked=True, screen_on=True, error_message="Device is locked. Unlock it manually"
    )
    with patch("mobile_crawler.domain.adb_action_executor.ADBActionExecutor", return_value=mock_adb):
        with pytest.raises(RuntimeError, match="locked"):
            await provider.get_state()


@pytest.mark.asyncio
async def test_unreadable_lock_state_does_not_abort(android_state_provider):  # noqa: F811
    provider, _ = android_state_provider
    mock_adb = Mock()
    mock_adb.get_current_package.return_value = "com.android.systemui"
    mock_adb.ensure_device_ready_for_crawl.return_value = SimpleNamespace(
        success=False, keyguard_locked=None, screen_on=True, error_message="Unable to read device lock state"
    )
    with patch("mobile_crawler.domain.adb_action_executor.ADBActionExecutor", return_value=mock_adb):
        await provider.get_state()  # within the default grace: no raise
