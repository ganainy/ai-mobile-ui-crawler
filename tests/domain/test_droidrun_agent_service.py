"""Tests for DroidRunAgentService initialization, step tracking, and error handling.

All DroidRun imports are mocked to avoid importing real DroidRun code.
"""

import asyncio
import json
import logging
import os
import sys
import types
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock

import pytest

from mobile_crawler.domain.droidrun_agent_service import (
    DroidRunAgentService,
    DroidRunGoal,
    DroidRunResult,
    DroidRunLogHandler,
    CancelledErrorFilter,
)
from mobile_crawler.domain.models import AIAction, BoundingBox, ActionResult
from mobile_crawler.domain.step_phase import StepPhase


@pytest.fixture
def mock_config_manager():
    """Create a mock ConfigManager with default values."""
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        "ai_provider": "gemini",
        "ai_model": "gemini-1.5-flash",
        "droidrun_reasoning_mode": True,
        "droidrun_streaming": False,
        "droidrun_telemetry_enabled": False,
        "ui_parser_mode": "omniparser",
        "omniparser_backend": "replicate",
        "max_steps": 15,
        "max_crawl_steps": 15,
        "max_duration_seconds": 300,
        "max_crawl_duration_seconds": 600,
        "limit_type": "steps",
        "gemini_api_key": "fake_gemini_key",
        "replicate_api_key": "fake_replicate_key",
        "openai_api_key": None,
        "anthropic_api_key": None,
        "openrouter_api_key": None,
    }.get(key, default)
    config.user_config_store = Mock()
    config.user_config_store.get_secret_plaintext = Mock(side_effect=KeyError("not found"))
    return config


@pytest.fixture
def mock_ai_repo():
    """Create a mock AIInteractionRepository."""
    return Mock()


@pytest.fixture
def droidrun_service(mock_config_manager, mock_ai_repo):
    """Create a DroidRunAgentService with mocked dependencies."""
    return DroidRunAgentService(
        config_manager=mock_config_manager,
        ai_interaction_repository=mock_ai_repo,
        device_id="test_device_123",
    )


class TestDroidRunAgentServiceInitialization:
    """Tests for DroidRunAgentService initialization."""

    def test_init_with_config_manager(self, mock_config_manager):
        """Test initialization with ConfigManager."""
        service = DroidRunAgentService(
            config_manager=mock_config_manager,
            ai_interaction_repository=None,
            device_id="device1",
        )
        assert service.config_manager == mock_config_manager
        assert service.ai_interaction_repository is None
        assert service.device_id == "device1"
        assert service._droid_agent is None
        assert not service._is_initialized

    def test_init_with_ai_repository(self, mock_config_manager, mock_ai_repo):
        """Test initialization with AI interaction repository."""
        service = DroidRunAgentService(
            config_manager=mock_config_manager,
            ai_interaction_repository=mock_ai_repo,
            device_id="device1",
        )
        assert service.ai_interaction_repository == mock_ai_repo

    def test_init_default_state(self, mock_config_manager):
        """Test default state after initialization."""
        service = DroidRunAgentService(
            config_manager=mock_config_manager,
            ai_interaction_repository=None,
            device_id="device1",
        )
        assert service._current_run_id is None
        assert service._current_step_number == 0
        assert service._step_phase_machine is None
        assert service._step_phase_repository is None
        assert service._ui_wait_predicate is None
        assert service._action_verifier is None

    def test_max_step_reason_is_normal_completion(self):
        """DroidRun max-step reasons should not be treated as crawl errors."""
        assert DroidRunAgentService._is_max_step_completion_reason(
            "Reached max step count of 1 steps"
        )
        assert DroidRunAgentService._is_max_step_completion_reason(
            "Reached maximum steps"
        )
        assert not DroidRunAgentService._is_max_step_completion_reason(
            "Unable to locate target app"
        )


