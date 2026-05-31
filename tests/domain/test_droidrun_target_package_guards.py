"""Tests for DroidRun target-package guards before state capture and app open."""

import sys
import types
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mobile_crawler.domain.models import ActionResult as CrawlerActionResult


REPO_ROOT = Path(__file__).resolve().parents[2]
DROIDRUN_ROOT = REPO_ROOT / "src" / "mobile_crawler" / "domain" / "crawler_agent"
if str(DROIDRUN_ROOT) not in sys.path:
    sys.path.insert(0, str(DROIDRUN_ROOT))


class _TestUIState:
    supported = {"element_index", "convert_point"}

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _install_droidrun_package_stubs():
    droidrun_pkg = types.ModuleType("droidrun")
    droidrun_pkg.__path__ = [str(DROIDRUN_ROOT)]
    tools_pkg = types.ModuleType("droidrun.tools")
    tools_pkg.__path__ = [str(DROIDRUN_ROOT / "tools")]
    ui_pkg = types.ModuleType("droidrun.tools.ui")
    ui_pkg.__path__ = [str(DROIDRUN_ROOT / "tools" / "ui")]
    driver_pkg = types.ModuleType("droidrun.tools.driver")
    driver_pkg.__path__ = [str(DROIDRUN_ROOT / "tools" / "driver")]

    base_module = types.ModuleType("droidrun.tools.driver.base")
    base_module.DeviceDisconnectedError = type("DeviceDisconnectedError", (Exception,), {})
    base_module.DeviceDriver = object

    state_module = types.ModuleType("droidrun.tools.ui.state")
    state_module.UIState = _TestUIState
    stealth_module = types.ModuleType("droidrun.tools.ui.stealth_state")
    stealth_module.StealthUIState = _TestUIState

    sys.modules.update(
        {
            "droidrun": droidrun_pkg,
            "droidrun.tools": tools_pkg,
            "droidrun.tools.ui": ui_pkg,
            "droidrun.tools.driver": driver_pkg,
            "droidrun.tools.driver.base": base_module,
            "droidrun.tools.ui.state": state_module,
            "droidrun.tools.ui.stealth_state": stealth_module,
            "mobile_crawler.domain.crawler_agent": droidrun_pkg,
            "mobile_crawler.domain.crawler_agent.tools": tools_pkg,
            "mobile_crawler.domain.crawler_agent.tools.ui": ui_pkg,
            "mobile_crawler.domain.crawler_agent.tools.driver": driver_pkg,
            "mobile_crawler.domain.crawler_agent.tools.driver.base": base_module,
            "mobile_crawler.domain.crawler_agent.tools.ui.state": state_module,
            "mobile_crawler.domain.crawler_agent.tools.ui.stealth_state": stealth_module,
        }
    )


