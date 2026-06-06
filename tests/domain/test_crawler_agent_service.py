"""Tests for CrawlerAgentService initialization, step tracking, and error handling.

All CrawlerAgent imports are mocked to avoid importing real agent code.
"""

import asyncio
import json
import logging
import os
import sys
import types
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mobile_crawler.domain.adb_action_executor import DeviceReadinessResult
from mobile_crawler.domain.crawler_agent_service import (
    CancelledErrorFilter,
    CrawlerAgentService,
    CrawlerGoal,
    CrawlerLogHandler,
)
from mobile_crawler.domain.models import ActionResult, BoundingBox
from mobile_crawler.domain.step_phase import StepPhase


@pytest.fixture
def mock_config_manager():
    """Create a mock ConfigManager with default values."""
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        "ai_provider": "gemini",
        "ai_model": "gemini-1.5-flash",
        "crawler_reasoning_mode": True,
        "crawler_streaming": False,
        "crawler_telemetry_enabled": False,
        "ui_parser_mode": "omniparser",
        "omniparser_backend": "replicate",
        "omniparser_local_url": "http://localhost:8000",
        "omniparser_local_parse_timeout_seconds": 120,
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
def crawler_agent_service(mock_config_manager, mock_ai_repo):
    """Create a CrawlerAgentService with mocked dependencies."""
    return CrawlerAgentService(
        config_manager=mock_config_manager,
        ai_interaction_repository=mock_ai_repo,
        device_id="test_device_123",
    )