class TestDroidRunAgentServiceStepTracking:
    """Tests for step tracking functionality."""

    @patch('mobile_crawler.domain.droidrun_agent_service.StepPhaseStateMachine')
    @patch('mobile_crawler.domain.droidrun_agent_service.StepPhaseRepository')
    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    def test_begin_step_tracking_creates_state_machine(
        self, mock_db_class, mock_repo_class, mock_machine_class, droidrun_service
    ):
        """Test begin_step_tracking creates StepPhaseStateMachine."""
        mock_machine = Mock()
        mock_machine_class.return_value = mock_machine
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        emit_callback = Mock()
        droidrun_service.begin_step_tracking(run_id=42, emit_step_phase_event=emit_callback)

        assert droidrun_service._current_run_id == 42
        assert droidrun_service._current_step_number == 0
        assert droidrun_service._emit_step_phase_event == emit_callback
        mock_machine_class.assert_called_once()
        mock_machine.add_listener.assert_called_once()

    @patch('mobile_crawler.domain.droidrun_agent_service.StepPhaseStateMachine')
    @patch('mobile_crawler.domain.droidrun_agent_service.StepPhaseRepository')
    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    def test_begin_step_tracking_wires_repository(
        self, mock_db_class, mock_repo_class, mock_machine_class, droidrun_service
    ):
        """Test begin_step_tracking wires StepPhaseRepository."""
        mock_machine = Mock()
        mock_machine_class.return_value = mock_machine
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        droidrun_service.begin_step_tracking(run_id=42)

        mock_repo_class.assert_called_once()
        assert droidrun_service._step_phase_repository is not None

    def test_begin_step_tracking_without_callback(self, droidrun_service):
        """Test begin_step_tracking works without emit callback."""
        with patch('mobile_crawler.domain.droidrun_agent_service.StepPhaseStateMachine') as mock_machine_class, \
             patch('mobile_crawler.domain.droidrun_agent_service.StepPhaseRepository') as mock_repo_class, \
             patch('mobile_crawler.infrastructure.database.DatabaseManager'):
            mock_machine = Mock()
            mock_machine_class.return_value = mock_machine
            droidrun_service.begin_step_tracking(run_id=1)
            assert droidrun_service._emit_step_phase_event is None


class TestDroidRunAgentServicePhaseTransition:
    """Tests for phase transition handling."""

    def test_on_phase_transition_without_run_id(self, droidrun_service):
        """Test _on_phase_transition returns early without run_id."""
        droidrun_service._current_run_id = None
        droidrun_service._step_phase_repository = Mock()

        droidrun_service._on_phase_transition(StepPhase.CAPTURE, StepPhase.DECIDE)

        droidrun_service._step_phase_repository.record_transition.assert_not_called()

    def test_on_phase_transition_persists_transition(self, droidrun_service):
        """Test _on_phase_transition persists transition to repository."""
        droidrun_service._current_run_id = 42
        droidrun_service._current_step_number = 5

        mock_repo = Mock()
        droidrun_service._step_phase_repository = mock_repo

        mock_machine = Mock()
        mock_machine.get_phase_duration.return_value = 1.5
        droidrun_service._step_phase_machine = mock_machine

        droidrun_service._on_phase_transition(StepPhase.CAPTURE, StepPhase.DECIDE)

        mock_repo.record_transition.assert_called_once()
        mock_repo.update_step_current_phase.assert_called_once_with(42, 5, "decide")

    def test_on_phase_transition_emits_event(self, droidrun_service):
        """Test _on_phase_transition emits event via callback."""
        droidrun_service._current_run_id = 42
        droidrun_service._current_step_number = 5
        emit_callback = Mock()
        droidrun_service._emit_step_phase_event = emit_callback

        mock_repo = Mock()
        droidrun_service._step_phase_repository = mock_repo

        mock_machine = Mock()
        mock_machine.get_phase_duration.return_value = 2.0
        droidrun_service._step_phase_machine = mock_machine

        droidrun_service._on_phase_transition(StepPhase.CAPTURE, StepPhase.DECIDE)

        emit_callback.assert_called_once_with(
            "on_step_phase_transition",
            42, 5, "capture", "decide", 2000.0,
        )

    def test_on_phase_transition_without_emit_callback(self, droidrun_service):
        """Test _on_phase_transition works without emit callback."""
        droidrun_service._current_run_id = 42
        droidrun_service._current_step_number = 1
        droidrun_service._emit_step_phase_event = None

        mock_repo = Mock()
        droidrun_service._step_phase_repository = mock_repo

        mock_machine = Mock()
        mock_machine.get_phase_duration.return_value = None
        droidrun_service._step_phase_machine = mock_machine

        # Should not raise
        droidrun_service._on_phase_transition(StepPhase.CAPTURE, StepPhase.DECIDE)

        mock_repo.record_transition.assert_called_once()