def _load_module(module_name: str, relative_path: str):
    _install_droidrun_package_stubs()
    spec = importlib.util.spec_from_file_location(module_name, DROIDRUN_ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_provider_module():
    return _load_module(
        "droidrun.tools.ui.provider",
        "tools/ui/provider.py",
    )


def _load_actions_module():
    _install_droidrun_package_stubs()

    agent_pkg = types.ModuleType("droidrun.agent")
    agent_pkg.__path__ = [str(DROIDRUN_ROOT / "agent")]
    oneflows_pkg = types.ModuleType("droidrun.agent.oneflows")
    oneflows_pkg.__path__ = [str(DROIDRUN_ROOT / "agent" / "oneflows")]

    action_result_module = types.ModuleType("droidrun.agent.action_result")

    class _ActionResult:
        def __init__(self, success: bool, summary: str):
            self.success = success
            self.summary = summary

    action_result_module.ActionResult = _ActionResult

    app_starter_module = types.ModuleType("droidrun.agent.oneflows.app_starter_workflow")
    app_starter_module.AppStarter = Mock()

    sys.modules.update(
        {
            "droidrun.agent": agent_pkg,
            "droidrun.agent.oneflows": oneflows_pkg,
            "droidrun.agent.action_result": action_result_module,
            "droidrun.agent.oneflows.app_starter_workflow": app_starter_module,
            "mobile_crawler.domain.crawler_agent.agent": agent_pkg,
            "mobile_crawler.domain.crawler_agent.agent.oneflows": oneflows_pkg,
            "mobile_crawler.domain.crawler_agent.agent.action_result": action_result_module,
            "mobile_crawler.domain.crawler_agent.agent.oneflows.app_starter_workflow": app_starter_module,
        }
    )

    return _load_module(
        "droidrun.agent.utils.actions",
        "agent/utils/actions.py",
    )


@pytest.fixture
def android_state_provider():
    AndroidStateProvider = _load_provider_module().AndroidStateProvider

    driver = SimpleNamespace(
        _serial="test_device",
        screenshot=AsyncMock(return_value=b"png"),
        get_ui_tree=AsyncMock(
            return_value={
                "device_context": {"screen_bounds": {"width": 320, "height": 640}},
                "phone_state": {},
                "a11y_tree": [{"text": "ok"}],
            }
        ),
    )
    tree_filter = Mock()
    tree_filter.filter.return_value = [{"text": "ok"}]
    tree_formatter = Mock()
    tree_formatter.format.return_value = ("formatted", "", [], {})

    provider = AndroidStateProvider(
        driver=driver,
        tree_filter=tree_filter,
        tree_formatter=tree_formatter,
        ui_parser_mode="omniparser",
        target_package="com.example.app",
    )
    provider._get_omni_parser_elements = AsyncMock(return_value=[{"text": "ok"}])
    return provider, driver


@pytest.mark.asyncio
async def test_state_provider_relaunches_target_before_screenshot_and_omniparser(android_state_provider):
    provider, driver = android_state_provider
    mock_adb = Mock()
    mock_adb.get_current_package.side_effect = ["com.android.launcher", "com.example.app"]
    mock_adb.am_start_recovery.return_value = CrawlerActionResult(
        success=True,
        action_type="am_start_recovery",
        target="com.example.app",
    )

    with patch("mobile_crawler.domain.adb_action_executor.ADBActionExecutor", return_value=mock_adb):
        await provider.get_state()

    mock_adb.am_start_recovery.assert_called_once_with("com.example.app")
    driver.screenshot.assert_awaited_once()
    provider._get_omni_parser_elements.assert_awaited_once()


@pytest.mark.asyncio
async def test_state_provider_correct_package_proceeds_to_capture(android_state_provider):
    provider, driver = android_state_provider
    mock_adb = Mock()
    mock_adb.get_current_package.return_value = "com.example.app"

    with patch("mobile_crawler.domain.adb_action_executor.ADBActionExecutor", return_value=mock_adb):
        await provider.get_state()

    mock_adb.am_start_recovery.assert_not_called()
    driver.screenshot.assert_awaited_once()
    provider._get_omni_parser_elements.assert_awaited_once()


@pytest.mark.asyncio
async def test_state_provider_failed_recovery_raises_before_screenshot_or_omniparser(android_state_provider):
    provider, driver = android_state_provider
    mock_adb = Mock()
    mock_adb.get_current_package.return_value = "com.android.launcher"
    mock_adb.am_start_recovery.return_value = CrawlerActionResult(
        success=False,
        action_type="am_start_recovery",
        target="com.example.app",
        error_message="not found",
    )

    with patch("mobile_crawler.domain.adb_action_executor.ADBActionExecutor", return_value=mock_adb), \
         pytest.raises(RuntimeError, match="Unable to recover target app"):
        await provider.get_state()

    driver.screenshot.assert_not_awaited()
    provider._get_omni_parser_elements.assert_not_awaited()


@pytest.mark.asyncio
async def test_open_app_package_input_bypasses_app_starter():
    actions = _load_actions_module()

    ctx = SimpleNamespace(
        driver=SimpleNamespace(start_app=AsyncMock(return_value="App started: com.example.app")),
        app_opener_llm=Mock(),
        streaming=False,
    )

    with patch.object(actions, "AppStarter") as mock_app_starter:
        result = await actions.open_app("com.example.app", ctx=ctx)

    assert result.success is True
    ctx.driver.start_app.assert_awaited_once_with("com.example.app")
    mock_app_starter.assert_not_called()


@pytest.mark.asyncio
async def test_open_app_human_name_uses_app_starter():
    actions = _load_actions_module()

    workflow = Mock()
    workflow.run = AsyncMock(return_value="Opened Gmail")
    ctx = SimpleNamespace(
        driver=SimpleNamespace(start_app=AsyncMock()),
        app_opener_llm=Mock(),
        streaming=False,
    )

    with patch.object(actions, "AppStarter", return_value=workflow) as mock_app_starter:
        result = await actions.open_app("Gmail", ctx=ctx)

    assert result.success is True
    ctx.driver.start_app.assert_not_called()
    mock_app_starter.assert_called_once()
    workflow.run.assert_awaited_once_with(app_description="Gmail")