class TestCrawlerAgentServiceInitialization:
    """Tests for CrawlerAgentService initialization."""

    def test_init_with_config_manager(self, mock_config_manager):
        """Test initialization with ConfigManager."""
        service = CrawlerAgentService(
            config_manager=mock_config_manager,
            ai_interaction_repository=None,
            device_id="device1",
        )
        assert service.config_manager == mock_config_manager
        assert service.ai_interaction_repository is None
        assert service.device_id == "device1"
        assert service._crawler_agent is None
        assert not service._is_initialized

    def test_init_with_ai_repository(self, mock_config_manager, mock_ai_repo):
        """Test initialization with AI interaction repository."""
        service = CrawlerAgentService(
            config_manager=mock_config_manager,
            ai_interaction_repository=mock_ai_repo,
            device_id="device1",
        )
        assert service.ai_interaction_repository == mock_ai_repo

    def test_init_default_state(self, mock_config_manager):
        """Test default state after initialization."""
        service = CrawlerAgentService(
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
        """CrawlerAgent max-step reasons should not be treated as crawl errors."""
        assert CrawlerAgentService._is_max_step_completion_reason(
            "Reached max step count of 1 steps"
        )
        assert CrawlerAgentService._is_max_step_completion_reason(
            "Reached maximum steps"
        )
        assert not CrawlerAgentService._is_max_step_completion_reason(
            "Unable to locate target app"
        )


class TestCrawlerAgentServiceStepTracking:
    """Tests for step tracking functionality."""

    @patch('mobile_crawler.domain.crawler_agent_service.StepPhaseStateMachine')
    @patch('mobile_crawler.domain.crawler_agent_service.StepPhaseRepository')
    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    def test_begin_step_tracking_creates_state_machine(
        self, mock_db_class, mock_repo_class, mock_machine_class, crawler_agent_service
    ):
        """Test begin_step_tracking creates StepPhaseStateMachine."""
        mock_machine = Mock()
        mock_machine_class.return_value = mock_machine
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        emit_callback = Mock()
        crawler_agent_service.begin_step_tracking(run_id=42, emit_step_phase_event=emit_callback)

        assert crawler_agent_service._current_run_id == 42
        assert crawler_agent_service._current_step_number == 0
        assert crawler_agent_service._emit_step_phase_event == emit_callback
        mock_machine_class.assert_called_once()
        mock_machine.add_listener.assert_called_once()

    @patch('mobile_crawler.domain.crawler_agent_service.StepPhaseStateMachine')
    @patch('mobile_crawler.domain.crawler_agent_service.StepPhaseRepository')
    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    def test_begin_step_tracking_wires_repository(
        self, mock_db_class, mock_repo_class, mock_machine_class, crawler_agent_service
    ):
        """Test begin_step_tracking wires StepPhaseRepository."""
        mock_machine = Mock()
        mock_machine_class.return_value = mock_machine
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        crawler_agent_service.begin_step_tracking(run_id=42)

        mock_repo_class.assert_called_once()
        assert crawler_agent_service._step_phase_repository is not None

    def test_begin_step_tracking_without_callback(self, crawler_agent_service):
        """Test begin_step_tracking works without emit callback."""
        with patch('mobile_crawler.domain.crawler_agent_service.StepPhaseStateMachine') as mock_machine_class, \
             patch('mobile_crawler.domain.crawler_agent_service.StepPhaseRepository'), \
             patch('mobile_crawler.infrastructure.database.DatabaseManager'):
            mock_machine = Mock()
            mock_machine_class.return_value = mock_machine
            crawler_agent_service.begin_step_tracking(run_id=1)
            assert crawler_agent_service._emit_step_phase_event is None


class TestCrawlerAgentServicePhaseTransition:
    """Tests for phase transition handling."""

    def test_on_phase_transition_without_run_id(self, crawler_agent_service):
        """Test _on_phase_transition returns early without run_id."""
        crawler_agent_service._current_run_id = None
        crawler_agent_service._step_phase_repository = Mock()

        crawler_agent_service._on_phase_transition(StepPhase.CAPTURE, StepPhase.DECIDE)

        crawler_agent_service._step_phase_repository.record_transition.assert_not_called()

    def test_on_phase_transition_persists_transition(self, crawler_agent_service):
        """Test _on_phase_transition persists transition to repository."""
        crawler_agent_service._current_run_id = 42
        crawler_agent_service._current_step_number = 5

        mock_repo = Mock()
        crawler_agent_service._step_phase_repository = mock_repo

        mock_machine = Mock()
        mock_machine.get_phase_duration.return_value = 1.5
        crawler_agent_service._step_phase_machine = mock_machine

        crawler_agent_service._on_phase_transition(StepPhase.CAPTURE, StepPhase.DECIDE)

        mock_repo.record_transition.assert_called_once()
        mock_repo.update_step_current_phase.assert_called_once_with(42, 5, "decide")

    def test_on_phase_transition_emits_event(self, crawler_agent_service):
        """Test _on_phase_transition emits event via callback."""
        crawler_agent_service._current_run_id = 42
        crawler_agent_service._current_step_number = 5
        emit_callback = Mock()
        crawler_agent_service._emit_step_phase_event = emit_callback

        mock_repo = Mock()
        crawler_agent_service._step_phase_repository = mock_repo

        mock_machine = Mock()
        mock_machine.get_phase_duration.return_value = 2.0
        crawler_agent_service._step_phase_machine = mock_machine

        crawler_agent_service._on_phase_transition(StepPhase.CAPTURE, StepPhase.DECIDE)

        emit_callback.assert_called_once_with(
            "on_step_phase_transition",
            42, 5, "capture", "decide", 2000.0,
        )

    def test_on_phase_transition_without_emit_callback(self, crawler_agent_service):
        """Test _on_phase_transition works without emit callback."""
        crawler_agent_service._current_run_id = 42
        crawler_agent_service._current_step_number = 1
        crawler_agent_service._emit_step_phase_event = None

        mock_repo = Mock()
        crawler_agent_service._step_phase_repository = mock_repo

        mock_machine = Mock()
        mock_machine.get_phase_duration.return_value = None
        crawler_agent_service._step_phase_machine = mock_machine

        # Should not raise
        crawler_agent_service._on_phase_transition(StepPhase.CAPTURE, StepPhase.DECIDE)

        mock_repo.record_transition.assert_called_once()

    def test_sub_phase_timing_metadata_persisted(self, crawler_agent_service):
        """Test sub-phase timings are written to transition metadata."""
        crawler_agent_service._current_run_id = 42
        crawler_agent_service._current_step_number = 1
        crawler_agent_service._emit_step_phase_event = None

        mock_repo = Mock()
        crawler_agent_service._step_phase_repository = mock_repo

        mock_machine = Mock()
        mock_machine.get_phase_duration.return_value = 0.25
        crawler_agent_service._step_phase_machine = mock_machine

        crawler_agent_service._add_sub_phase_timing(
            "manager_llm_ms", 1234.5678, parent_phase=StepPhase.DECIDE
        )
        crawler_agent_service._add_validation_retry(
            "Missing plan tag", parent_phase=StepPhase.DECIDE, attempt=1
        )

        crawler_agent_service._on_phase_transition(StepPhase.DECIDE, StepPhase.EXECUTE)

        transition = mock_repo.record_transition.call_args.args[0]
        metadata = json.loads(transition.metadata_json)
        assert metadata["sub_phases"]["manager_llm_ms"] == 1234.568
        assert metadata["validation_retries"][0]["reason"] == "Missing plan tag"
        assert metadata["validation_retries"][0]["attempt"] == 1

    def test_pending_workflow_timing_applies_to_decide_phase(self, crawler_agent_service):
        """Test buffered Manager/Executor timings attach to DECIDE metadata."""
        crawler_agent_service._pending_step_timing = {
            "app_card_load_ms": 10.0,
            "manager_llm_ms": 20.0,
            "executor_llm_ms": 30.0,
            "validation_retries": [
                {"reason": "Missing plan tag", "timestamp": "2026-06-06T00:00:00", "attempt": 1}
            ],
        }

        crawler_agent_service._apply_pending_step_timing()

        metadata = crawler_agent_service._phase_metadata[StepPhase.DECIDE.value]
        assert metadata["sub_phases"] == {
            "app_card_load_ms": 10.0,
            "manager_llm_ms": 20.0,
            "executor_llm_ms": 30.0,
        }
        assert metadata["validation_retries"][0]["reason"] == "Missing plan tag"
        assert crawler_agent_service._pending_step_timing == {}


class TestCrawlerAgentServiceWireObservers:
    """Tests for wiring observers to agent."""

    def test_wire_observers_without_agent(self, crawler_agent_service):
        """Test _wire_observers_to_agent returns early without agent."""
        crawler_agent_service._crawler_agent = None
        # Should not raise
        crawler_agent_service._wire_observers_to_agent()
        assert crawler_agent_service._ui_wait_predicate is None

    def test_wire_observers_with_state_provider(self, crawler_agent_service, mock_config_manager):
        """Test _wire_observers_to_agent wires UIWaitPredicate and ActionVerifier."""
        mock_agent = Mock()
        mock_state_provider = Mock()
        mock_driver = Mock()
        mock_agent.state_provider = mock_state_provider
        mock_agent.driver = mock_driver
        crawler_agent_service._crawler_agent = mock_agent
        crawler_agent_service._target_package = "com.example.app"

        with patch('mobile_crawler.domain.crawler_agent_service.UIWaitPredicate') as mock_wait, \
             patch('mobile_crawler.domain.crawler_agent_service.ActionVerifier') as mock_verifier, \
             patch('mobile_crawler.domain.crawler_agent_service.DeviceContextCapture') as mock_ctx, \
             patch('mobile_crawler.domain.crawler_agent_service.AppSwitchRecovery') as mock_recovery, \
             patch('mobile_crawler.domain.adb_action_executor.ADBActionExecutor'):
            crawler_agent_service._wire_observers_to_agent()
            mock_wait.assert_called_once()
            mock_verifier.assert_called_once()
            mock_ctx.assert_called_once()
            mock_recovery.assert_called_once()

    def test_wire_observers_without_driver(self, crawler_agent_service):
        """Test _wire_observers_to_agent without driver skips ActionVerifier."""
        mock_agent = Mock()
        mock_state_provider = Mock()
        mock_agent.state_provider = mock_state_provider
        mock_agent.driver = None
        crawler_agent_service._crawler_agent = mock_agent
        crawler_agent_service._target_package = "com.example.app"

        with patch('mobile_crawler.domain.crawler_agent_service.UIWaitPredicate') as mock_wait, \
             patch('mobile_crawler.domain.crawler_agent_service.ActionVerifier') as mock_verifier, \
             patch('mobile_crawler.domain.crawler_agent_service.DeviceContextCapture'), \
             patch('mobile_crawler.domain.crawler_agent_service.AppSwitchRecovery'), \
             patch('mobile_crawler.domain.adb_action_executor.ADBActionExecutor'):
            crawler_agent_service._wire_observers_to_agent()
            mock_wait.assert_called_once()
            mock_verifier.assert_not_called()


class TestCrawlerAgentServiceHandleToolExecution:
    """Tests for _handle_tool_execution_event."""

    def test_handle_tool_execution_without_machine(self, crawler_agent_service):
        """Test _handle_tool_execution_event returns early without step phase machine."""
        crawler_agent_service._step_phase_machine = None

        event = Mock()
        event.tool_name = "tap"
        event.success = True

        # Should not raise - but it's async so we need to run it
        asyncio.run(crawler_agent_service._handle_tool_execution_event(event))

        # Step number should not increment
        assert crawler_agent_service._current_step_number == 0

    def test_handle_tool_execution_increments_step(self, crawler_agent_service):
        """Test _handle_tool_execution_event increments step number."""
        mock_machine = Mock()
        crawler_agent_service._step_phase_machine = mock_machine
        crawler_agent_service._context_capture = None
        crawler_agent_service._ui_dump_validator = None
        crawler_agent_service._action_verifier = None
        crawler_agent_service._ui_wait_predicate = None
        crawler_agent_service._current_step_number = 0

        event = Mock()
        event.tool_name = "tap"
        event.success = True

        asyncio.run(crawler_agent_service._handle_tool_execution_event(event))

        assert crawler_agent_service._current_step_number == 1

    def test_handle_tool_execution_normal_flow(self, crawler_agent_service):
        """Test _handle_tool_execution_event drives normal phase transitions."""
        mock_machine = Mock()
        crawler_agent_service._step_phase_machine = mock_machine
        crawler_agent_service._context_capture = None
        crawler_agent_service._ui_dump_validator = None
        crawler_agent_service._action_verifier = None
        crawler_agent_service._ui_wait_predicate = None
        crawler_agent_service._current_step_number = 0

        event = Mock()
        event.tool_name = "tap"
        event.success = True

        asyncio.run(crawler_agent_service._handle_tool_execution_event(event))

        # Normal flow: CAPTURE -> DECIDE -> EXECUTE -> RECORD -> CHECKPOINT -> CAPTURE
        calls = [call[0][0] for call in mock_machine.transition_to.call_args_list]
        assert StepPhase.DECIDE in calls
        assert StepPhase.EXECUTE in calls
        assert StepPhase.RECORD in calls
        assert StepPhase.CHECKPOINT in calls
        assert StepPhase.CAPTURE in calls

    def test_handle_tool_execution_with_skip_reason(self, crawler_agent_service):
        """Test _handle_tool_execution_event skips phases when skip reason set."""
        mock_machine = Mock()
        crawler_agent_service._step_phase_machine = mock_machine
        crawler_agent_service._context_capture = None

        # Mock UI dump validator to return invalid
        mock_validator = Mock()
        mock_validator.validate.return_value = Mock(is_valid=False, error="empty", element_count=0)
        crawler_agent_service._ui_dump_validator = mock_validator

        # Need to mock crawler_agent state_provider to return a11y data
        mock_agent = Mock()
        mock_state_provider = Mock()
        mock_state = Mock()
        mock_state.get.return_value = [{"clickable": True}]
        mock_state_provider.get_state = AsyncMock(return_value=mock_state)
        mock_agent.state_provider = mock_state_provider
        crawler_agent_service._crawler_agent = mock_agent

        crawler_agent_service._action_verifier = None
        crawler_agent_service._ui_wait_predicate = None
        crawler_agent_service._current_step_number = 0
        crawler_agent_service._current_run_id = 1
        crawler_agent_service._step_phase_repository = Mock()

        event = Mock()
        event.tool_name = "tap"
        event.success = True

        asyncio.run(crawler_agent_service._handle_tool_execution_event(event))

        # With skip: should still have transitions
        calls = [call[0][0] for call in mock_machine.transition_to.call_args_list]
        assert StepPhase.CHECKPOINT in calls
        assert StepPhase.CAPTURE in calls


class TestCrawlerAgentServiceErrorHandling:
    """Tests for error handling."""

    def test_is_app_crash_error_detects_crash(self, crawler_agent_service):
        """Test _is_app_crash_error detects crash indicators."""
        assert crawler_agent_service._is_app_crash_error("No active window found")
        assert crawler_agent_service._is_app_crash_error("root filtered out")
        assert crawler_agent_service._is_app_crash_error("Accessibility node info error")
        assert not crawler_agent_service._is_app_crash_error("Normal timeout")

    def test_create_exploration_goal(self, crawler_agent_service):
        """Test _create_exploration_goal creates correct goal."""
        goal = crawler_agent_service._create_exploration_goal("com.example.app", 10)
        assert goal.app_package == "com.example.app"
        assert goal.max_steps == 10
        assert "com.example.app" in goal.description
        assert "continuous exploration" in goal.description.lower()

    def test_create_exploration_goal_with_objective(self, crawler_agent_service):
        """Test _create_exploration_goal includes exploration objective."""
        goal = crawler_agent_service._create_exploration_goal(
            "com.example.app", 10, "test login flow"
        )
        assert "test login flow" in goal.description

    def test_log_agent_interaction_without_repo(self, crawler_agent_service):
        """Test _log_agent_interaction returns early without repository."""
        crawler_agent_service.ai_interaction_repository = None
        goal = CrawlerGoal(description="test", max_steps=5)
        # Should not raise
        crawler_agent_service._log_agent_interaction(1, goal, None, None)

    def test_log_agent_interaction_with_repo(self, crawler_agent_service, mock_ai_repo):
        """Test _log_agent_interaction creates interaction record."""
        goal = CrawlerGoal(description="test goal", max_steps=5)
        result = {"success": True, "steps_completed": 3}
        crawler_agent_service._log_agent_interaction(1, goal, result, None)

        mock_ai_repo.create_ai_interaction.assert_called_once()
        call_args = mock_ai_repo.create_ai_interaction.call_args[0][0]
        assert call_args.run_id == 1
        assert call_args.success is True

    def test_log_agent_interaction_accepts_list_result(self, crawler_agent_service, mock_ai_repo):
        """Test _log_agent_interaction handles workflow results that are lists."""
        goal = CrawlerGoal(description="test goal", max_steps=5)
        result = [{"action": "tap"}, {"action": "back"}]

        crawler_agent_service._log_agent_interaction(1, goal, result, None)

        mock_ai_repo.create_ai_interaction.assert_called_once()
        call_args = mock_ai_repo.create_ai_interaction.call_args[0][0]
        response_data = json.loads(call_args.response_raw)
        assert response_data["success"] is True
        assert response_data["steps_completed"] == 2
        assert response_data["actions_taken"] == result


class TestCrawlerAgentServiceConfig:
    """Tests for crawler_agent configuration."""

    @patch.dict(os.environ, {}, clear=False)
    def test_get_crawler_agent_config(self, crawler_agent_service, mock_config_manager):
        """Test _get_crawler_agent_config produces valid config dict."""
        config = crawler_agent_service._get_crawler_agent_config(max_steps=20)

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
    def test_get_crawler_agent_config_gemini_provider(self, crawler_agent_service, mock_config_manager):
        """Test _get_crawler_agent_config maps gemini provider correctly."""
        config = crawler_agent_service._get_crawler_agent_config()
        assert config["llm_profiles"]["manager"]["provider"] == "GoogleGenAI"

    @patch.dict(os.environ, {}, clear=False)
    def test_get_crawler_agent_config_openrouter_provider(self, crawler_agent_service, mock_config_manager):
        """Test _get_crawler_agent_config maps openrouter provider correctly."""
        settings = {
            "ai_provider": "openrouter",
            "ai_model": "qwen/qwen3.6-plus",
            "openrouter_api_key": "sk-or-test-key",
            "crawler_reasoning_mode": True,
            "crawler_streaming": False,
            "crawler_telemetry_enabled": False,
            "ui_parser_mode": "omniparser",
            "omniparser_backend": "replicate",
            "replicate_api_key": "fake_replicate_key",
        }
        mock_config_manager.get.side_effect = lambda key, default=None: settings.get(key, default)

        config = crawler_agent_service._get_crawler_agent_config()

        for profile in config["llm_profiles"].values():
            assert profile["provider"] == "OpenRouter"
            assert profile["model"] == "qwen/qwen3.6-plus"
            assert profile["kwargs"]["api_key"] == "sk-or-test-key"
        assert os.environ["OPENROUTER_API_KEY"] == "sk-or-test-key"

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-env-key"}, clear=False)
    def test_get_crawler_agent_config_openrouter_uses_env_api_key(self, crawler_agent_service, mock_config_manager):
        """Test OpenRouter API key can come from OPENROUTER_API_KEY."""
        settings = {
            "ai_provider": "openrouter",
            "ai_model": "qwen/qwen3.6-plus",
            "openrouter_api_key": None,
            "crawler_reasoning_mode": True,
            "crawler_streaming": False,
            "crawler_telemetry_enabled": False,
            "ui_parser_mode": "omniparser",
            "omniparser_backend": "replicate",
            "replicate_api_key": "fake_replicate_key",
        }
        mock_config_manager.get.side_effect = lambda key, default=None: settings.get(key, default)

        config = crawler_agent_service._get_crawler_agent_config()

        for profile in config["llm_profiles"].values():
            assert profile["kwargs"]["api_key"] == "sk-or-env-key"

    @patch.dict(os.environ, {}, clear=False)
    def test_get_crawler_agent_config_unknown_provider_raises(self, crawler_agent_service, mock_config_manager):
        """Test unknown providers do not silently fall back to Gemini."""
        settings = {
            "ai_provider": "unknown",
            "ai_model": "some-model",
        }
        mock_config_manager.get.side_effect = lambda key, default=None: settings.get(key, default)

        with pytest.raises(ValueError, match="Unsupported AI provider: unknown"):
            crawler_agent_service._get_crawler_agent_config()

    @patch.dict(os.environ, {}, clear=False)
    def test_get_crawler_agent_config_telemetry(self, crawler_agent_service, mock_config_manager):
        """Test _get_crawler_agent_config includes telemetry settings."""
        config = crawler_agent_service._get_crawler_agent_config()
        assert "telemetry" in config
        assert config["telemetry"]["enabled"] is False

    def test_get_crawler_agent_config_includes_omniparser_timeout(
        self, crawler_agent_service, mock_config_manager
    ):
        """Test local OmniParser parse timeout is passed to crawler-agent config."""
        config = crawler_agent_service._get_crawler_agent_config()
        assert config["omniparser_local_url"] == "http://localhost:8000"
        assert config["omniparser_local_parse_timeout_seconds"] == 120


class TestCrawlerAgentServiceTargetPreflight:
    """Tests for launching/verifying the target app before CrawlerAgent starts."""

    @pytest.mark.asyncio
    async def test_execute_runs_wake_preflight_before_target_launch(self, crawler_agent_service):
        order = []

        async def wake_preflight():
            order.append("wake")

        async def target_preflight(app_package):
            order.append(f"target:{app_package}")

        with patch.object(crawler_agent_service, "_ensure_device_awake_before_crawler", side_effect=wake_preflight), \
             patch.object(crawler_agent_service, "_ensure_target_app_active_before_crawler", side_effect=target_preflight), \
             patch.object(crawler_agent_service, "_initialize_agent", new=AsyncMock()), \
             patch.object(crawler_agent_service, "_log_agent_interaction"), \
             patch.dict(sys.modules, self._fake_crawler_agent_modules(success=True)):
            crawler_agent_service._crawler_agent_config = Mock()
            result = await crawler_agent_service.execute_exploration_task(
                run_id=1,
                app_package="com.example.app",
                max_steps=3,
            )

        assert result.success is True
        assert order == ["wake", "target:com.example.app"]

    @pytest.mark.asyncio
    async def test_execute_wake_lock_failure_returns_without_launch_or_agent(self, crawler_agent_service):
        mock_adb = Mock()
        mock_adb.ensure_device_ready_for_crawl.return_value = DeviceReadinessResult(
            success=False,
            error_message="Device is locked. Unlock it manually and start the crawl again.",
        )
        fake_modules = self._fake_crawler_agent_modules(success=True)
        fake_agent = fake_modules["mobile_crawler.domain.crawler_agent.agent.droid.crawler_agent"].CrawlerAgent

        with patch("mobile_crawler.domain.adb_action_executor.ADBActionExecutor", return_value=mock_adb), \
             patch.object(crawler_agent_service, "_ensure_target_app_active_before_crawler", new=AsyncMock()) as target_preflight, \
             patch.object(crawler_agent_service, "_initialize_agent", new=AsyncMock()), \
             patch.object(crawler_agent_service, "_log_agent_interaction"), \
             patch.dict(sys.modules, fake_modules):
            result = await crawler_agent_service.execute_exploration_task(
                run_id=1,
                app_package="com.example.app",
                max_steps=3,
            )

        assert result.success is False
        assert "Unlock it manually" in result.error_message
        target_preflight.assert_not_awaited()
        fake_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_preflight_already_in_target_does_not_launch(self, crawler_agent_service):
        mock_adb = Mock()
        mock_adb.get_current_package.return_value = "com.example.app"

        with patch("mobile_crawler.domain.adb_action_executor.ADBActionExecutor", return_value=mock_adb), \
             patch.object(crawler_agent_service, "_initialize_agent", new=AsyncMock()), \
             patch.object(crawler_agent_service, "_log_agent_interaction"), \
             patch.dict(sys.modules, self._fake_crawler_agent_modules(success=True)):
            crawler_agent_service._crawler_agent_config = Mock()
            result = await crawler_agent_service.execute_exploration_task(
                run_id=1,
                app_package="com.example.app",
                max_steps=3,
            )

        assert result.success is True
        mock_adb.am_start_recovery.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_preflight_launches_and_verifies_before_crawler(self, crawler_agent_service):
        mock_adb = Mock()
        mock_adb.get_current_package.side_effect = ["com.android.launcher", "com.example.app"]
        mock_adb.am_start_recovery.return_value = ActionResult(
            success=True,
            action_type="am_start_recovery",
            target="com.example.app",
        )

        with patch("mobile_crawler.domain.adb_action_executor.ADBActionExecutor", return_value=mock_adb), \
             patch.object(crawler_agent_service, "_initialize_agent", new=AsyncMock()), \
             patch.object(crawler_agent_service, "_log_agent_interaction"), \
             patch.dict(sys.modules, self._fake_crawler_agent_modules(success=True)):
            crawler_agent_service._crawler_agent_config = Mock()
            result = await crawler_agent_service.execute_exploration_task(
                run_id=1,
                app_package="com.example.app",
                max_steps=3,
            )

        assert result.success is True
        mock_adb.am_start_recovery.assert_called_once_with("com.example.app")

    @pytest.mark.asyncio
    async def test_execute_accepts_list_workflow_result(self, crawler_agent_service):
        mock_adb = Mock()
        mock_adb.get_current_package.return_value = "com.example.app"

        fake_modules = self._fake_crawler_agent_modules(success=True)
        agent_instance = fake_modules["mobile_crawler.domain.crawler_agent.agent.droid.crawler_agent"].CrawlerAgent.return_value

        async def _run_list_result():
            return [{"action": "tap"}]

        agent_instance.run.side_effect = _run_list_result

        with patch("mobile_crawler.domain.adb_action_executor.ADBActionExecutor", return_value=mock_adb), \
             patch.object(crawler_agent_service, "_initialize_agent", new=AsyncMock()), \
             patch.dict(sys.modules, fake_modules):
            crawler_agent_service._crawler_agent_config = Mock()
            result = await crawler_agent_service.execute_exploration_task(
                run_id=1,
                app_package="com.example.app",
                max_steps=3,
            )

        assert result.success is True
        assert result.steps_completed == 1

    @pytest.mark.asyncio
    async def test_execute_preflight_failure_returns_without_creating_crawler_agent(self, crawler_agent_service):
        mock_adb = Mock()
        mock_adb.get_current_package.return_value = "com.android.launcher"
        mock_adb.am_start_recovery.return_value = ActionResult(
            success=False,
            action_type="am_start_recovery",
            target="com.example.app",
            error_message="not found",
        )

        fake_modules = self._fake_crawler_agent_modules(success=True)
        fake_agent = fake_modules["mobile_crawler.domain.crawler_agent.agent.droid.crawler_agent"].CrawlerAgent

        with patch("mobile_crawler.domain.adb_action_executor.ADBActionExecutor", return_value=mock_adb), \
             patch.object(crawler_agent_service, "_initialize_agent", new=AsyncMock()), \
             patch.object(crawler_agent_service, "_log_agent_interaction"), \
             patch.dict(sys.modules, fake_modules):
            result = await crawler_agent_service.execute_exploration_task(
                run_id=1,
                app_package="com.example.app",
                max_steps=3,
            )

        assert result.success is False
        assert "Unable to open target app" in result.error_message
        fake_agent.assert_not_called()

    @staticmethod
    def _fake_crawler_agent_modules(success: bool):
        async def _run_result():
            return types.SimpleNamespace(success=success, steps=1, reason="")

        agent_instance = Mock()
        agent_instance.run.side_effect = _run_result
        agent_instance.shared_state = types.SimpleNamespace(
            action_history=[],
            action_outcomes=[],
        )

        crawler_agent_module = types.ModuleType("mobile_crawler.domain.crawler_agent.agent.droid.crawler_agent")
        crawler_agent_module.CrawlerAgent = Mock(return_value=agent_instance)

        return {
            "mobile_crawler.domain.crawler_agent": types.ModuleType("mobile_crawler.domain.crawler_agent"),
            "mobile_crawler.domain.crawler_agent.agent": types.ModuleType("mobile_crawler.domain.crawler_agent.agent"),
            "mobile_crawler.domain.crawler_agent.agent.droid": types.ModuleType("mobile_crawler.domain.crawler_agent.agent.droid"),
            "mobile_crawler.domain.crawler_agent.agent.droid.crawler_agent": crawler_agent_module,
        }


class TestCrawlerAgentServiceLogging:
    """Tests for run logging configuration."""

    def test_configure_run_logging(self, crawler_agent_service, tmp_path):
        """Test configure_run_logging attaches handler."""
        log_dir = str(tmp_path)
        emit_debug = Mock()
        droid_logger = logging.getLogger("crawler_agent")
        original_propagate = droid_logger.propagate

        try:
            with patch('mobile_crawler.domain.crawler_agent_service.CrawlerLogHandler') as mock_handler_class:
                mock_handler = Mock()
                mock_handler_class.return_value = mock_handler
                crawler_agent_service.configure_run_logging(1, log_dir, emit_debug, True)
                assert crawler_agent_service._log_handler is not None
                assert droid_logger.propagate is False
                mock_handler_class.assert_called_once()
        finally:
            crawler_agent_service.clear_run_logging()
            droid_logger.propagate = original_propagate

    def test_clear_run_logging(self, crawler_agent_service, tmp_path):
        """Test clear_run_logging removes handler."""
        log_dir = str(tmp_path)
        emit_debug = Mock()
        droid_logger = logging.getLogger("crawler_agent")
        original_propagate = droid_logger.propagate

        try:
            with patch('mobile_crawler.domain.crawler_agent_service.CrawlerLogHandler') as mock_handler_class:
                mock_handler = Mock()
                mock_handler_class.return_value = mock_handler
                crawler_agent_service.configure_run_logging(1, log_dir, emit_debug, True)
                crawler_agent_service.clear_run_logging()
                assert crawler_agent_service._log_handler is None
                assert droid_logger.propagate is True
        finally:
            droid_logger.propagate = original_propagate


class TestCrawlerAgentServiceActionConversion:
    """Tests for action conversion."""

    def test_convert_crawler_agent_actions(self, crawler_agent_service):
        """Test convert_agent_actions_to_crawler_format maps actions correctly."""
        crawler_agent_actions = [
            {"action": "click", "description": "Click button", "coordinates": [100, 200]},
            {"action": "type", "description": "Enter text", "text": "hello"},
            {"action": "back", "description": "Go back"},
        ]
        actions = crawler_agent_service.convert_agent_actions_to_crawler_format(crawler_agent_actions)

        assert len(actions) == 3
        assert actions[0].action == "click"
        assert actions[1].action == "input"
        assert actions[2].action == "back"
        assert actions[1].input_text == "hello"

    def test_convert_crawler_agent_actions_with_bounding_box(self, crawler_agent_service):
        """Test action conversion creates bounding box from coordinates."""
        crawler_agent_actions = [
            {"action": "click", "description": "Click", "coordinates": [100, 200]},
        ]
        actions = crawler_agent_service.convert_agent_actions_to_crawler_format(crawler_agent_actions)

        assert actions[0].target_bounding_box is not None
        assert isinstance(actions[0].target_bounding_box, BoundingBox)

    def test_convert_crawler_agent_actions_unknown_action(self, crawler_agent_service):
        """Test unknown actions default to click."""
        crawler_agent_actions = [
            {"action": "unknown_action", "description": "Unknown"},
        ]
        actions = crawler_agent_service.convert_agent_actions_to_crawler_format(crawler_agent_actions)
        assert actions[0].action == "click"


class TestCrawlerLogHandler:
    """Tests for CrawlerLogHandler."""

    def test_handler_initialization(self, tmp_path):
        """Test CrawlerLogHandler initialization."""
        log_path = str(tmp_path / "test.jsonl")
        emit_debug = Mock()
        handler = CrawlerLogHandler(1, log_path, emit_debug, True)
        assert handler.run_id == 1
        assert handler.log_path == log_path
        assert handler.enable_ui is True

    def test_handler_emits_to_file(self, tmp_path):
        """Test CrawlerLogHandler writes JSONL to file."""
        log_path = str(tmp_path / "test.jsonl")
        emit_debug = Mock()
        handler = CrawlerLogHandler(1, log_path, emit_debug, True)

        record = Mock()
        record.getMessage.return_value = "test log message"
        record.levelname = "INFO"

        handler.emit(record)

        with open(log_path) as f:
            line = f.readline()
            event = json.loads(line)
            assert event["message"] == "test log message"
            assert event["level"] == "INFO"
            assert event["run_id"] == 1

    def test_handler_ui_disabled(self, tmp_path):
        """Test CrawlerLogHandler does not emit to UI when disabled."""
        log_path = str(tmp_path / "test.jsonl")
        emit_debug = Mock()
        handler = CrawlerLogHandler(1, log_path, emit_debug, False)

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