class TestDroidRunAgentServiceWireObservers:
    """Tests for wiring observers to agent."""

    def test_wire_observers_without_agent(self, droidrun_service):
        """Test _wire_observers_to_agent returns early without agent."""
        droidrun_service._droid_agent = None
        # Should not raise
        droidrun_service._wire_observers_to_agent()
        assert droidrun_service._ui_wait_predicate is None

    def test_wire_observers_with_state_provider(self, droidrun_service, mock_config_manager):
        """Test _wire_observers_to_agent wires UIWaitPredicate and ActionVerifier."""
        mock_agent = Mock()
        mock_state_provider = Mock()
        mock_driver = Mock()
        mock_agent.state_provider = mock_state_provider
        mock_agent.driver = mock_driver
        droidrun_service._droid_agent = mock_agent
        droidrun_service._target_package = "com.example.app"

        with patch('mobile_crawler.domain.droidrun_agent_service.UIWaitPredicate') as mock_wait, \
             patch('mobile_crawler.domain.droidrun_agent_service.ActionVerifier') as mock_verifier, \
             patch('mobile_crawler.domain.droidrun_agent_service.DeviceContextCapture') as mock_ctx, \
             patch('mobile_crawler.domain.droidrun_agent_service.AppSwitchRecovery') as mock_recovery, \
             patch('mobile_crawler.domain.adb_action_executor.ADBActionExecutor'):
            droidrun_service._wire_observers_to_agent()
            mock_wait.assert_called_once()
            mock_verifier.assert_called_once()
            mock_ctx.assert_called_once()
            mock_recovery.assert_called_once()

    def test_wire_observers_without_driver(self, droidrun_service):
        """Test _wire_observers_to_agent without driver skips ActionVerifier."""
        mock_agent = Mock()
        mock_state_provider = Mock()
        mock_agent.state_provider = mock_state_provider
        mock_agent.driver = None
        droidrun_service._droid_agent = mock_agent
        droidrun_service._target_package = "com.example.app"

        with patch('mobile_crawler.domain.droidrun_agent_service.UIWaitPredicate') as mock_wait, \
             patch('mobile_crawler.domain.droidrun_agent_service.ActionVerifier') as mock_verifier, \
             patch('mobile_crawler.domain.droidrun_agent_service.DeviceContextCapture'), \
             patch('mobile_crawler.domain.droidrun_agent_service.AppSwitchRecovery'), \
             patch('mobile_crawler.domain.adb_action_executor.ADBActionExecutor'):
            droidrun_service._wire_observers_to_agent()
            mock_wait.assert_called_once()
            mock_verifier.assert_not_called()


class TestDroidRunAgentServiceHandleToolExecution:
    """Tests for _handle_tool_execution_event."""

    def test_handle_tool_execution_without_machine(self, droidrun_service):
        """Test _handle_tool_execution_event returns early without step phase machine."""
        droidrun_service._step_phase_machine = None

        event = Mock()
        event.tool_name = "tap"
        event.success = True

        # Should not raise - but it's async so we need to run it
        asyncio.run(droidrun_service._handle_tool_execution_event(event))

        # Step number should not increment
        assert droidrun_service._current_step_number == 0

    def test_handle_tool_execution_increments_step(self, droidrun_service):
        """Test _handle_tool_execution_event increments step number."""
        mock_machine = Mock()
        droidrun_service._step_phase_machine = mock_machine
        droidrun_service._context_capture = None
        droidrun_service._ui_dump_validator = None
        droidrun_service._action_verifier = None
        droidrun_service._ui_wait_predicate = None
        droidrun_service._current_step_number = 0

        event = Mock()
        event.tool_name = "tap"
        event.success = True

        asyncio.run(droidrun_service._handle_tool_execution_event(event))

        assert droidrun_service._current_step_number == 1

    def test_handle_tool_execution_normal_flow(self, droidrun_service):
        """Test _handle_tool_execution_event drives normal phase transitions."""
        mock_machine = Mock()
        droidrun_service._step_phase_machine = mock_machine
        droidrun_service._context_capture = None
        droidrun_service._ui_dump_validator = None
        droidrun_service._action_verifier = None
        droidrun_service._ui_wait_predicate = None
        droidrun_service._current_step_number = 0

        event = Mock()
        event.tool_name = "tap"
        event.success = True

        asyncio.run(droidrun_service._handle_tool_execution_event(event))

        # Normal flow: CAPTURE -> DECIDE -> EXECUTE -> RECORD -> CHECKPOINT -> CAPTURE
        calls = [call[0][0] for call in mock_machine.transition_to.call_args_list]
        assert StepPhase.DECIDE in calls
        assert StepPhase.EXECUTE in calls
        assert StepPhase.RECORD in calls
        assert StepPhase.CHECKPOINT in calls
        assert StepPhase.CAPTURE in calls

    def test_handle_tool_execution_with_skip_reason(self, droidrun_service):
        """Test _handle_tool_execution_event skips phases when skip reason set."""
        mock_machine = Mock()
        droidrun_service._step_phase_machine = mock_machine
        droidrun_service._context_capture = None

        # Mock UI dump validator to return invalid
        mock_validator = Mock()
        mock_validator.validate.return_value = Mock(is_valid=False, error="empty", element_count=0)
        droidrun_service._ui_dump_validator = mock_validator

        # Need to mock droid_agent state_provider to return a11y data
        mock_agent = Mock()
        mock_state_provider = Mock()
        mock_state = Mock()
        mock_state.get.return_value = [{"clickable": True}]
        mock_state_provider.get_state = AsyncMock(return_value=mock_state)
        mock_agent.state_provider = mock_state_provider
        droidrun_service._droid_agent = mock_agent

        droidrun_service._action_verifier = None
        droidrun_service._ui_wait_predicate = None
        droidrun_service._current_step_number = 0
        droidrun_service._current_run_id = 1
        droidrun_service._step_phase_repository = Mock()

        event = Mock()
        event.tool_name = "tap"
        event.success = True

        asyncio.run(droidrun_service._handle_tool_execution_event(event))

        # With skip: should still have transitions
        calls = [call[0][0] for call in mock_machine.transition_to.call_args_list]
        assert StepPhase.CHECKPOINT in calls
        assert StepPhase.CAPTURE in calls


