"""The run aborts after repeated captures with no UI elements, in any parser mode."""

import pytest

from tests.domain.test_droidrun_target_package_guards import android_state_provider  # noqa: F401


@pytest.mark.asyncio
async def test_omniparser_only_mode_aborts_when_nothing_is_ever_parsed(android_state_provider):  # noqa: F811
    provider, driver = android_state_provider
    # a11y tree has a node, OmniParser finds nothing, the formatter yields no elements
    provider._get_omni_parser_elements.return_value = []
    provider.tree_formatter.format.return_value = ("formatted", "", [], {})
    from unittest.mock import Mock, patch

    mock_adb = Mock()
    mock_adb.get_current_package.return_value = "com.example.app"
    with patch("mobile_crawler.domain.adb_action_executor.ADBActionExecutor", return_value=mock_adb):
        with pytest.raises(RuntimeError, match="No UI elements for 6 consecutive captures"):
            for _ in range(10):
                await provider.get_state()