class TestDroidRunAgentServiceErrorHandling:
    """Tests for error handling."""

    def test_is_app_crash_error_detects_crash(self, droidrun_service):
        """Test _is_app_crash_error detects crash indicators."""
        assert droidrun_service._is_app_crash_error("No active window found")
        assert droidrun_service._is_app_crash_error("root filtered out")
        assert droidrun_service._is_app_crash_error("Accessibility node info error")
        assert not droidrun_service._is_app_crash_error("Normal timeout")

    def test_create_exploration_goal(self, droidrun_service):
        """Test _create_exploration_goal creates correct goal."""
        goal = droidrun_service._create_exploration_goal("com.example.app", 10)
        assert goal.app_package == "com.example.app"
        assert goal.max_steps == 10
        assert "com.example.app" in goal.description
        assert "continuous exploration" in goal.description.lower()

    def test_create_exploration_goal_with_objective(self, droidrun_service):
        """Test _create_exploration_goal includes exploration objective."""
        goal = droidrun_service._create_exploration_goal(
            "com.example.app", 10, "test login flow"
        )
        assert "test login flow" in goal.description

    def test_log_agent_interaction_without_repo(self, droidrun_service):
        """Test _log_agent_interaction returns early without repository."""
        droidrun_service.ai_interaction_repository = None
        goal = DroidRunGoal(description="test", max_steps=5)
        # Should not raise
        droidrun_service._log_agent_interaction(1, goal, None, None)

    def test_log_agent_interaction_with_repo(self, droidrun_service, mock_ai_repo):
        """Test _log_agent_interaction creates interaction record."""
        goal = DroidRunGoal(description="test goal", max_steps=5)
        result = {"success": True, "steps_completed": 3}
        droidrun_service._log_agent_interaction(1, goal, result, None)

        mock_ai_repo.create_ai_interaction.assert_called_once()
        call_args = mock_ai_repo.create_ai_interaction.call_args[0][0]
        assert call_args.run_id == 1
        assert call_args.success is True


class TestDroidRunAgentServiceConfig:
    """Tests for DroidRun configuration."""

    @patch.dict(os.environ, {}, clear=False)
    def test_get_droidrun_config(self, droidrun_service, mock_config_manager):
        """Test _get_droidrun_config produces valid config dict."""
        config = droidrun_service._get_droidrun_config(max_steps=20)

        assert config["agent"]["max_steps"] == 20
        assert config["device"]["platform"] == "android"
        assert config["device"]["serial"] == "test_device_123"
        assert config["device"]["auto_setup"] is False
        assert "llm_profiles" in config
        assert "manager" in config["llm_profiles"]
        assert config["llm_profiles"]["manager"]["kwargs"]["max_tokens"] == 2048
        assert config["llm_profiles"]["executor"]["kwargs"]["max_tokens"] == 512
        assert config["llm_profiles"]["fast_agent"]["kwargs"]["max_tokens"] == 1024

    @patch.dict(os.environ, {}, clear=False)
    def test_get_droidrun_config_gemini_provider(self, droidrun_service, mock_config_manager):
        """Test _get_droidrun_config maps gemini provider correctly."""
        config = droidrun_service._get_droidrun_config()
        assert config["llm_profiles"]["manager"]["provider"] == "GoogleGenAI"

    @patch.dict(os.environ, {}, clear=False)
    def test_get_droidrun_config_openrouter_provider(self, droidrun_service, mock_config_manager):
        """Test _get_droidrun_config maps openrouter provider correctly."""
        settings = {
            "ai_provider": "openrouter",
            "ai_model": "qwen/qwen3.6-plus",
            "openrouter_api_key": "sk-or-test-key",
            "droidrun_reasoning_mode": True,
            "droidrun_streaming": False,
            "droidrun_telemetry_enabled": False,
            "ui_parser_mode": "omniparser",
            "omniparser_backend": "replicate",
            "replicate_api_key": "fake_replicate_key",
        }
        mock_config_manager.get.side_effect = lambda key, default=None: settings.get(key, default)

        config = droidrun_service._get_droidrun_config()

        for profile in config["llm_profiles"].values():
            assert profile["provider"] == "OpenRouter"
            assert profile["model"] == "qwen/qwen3.6-plus"
            assert profile["kwargs"]["api_key"] == "sk-or-test-key"
        assert os.environ["OPENROUTER_API_KEY"] == "sk-or-test-key"

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-env-key"}, clear=False)
    def test_get_droidrun_config_openrouter_uses_env_api_key(self, droidrun_service, mock_config_manager):
        """Test OpenRouter API key can come from OPENROUTER_API_KEY."""
        settings = {
            "ai_provider": "openrouter",
            "ai_model": "qwen/qwen3.6-plus",
            "openrouter_api_key": None,
            "droidrun_reasoning_mode": True,
            "droidrun_streaming": False,
            "droidrun_telemetry_enabled": False,
            "ui_parser_mode": "omniparser",
            "omniparser_backend": "replicate",
            "replicate_api_key": "fake_replicate_key",
        }
        mock_config_manager.get.side_effect = lambda key, default=None: settings.get(key, default)

        config = droidrun_service._get_droidrun_config()

        for profile in config["llm_profiles"].values():
            assert profile["kwargs"]["api_key"] == "sk-or-env-key"

    @patch.dict(os.environ, {}, clear=False)
    def test_get_droidrun_config_unknown_provider_raises(self, droidrun_service, mock_config_manager):
        """Test unknown providers do not silently fall back to Gemini."""
        settings = {
            "ai_provider": "unknown",
            "ai_model": "some-model",
        }
        mock_config_manager.get.side_effect = lambda key, default=None: settings.get(key, default)

        with pytest.raises(ValueError, match="Unsupported AI provider: unknown"):
            droidrun_service._get_droidrun_config()

    @patch.dict(os.environ, {}, clear=False)
    def test_get_droidrun_config_telemetry(self, droidrun_service, mock_config_manager):
        """Test _get_droidrun_config includes telemetry settings."""
        config = droidrun_service._get_droidrun_config()
        assert "telemetry" in config
        assert config["telemetry"]["enabled"] is False


class TestDroidRunAgentServiceTargetPreflight:
    """Tests for launching/verifying the target app before DroidRun starts."""

    @pytest.mark.asyncio
    async def test_execute_preflight_already_in_target_does_not_launch(self, droidrun_service):
        mock_adb = Mock()
        mock_adb.get_current_package.return_value = "com.example.app"

        with patch("mobile_crawler.domain.adb_action_executor.ADBActionExecutor", return_value=mock_adb), \
             patch.object(droidrun_service, "_initialize_agent", new=AsyncMock()), \
             patch.object(droidrun_service, "_log_agent_interaction"), \
             patch.dict(sys.modules, self._fake_droidrun_modules(success=True)):
            droidrun_service._droidrun_config = Mock()
            result = await droidrun_service.execute_exploration_task(
                run_id=1,
                app_package="com.example.app",
                max_steps=3,
            )

        assert result.success is True
        mock_adb.am_start_recovery.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_preflight_launches_and_verifies_before_droidrun(self, droidrun_service):
        mock_adb = Mock()
        mock_adb.get_current_package.side_effect = ["com.android.launcher", "com.example.app"]
        mock_adb.am_start_recovery.return_value = ActionResult(
            success=True,
            action_type="am_start_recovery",
            target="com.example.app",
        )

        with patch("mobile_crawler.domain.adb_action_executor.ADBActionExecutor", return_value=mock_adb), \
             patch.object(droidrun_service, "_initialize_agent", new=AsyncMock()), \
             patch.object(droidrun_service, "_log_agent_interaction"), \
             patch.dict(sys.modules, self._fake_droidrun_modules(success=True)):
            droidrun_service._droidrun_config = Mock()
            result = await droidrun_service.execute_exploration_task(
                run_id=1,
                app_package="com.example.app",
                max_steps=3,
            )

        assert result.success is True
        mock_adb.am_start_recovery.assert_called_once_with("com.example.app")

    @pytest.mark.asyncio
    async def test_execute_preflight_failure_returns_without_creating_droid_agent(self, droidrun_service):
        mock_adb = Mock()
        mock_adb.get_current_package.return_value = "com.android.launcher"
        mock_adb.am_start_recovery.return_value = ActionResult(
            success=False,
            action_type="am_start_recovery",
            target="com.example.app",
            error_message="not found",
        )

        fake_modules = self._fake_droidrun_modules(success=True)
        fake_agent = fake_modules["droidrun.agent.droid.droid_agent"].DroidAgent

        with patch("mobile_crawler.domain.adb_action_executor.ADBActionExecutor", return_value=mock_adb), \
             patch.object(droidrun_service, "_initialize_agent", new=AsyncMock()), \
             patch.object(droidrun_service, "_log_agent_interaction"), \
             patch.dict(sys.modules, fake_modules):
            result = await droidrun_service.execute_exploration_task(
                run_id=1,
                app_package="com.example.app",
                max_steps=3,
            )

        assert result.success is False
        assert "Unable to open target app" in result.error_message
        fake_agent.assert_not_called()

    @staticmethod
    def _fake_droidrun_modules(success: bool):
        async def _run_result():
            return types.SimpleNamespace(success=success, steps=1, reason="")

        agent_instance = Mock()
        agent_instance.run.side_effect = _run_result
        agent_instance.shared_state = types.SimpleNamespace(
            action_history=[],
            action_outcomes=[],
        )

        droid_agent_module = types.ModuleType("droidrun.agent.droid.droid_agent")
        droid_agent_module.DroidAgent = Mock(return_value=agent_instance)

        return {
            "droidrun": types.ModuleType("droidrun"),
            "droidrun.agent": types.ModuleType("droidrun.agent"),
            "droidrun.agent.droid": types.ModuleType("droidrun.agent.droid"),
            "droidrun.agent.droid.droid_agent": droid_agent_module,
        }


class TestDroidRunAgentServiceLogging:
    """Tests for run logging configuration."""

    def test_configure_run_logging(self, droidrun_service, tmp_path):
        """Test configure_run_logging attaches handler."""
        log_dir = str(tmp_path)
        emit_debug = Mock()
        droid_logger = logging.getLogger("droidrun")
        original_propagate = droid_logger.propagate

        try:
            with patch('mobile_crawler.domain.droidrun_agent_service.DroidRunLogHandler') as mock_handler_class:
                mock_handler = Mock()
                mock_handler_class.return_value = mock_handler
                droidrun_service.configure_run_logging(1, log_dir, emit_debug, True)
                assert droidrun_service._log_handler is not None
                assert droid_logger.propagate is False
                mock_handler_class.assert_called_once()
        finally:
            droid_logger.propagate = original_propagate

    def test_clear_run_logging(self, droidrun_service, tmp_path):
        """Test clear_run_logging removes handler."""
        log_dir = str(tmp_path)
        emit_debug = Mock()
        droid_logger = logging.getLogger("droidrun")
        original_propagate = droid_logger.propagate

        try:
            with patch('mobile_crawler.domain.droidrun_agent_service.DroidRunLogHandler') as mock_handler_class:
                mock_handler = Mock()
                mock_handler_class.return_value = mock_handler
                droidrun_service.configure_run_logging(1, log_dir, emit_debug, True)
                droidrun_service.clear_run_logging()
                assert droidrun_service._log_handler is None
                assert droid_logger.propagate is True
        finally:
            droid_logger.propagate = original_propagate


class TestDroidRunAgentServiceActionConversion:
    """Tests for action conversion."""

    def test_convert_droidrun_actions(self, droidrun_service):
        """Test convert_droidrun_actions_to_crawler_format maps actions correctly."""
        droidrun_actions = [
            {"action": "click", "description": "Click button", "coordinates": [100, 200]},
            {"action": "type", "description": "Enter text", "text": "hello"},
            {"action": "back", "description": "Go back"},
        ]
        actions = droidrun_service.convert_droidrun_actions_to_crawler_format(droidrun_actions)

        assert len(actions) == 3
        assert actions[0].action == "click"
        assert actions[1].action == "input"
        assert actions[2].action == "back"
        assert actions[1].input_text == "hello"

    def test_convert_droidrun_actions_with_bounding_box(self, droidrun_service):
        """Test action conversion creates bounding box from coordinates."""
        droidrun_actions = [
            {"action": "click", "description": "Click", "coordinates": [100, 200]},
        ]
        actions = droidrun_service.convert_droidrun_actions_to_crawler_format(droidrun_actions)

        assert actions[0].target_bounding_box is not None
        assert isinstance(actions[0].target_bounding_box, BoundingBox)

    def test_convert_droidrun_actions_unknown_action(self, droidrun_service):
        """Test unknown actions default to click."""
        droidrun_actions = [
            {"action": "unknown_action", "description": "Unknown"},
        ]
        actions = droidrun_service.convert_droidrun_actions_to_crawler_format(droidrun_actions)
        assert actions[0].action == "click"


class TestDroidRunLogHandler:
    """Tests for DroidRunLogHandler."""

    def test_handler_initialization(self, tmp_path):
        """Test DroidRunLogHandler initialization."""
        log_path = str(tmp_path / "test.jsonl")
        emit_debug = Mock()
        handler = DroidRunLogHandler(1, log_path, emit_debug, True)
        assert handler.run_id == 1
        assert handler.log_path == log_path
        assert handler.enable_ui is True

    def test_handler_emits_to_file(self, tmp_path):
        """Test DroidRunLogHandler writes JSONL to file."""
        log_path = str(tmp_path / "test.jsonl")
        emit_debug = Mock()
        handler = DroidRunLogHandler(1, log_path, emit_debug, True)

        record = Mock()
        record.getMessage.return_value = "test log message"
        record.levelname = "INFO"

        handler.emit(record)

        with open(log_path, "r") as f:
            line = f.readline()
            event = json.loads(line)
            assert event["message"] == "test log message"
            assert event["level"] == "INFO"
            assert event["run_id"] == 1

    def test_handler_ui_disabled(self, tmp_path):
        """Test DroidRunLogHandler does not emit to UI when disabled."""
        log_path = str(tmp_path / "test.jsonl")
        emit_debug = Mock()
        handler = DroidRunLogHandler(1, log_path, emit_debug, False)

        record = Mock()
        record.getMessage.return_value = "test"
        record.levelname = "DEBUG"

        handler.emit(record)
        emit_debug.assert_not_called()


class TestCancelledErrorFilter:
    """Tests for CancelledErrorFilter."""

    def test_filter_allows_normal_errors(self):
        """Test filter allows normal ERROR records."""
        f = CancelledErrorFilter()
        record = Mock()
        record.levelno = logging.ERROR
        record.getMessage.return_value = "normal error"
        record.exc_info = None
        assert f.filter(record) is True

    def test_filter_suppresses_cancelled_error(self):
        """Test filter suppresses CancelledError records."""
        f = CancelledErrorFilter()
        record = Mock()
        record.levelno = logging.ERROR
        record.getMessage.return_value = "task cancelled"
        record.exc_info = (asyncio.CancelledError, asyncio.CancelledError(), None)
        assert f.filter(record) is False

    def test_filter_suppresses_cancelled_in_message(self):
        """Test filter suppresses records with CancelledError in message."""
        f = CancelledErrorFilter()
        record = Mock()
        record.levelno = logging.ERROR
        record.getMessage.return_value = "CancelledError in task"
        record.exc_info = None
        assert f.filter(record) is False
