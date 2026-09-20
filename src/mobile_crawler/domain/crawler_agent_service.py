"""Internal crawler-agent service integration for Mobile Crawler."""

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from workflows.errors import WorkflowCancelledByUser

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.domain.action_verifier import ActionVerifier
from mobile_crawler.domain.authentication import AuthenticationSession
from mobile_crawler.domain.context_guard import (
    AppSwitchRecovery,
    DeviceContextCapture,
    StepSkipReason,
    UIDumpValidator,
)
from mobile_crawler.domain.crawler_agent.agent.common.events import (
    ScreenshotEvent,
    StepAdvanceEvent,
    StepPausedEvent,
    ToolExecutionEvent,
)
from mobile_crawler.domain.crawler_agent.agent.droid.events import AppOpenerResponseEvent
from mobile_crawler.domain.crawler_agent.agent.executor.events import ExecutorResponseEvent
from mobile_crawler.domain.crawler_agent.agent.fast_agent.events import FastAgentResponseEvent
from mobile_crawler.domain.crawler_agent.agent.manager.events import ManagerResponseEvent
from mobile_crawler.domain.errors import ErrorContext, FatalError
from mobile_crawler.domain.guided_scenarios_generator import guided_scenarios_config_key
from mobile_crawler.domain.human_fallback import HumanFallback, HumanFallbackConfig, HumanPrompter
from mobile_crawler.domain.models import AIAction, BoundingBox
from mobile_crawler.domain.prompt_builder import format_login_and_form_data
from mobile_crawler.domain.run_outcome import build_guided_progress
from mobile_crawler.domain.stats_collector_span_processor import OTEL_AVAILABLE, StatsCollectorSpanProcessor
from mobile_crawler.domain.step_phase import StepPhase, StepPhaseStateMachine
from mobile_crawler.domain.step_phase_models import StepPhaseTransition
from mobile_crawler.domain.ui_wait_predicate import AdaptiveWaitConfig, UIWaitPredicate, is_omniparser_backed
from mobile_crawler.infrastructure.ai_interaction_repository import AIInteraction, AIInteractionRepository
from mobile_crawler.infrastructure.step_phase_repository import StepPhaseRepository

logger = logging.getLogger(__name__)


class CancelledErrorFilter(logging.Filter):
    """Filter that suppresses asyncio.CancelledError from ERROR level logs.

    When tasks are cancelled due to timeout, CancelledError propagates through
    async call stacks and gets logged by instrumentation libraries (e.g.,
    llama_index_instrumentation). This filter prevents these expected cancellations
    from appearing as ERROR level logs since they are handled gracefully.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Suppress CancelledError at ERROR level - it's an expected cancellation
        if record.levelno == logging.ERROR:
            msg = record.getMessage()
            exc_info = record.exc_info
            if exc_info and exc_info[0] is asyncio.CancelledError:
                return False
            # Also check for CancelledError in the message
            if "CancelledError" in msg and "task" in msg.lower():
                return False
        return True


# Install the filter on the root logger to catch all loggers
# This ensures CancelledError doesn't appear as ERROR in any handler
_root_logger = logging.getLogger()
_cancelled_filter = CancelledErrorFilter()
_root_logger.addFilter(_cancelled_filter)

# Also add to common library loggers that might log CancelledError
for lib_logger in ["llama_index", "llama_index_instrumentation", "crawler_agent"]:
    logging.getLogger(lib_logger).addFilter(_cancelled_filter)

# Optional import for OmniParser integration
try:
    from mobile_crawler.domain.omni_parser_client import OmniParserClient
    from mobile_crawler.domain.ui_context import UIContextManager

    OMNIPARSER_AVAILABLE = True
except ImportError:
    OMNIPARSER_AVAILABLE = False
    OmniParserClient = None
    UIContextManager = None


class CrawlerLogHandler(logging.Handler):
    """Forward Crawler logs to UI and JSONL file per run."""

    def __init__(self, run_id: int, log_path: str, emit_debug, enable_ui: bool):
        super().__init__()
        self.run_id = run_id
        self.log_path = log_path
        self.emit_debug = emit_debug
        self.enable_ui = enable_ui

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
            payload = {
                "timestamp": time.time(),
                "level": record.levelname,
                "run_id": self.run_id,
                "message": message,
            }

            with open(self.log_path, "a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(payload, ensure_ascii=True) + "\n")

            if self.enable_ui and self.emit_debug:
                # emit_debug is CrawlerLoop._emit_event — call with method name first
                self.emit_debug("on_debug_log", self.run_id, 0, message)
        except Exception as e:
            # Log the failure but avoid recursion by not re-emitting
            logger.error(f"CrawlerLogHandler emit failed: {e}", exc_info=True)


@dataclass
class CrawlerGoal:
    """Goal representation for Crawler agent."""

    description: str
    max_steps: int = 15
    reasoning: bool = True
    app_package: str | None = None


@dataclass
class CrawlerRunResult:
    """Result from Crawler agent execution."""

    success: bool
    steps_completed: int
    actions_taken: list[dict[str, Any]]
    final_state: dict[str, Any]
    error_message: str | None = None
    total_duration_ms: float = 0.0


class CrawlerAgentService:
    """Service for integrating the internal crawler_agent runtime with Mobile Crawler.

    All device actions (tap, scroll, input, navigate) are executed through the
    internalized crawler agent's ADB-backed Android runtime.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        ai_interaction_repository: AIInteractionRepository | None,
        device_id: str,
    ):
        """Initialize crawler-agent service.

        Args:
            config_manager: Configuration manager for crawler settings
            ai_interaction_repository: Repository for logging AI interactions
            device_id: ADB device serial identifier. All device interactions route
                       through ADB using this serial.
        """
        self.config_manager = config_manager
        self.ai_interaction_repository = ai_interaction_repository
        self.device_id = device_id
        self._crawler_agent = None
        self._crawler_agent_config = None
        # Set by the crawl loop so Human Fallback can reach the GUI; None means fallback is off.
        self.human_prompter: HumanPrompter | None = None
        self._auth_session: AuthenticationSession | None = None
        self._current_handler = None
        self._handler_loop = None
        self._log_handler = None
        self._is_initialized = False
        self._ui_context_manager = None
        self._omni_parser_client = None

        # Step phase machine and observers (set per-run via begin_step_tracking)
        self._step_phase_machine: StepPhaseStateMachine | None = None
        self._step_phase_repository: StepPhaseRepository | None = None
        self._ui_wait_predicate: UIWaitPredicate | None = None
        self._action_verifier: ActionVerifier | None = None
        self._current_run_id: int | None = None
        # Per-run id set on Phoenix/Langfuse traces so a run's telemetry can be found later.
        self.trace_session_id: str | None = None
        self._current_step_number: int = 0
        # Dedicated counter for AI Monitor step numbering (Fix 5). Advanced on each
        # new decide cycle (Manager/AppOpener/FastAgent response) instead of reusing
        # `self._current_step_number + 1`, so numbering stays monotonic even when a
        # cycle aborts mid-way and no ToolExecutionEvent ever fires to advance the
        # tool-level counter.
        self._ai_call_step_number: int = 0
        self._emit_step_phase_event = None  # Callback to CrawlerLoop._emit_event
        self._emit_state_change = None  # Callback for CrawlState transitions (set in begin_step_tracking)
        self._sub_phase_starts: dict[str, float] = {}
        self._phase_metadata: dict[str, dict[str, Any]] = {}
        self._pending_step_timing: dict[str, Any] = {}

        # Initialize OmniParser if available
        if OMNIPARSER_AVAILABLE:
            self._initialize_omni_parser()

        # OTel stats collector — always active regardless of Phoenix/telemetry setting
        self._stats_processor: StatsCollectorSpanProcessor = StatsCollectorSpanProcessor()
        self._instrumentation_done: bool = False

    def _get_crawler_agent_config(
        self,
        max_steps: int = 15,
        target_package: str | None = None,
        step_by_step: bool = False,
    ) -> dict[str, Any]:
        """Convert crawler configuration to internal crawler_agent format.

        Returns:
            Crawler agent configuration dictionary
        """
        # Get LLM configuration from crawler config
        ai_provider = self.config_manager.get("ai_provider", "gemini")
        ai_model = self.config_manager.get("ai_model", "gemini-1.5-flash")

        # Map crawler providers to internal format
        provider_mapping = {
            "gemini": "GoogleGenAI",
            "openai": "OpenAI",
            "anthropic": "AnthropicAI",
            "ollama": "Ollama",
            "openrouter": "OpenRouter",
        }

        if ai_provider not in provider_mapping:
            raise ValueError(f"Unsupported AI provider: {ai_provider}")

        droid_provider = provider_mapping[ai_provider]

        def resolve_api_key(primary_key: str, env_keys: list[str]) -> str | None:
            key_value = self.config_manager.get(primary_key)
            if not key_value:
                try:
                    key_value = self.config_manager.user_config_store.get_secret_plaintext(primary_key)
                except (KeyError, AttributeError):
                    key_value = None
            if not key_value:
                for env_key in env_keys:
                    key_value = os.environ.get(env_key)
                    if key_value:
                        break
            return key_value

        config = {
            "agent": {
                "max_steps": max_steps,
                "reasoning": self.config_manager.get("crawler_reasoning_mode", True),
                "streaming": self.config_manager.get("crawler_streaming", False),
                "step_by_step": bool(step_by_step),
            },
            "device": {
                "serial": self.device_id,
                "auto_setup": False,  # We handle device setup separately
            },
            "ui_parser_mode": self.config_manager.get("ui_parser_mode", "omniparser"),
            "omniparser_backend": self.config_manager.get("omniparser_backend", "replicate"),
            "omniparser_api_key": resolve_api_key("replicate_api_key", ["REPLICATE_API_KEY"]) or "",
            "omniparser_local_url": self.config_manager.get("omniparser_local_url", "http://localhost:8001"),
            "omniparser_local_parse_timeout_seconds": self.config_manager.get(
                "omniparser_local_parse_timeout_seconds", 120
            ),
            "target_package": target_package,
            "status_bar_exclusion_px": self.config_manager.get("top_bar_height", 80),
            "bottom_bar_exclusion_px": self.config_manager.get("bottom_bar_height", 0),
        }

        # Set Replicate API key in environment (both names) for the agent
        replicate_key = config["omniparser_api_key"]
        if replicate_key:
            os.environ["REPLICATE_API_KEY"] = replicate_key
            os.environ["REPLICATE_API_TOKEN"] = replicate_key

        config["llm_profiles"] = {
            "manager": {
                "provider": droid_provider,
                "model": ai_model,
                "temperature": 0.1,
                "kwargs": {"max_tokens": 8192},
            },
            # Gemini thinking tokens count against max_tokens, so small limits
            # truncate the visible answer (MAX_TOKENS) before the action is emitted.
            "executor": {
                "provider": droid_provider,
                "model": ai_model,
                "temperature": 0.0,
                "kwargs": {"max_tokens": 4096},
            },
            "fast_agent": {
                "provider": droid_provider,
                "model": ai_model,
                "temperature": 0.0,
                "kwargs": {"max_tokens": 1024},
            },
            "app_opener": {
                "provider": droid_provider,
                "model": ai_model,
                "temperature": 0.0,
                "kwargs": {"max_tokens": 2048},
            },
            "structured_output": {
                "provider": droid_provider,
                "model": ai_model,
                "temperature": 0.0,
                "kwargs": {"max_tokens": 1024},
            },
        }
        # Telemetry: respect explicit config setting; default off since the
        # PostHog project key is no longer bundled with the app.
        telemetry_enabled = self.config_manager.get("crawler_telemetry_enabled", False)
        config["telemetry"] = {"enabled": bool(telemetry_enabled)}

        # Configure Tracing (Arize Phoenix / Langfuse)
        enable_tracing = self.config_manager.get("enable_tracing", False)
        tracing_provider = self.config_manager.get("tracing_provider", "phoenix")
        phoenix_url = self.config_manager.get("phoenix_url", "http://localhost:6006")
        langfuse_host = self.config_manager.get("langfuse_host", "https://cloud.langfuse.com")
        langfuse_pub = self.config_manager.get("langfuse_public_key", "")
        langfuse_sec = self.config_manager.get("langfuse_secret_key", "")

        config["tracing"] = {
            "enabled": enable_tracing,
            "provider": tracing_provider,
            "langfuse_screenshots": False,
            "langfuse_secret_key": langfuse_sec,
            "langfuse_public_key": langfuse_pub,
            "langfuse_host": langfuse_host,
            "langfuse_session_id": self.trace_session_id or "",
        }

        # Inject environment variables for OpenTelemetry tracing tools
        if enable_tracing:
            if tracing_provider == "phoenix":
                os.environ["PHOENIX_URL"] = phoenix_url
                logger.info(f"Observability: Phoenix tracing enabled targeting endpoint {phoenix_url}")
            elif tracing_provider == "langfuse":
                if langfuse_pub:
                    os.environ["LANGFUSE_PUBLIC_KEY"] = langfuse_pub
                if langfuse_sec:
                    os.environ["LANGFUSE_SECRET_KEY"] = langfuse_sec
                if langfuse_host:
                    os.environ["LANGFUSE_HOST"] = langfuse_host
                logger.info(f"Observability: Langfuse cloud tracing enabled targeting host {langfuse_host}")

        def set_llm_api_key(api_key: str) -> None:
            for profile in config["llm_profiles"].values():
                profile["kwargs"]["api_key"] = api_key

        # Add API keys based on provider
        if ai_provider == "gemini":
            api_key = resolve_api_key("gemini_api_key", ["GEMINI_API_KEY", "GOOGLE_API_KEY"])
            if api_key:
                set_llm_api_key(api_key)
                os.environ["GEMINI_API_KEY"] = api_key
                os.environ["GOOGLE_API_KEY"] = api_key
        elif ai_provider == "openai":
            api_key = resolve_api_key("openai_api_key", ["OPENAI_API_KEY"])
            if api_key:
                set_llm_api_key(api_key)
                os.environ["OPENAI_API_KEY"] = api_key
        elif ai_provider == "anthropic":
            api_key = resolve_api_key("anthropic_api_key", ["ANTHROPIC_API_KEY"])
            if api_key:
                set_llm_api_key(api_key)
                os.environ["ANTHROPIC_API_KEY"] = api_key
        elif ai_provider == "openrouter":
            api_key = resolve_api_key("openrouter_api_key", ["OPENROUTER_API_KEY"])
            if api_key:
                set_llm_api_key(api_key)
                os.environ["OPENROUTER_API_KEY"] = api_key

        return config

    def configure_run_logging(self, run_id: int, log_dir: str, emit_debug, enable_ui: bool) -> None:
        """Attach a Crawler log handler for UI/debug and JSONL output.

        Always enables UI forwarding so logs reach both the JSONL file
        and the root QLogHandler bridge in MainWindow.
        """
        log_path = os.path.join(log_dir, "crawler_trace.jsonl")
        handler = CrawlerLogHandler(run_id, log_path, emit_debug, True)
        handler.setLevel(logging.DEBUG)

        # Patch the crawler_agent logger and known children for debug visibility.
        for name in ["crawler_agent", "crawler_agent.agent", "crawler_agent.tools", "crawler_agent.config_manager"]:
            lg = logging.getLogger(name)
            lg.setLevel(logging.DEBUG)

        droid_logger = logging.getLogger("crawler_agent")
        droid_logger.addHandler(handler)
        droid_logger.propagate = False
        self._log_handler = handler

    def clear_run_logging(self) -> None:
        """Detach Crawler log handler if attached."""
        if self._log_handler:
            droid_logger = logging.getLogger("crawler_agent")
            droid_logger.removeHandler(self._log_handler)
            droid_logger.propagate = True
            self._log_handler = None

    async def _initialize_agent(
        self,
        max_steps: int = 15,
        target_package: str | None = None,
        step_by_step: bool = False,
    ) -> None:
        """Initialize Crawler agent with current configuration."""
        if self._is_initialized:
            if self._crawler_agent_config is not None:
                self._crawler_agent_config.agent.max_steps = max_steps
                self._crawler_agent_config.target_package = target_package
                self._crawler_agent_config.agent.step_by_step = step_by_step
            return

        self._stats_processor.reset()

        try:
            # Import internalized crawler_agent components
            from mobile_crawler.domain.crawler_agent.config_manager.config_manager import CrawlerConfig

            # Create Crawler configuration
            config_dict = self._get_crawler_agent_config(
                max_steps, target_package=target_package, step_by_step=step_by_step
            )
            self._crawler_agent_config = CrawlerConfig.from_dict(config_dict)

            self._is_initialized = True
            logger.info("Crawler agent initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Crawler agent: {e}")
            raise

    async def _ensure_target_app_active_before_crawler(
        self,
        app_package: str,
    ) -> None:
        """Launch and verify the target package before any crawler work starts."""
        from mobile_crawler.domain.adb_action_executor import ADBActionExecutor

        attempts = int(self.config_manager.get("target_app_launch_attempts", 3) or 3)
        adb_executor = ADBActionExecutor(device_id=self.device_id)
        current_package = adb_executor.get_current_package()

        if current_package == app_package:
            logger.info("Target app already active before crawler startup: %s", app_package)
            return

        logger.info(
            "Target app is not active before crawler startup " "(current=%s, target=%s). Launching target app.",
            current_package,
            app_package,
        )

        last_error = None
        for attempt in range(1, attempts + 1):
            launch_result = adb_executor.am_start_recovery(app_package)
            if not launch_result.success:
                last_error = launch_result.error_message or "ADB launch command failed"
                logger.warning(
                    "Target app launch attempt %s/%s failed: %s",
                    attempt,
                    attempts,
                    last_error,
                )

            await asyncio.sleep(0.5)
            current_package = adb_executor.get_current_package()
            if current_package == app_package:
                logger.info(
                    "Target app active after preflight launch attempt %s/%s: %s",
                    attempt,
                    attempts,
                    app_package,
                )
                return

            logger.warning(
                "Target app preflight verification failed on attempt %s/%s " "(current=%s, target=%s)",
                attempt,
                attempts,
                current_package,
                app_package,
            )

        detail = f"last_error={last_error}" if last_error else f"current_package={current_package}"
        raise RuntimeError(
            f"Unable to open target app '{app_package}' before crawler startup after " f"{attempts} attempts ({detail})"
        )

    async def _ensure_device_awake_before_crawler(self) -> None:
        """Wake the selected device and fail fast if it is still locked."""
        if not self.config_manager.get("pre_crawl_wake_device", True):
            return

        from mobile_crawler.domain.adb_action_executor import ADBActionExecutor

        logger.info("Waking device before crawl...")
        adb_executor = ADBActionExecutor(device_id=self.device_id)
        result = adb_executor.ensure_device_ready_for_crawl(
            timeout_seconds=float(self.config_manager.get("pre_crawl_wake_timeout_seconds", 5.0) or 5.0),
            unlock_swipe=bool(self.config_manager.get("pre_crawl_unlock_swipe", True)),
        )

        if not result.success:
            message = result.error_message or "Unable to verify device wake/unlock state before crawl."
            logger.error(message)
            raise RuntimeError(message)

        logger.info("Device is awake and unlocked.")

    def _setup_instrumentation(self) -> None:
        """Instrument LlamaIndex with OTel and register the stats collector processor.

        Called once per service lifetime. Safe to call multiple times (idempotent).
        Does not require Phoenix to be running — the stats processor works standalone.
        """
        if self._instrumentation_done or not OTEL_AVAILABLE:
            return
        try:
            from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider

            # Reuse existing provider if one is already set (e.g. by Phoenix/Langfuse)
            existing = trace.get_tracer_provider()
            if hasattr(existing, "add_span_processor"):
                provider = existing
            else:
                provider = TracerProvider()
                trace.set_tracer_provider(provider)

            provider.add_span_processor(self._stats_processor)

            instrumentor = LlamaIndexInstrumentor()
            if not instrumentor.is_instrumented_by_opentelemetry:
                instrumentor.instrument(tracer_provider=provider)

            self._instrumentation_done = True
            logger.debug("OTel LlamaIndex instrumentation active; stats collector registered")
        except Exception as e:
            logger.debug(f"OTel instrumentation setup skipped: {e}")

    def _initialize_omni_parser(self) -> None:
        """Initialize OmniParser client and UI context manager."""
        try:
            from mobile_crawler.infrastructure.database import DatabaseManager

            self._omni_parser_client = OmniParserClient(self.config_manager)
            logger.info(f"OmniParser client initialized (backend: {self._omni_parser_client.backend.value})")

            db_manager = DatabaseManager()
            db_conn = db_manager.get_connection()
            self._ui_context_manager = UIContextManager(db_conn, self._omni_parser_client)
            logger.info("UIContextManager initialized")

        except Exception as e:
            logger.warning(f"Failed to initialize OmniParser: {e}")
            self._omni_parser_client = None
            self._ui_context_manager = None

    def begin_step_tracking(
        self,
        run_id: int,
        emit_step_phase_event=None,
        emit_state_change=None,
        screenshots_dir: str | None = None,
    ) -> None:
        """Initialize step phase tracking for a run.

        Args:
            run_id: The current run ID.
            emit_step_phase_event: Callback to emit phase transition events
                                    to CrawlerLoop listeners. Signature:
                                    (method_name, *args) -> None
            screenshots_dir: Directory to write per-step screenshots (for AI Monitor panel).
        """
        self._current_run_id = run_id
        self.trace_session_id = f"run-{run_id}-{uuid.uuid4().hex[:8]}"
        self._current_step_number = 0
        self._ai_call_step_number = 0
        self._emit_step_phase_event = emit_step_phase_event
        self._emit_state_change = emit_state_change
        self._sub_phase_starts = {}
        self._phase_metadata = {}
        self._pending_step_timing = {}
        self._screenshots_dir = screenshots_dir
        self._screenshot_written: set[tuple[int, int]] = set()  # (run_id, step_number)

        # Initialize step phase machine with a listener that persists transitions
        self._step_phase_machine = StepPhaseStateMachine()
        self._step_phase_machine.add_listener(self._on_phase_transition)

        # Initialize repository for persistence
        from mobile_crawler.infrastructure.database import DatabaseManager

        db_manager = DatabaseManager()
        self._step_phase_repository = StepPhaseRepository(db_manager)

        # Initialize wait predicate and verifier (lazy -- will be fully wired
        # when crawler_agent provides state_provider/driver)
        self._ui_wait_predicate = None  # Wired after agent init
        self._action_verifier = None  # Wired after agent init

        # Context guardrails (Plan 02: UI dump validation + app mismatch detection)
        self._context_capture: DeviceContextCapture | None = None
        self._ui_dump_validator = UIDumpValidator()
        self._target_package: str | None = None
        self._current_device_context = None  # Set during context capture for downstream recovery

        # App-switch recovery (Plan 03: detect and recover from app switches)
        self._app_switch_recovery: AppSwitchRecovery | None = None
        self._adb_executor: Any | None = None

        logger.info(f"Step phase tracking initialized for run {run_id}")

    def _wire_observers_to_agent(self) -> None:
        """Wire UIWaitPredicate, ActionVerifier, and DeviceContextCapture to the agent.

        Called after Crawler agent is initialized, when state_provider, driver,
        and ADB executor are available on the agent object.
        """
        if not self._crawler_agent:
            return

        state_provider = getattr(self._crawler_agent, "state_provider", None)
        driver = getattr(self._crawler_agent, "driver", None)

        if state_provider:

            def latest_state():
                action_ctx = getattr(self._crawler_agent, "action_ctx", None)
                latest = getattr(action_ctx, "ui", None) if action_ctx else None
                if latest is not None:
                    return latest
                shared_state = getattr(self._crawler_agent, "shared_state", None)
                if shared_state and getattr(shared_state, "a11y_tree", None):
                    state = type("LatestUIState", (), {})()
                    state.elements = shared_state.a11y_tree
                    state.formatted_text = getattr(shared_state, "formatted_device_state", "")
                    state.phone_state = getattr(shared_state, "phone_state", {})
                    return state
                return None

            async def current_app():
                if driver and hasattr(driver, "_get_current_app"):
                    return await driver._get_current_app()
                return ""

            expensive_state_polling = is_omniparser_backed(getattr(state_provider, "ui_parser_mode", None))
            grace_delay_s = (
                self._crawler_agent_config.agent.wait_for_stable_ui if self._crawler_agent_config is not None else 0.3
            )
            self._ui_wait_predicate = UIWaitPredicate(
                state_provider=state_provider,
                config=AdaptiveWaitConfig(self.config_manager),
                latest_state_provider=latest_state,
                current_app_provider=current_app if driver else None,
                expensive_state_polling=expensive_state_polling,
                grace_delay_s=grace_delay_s,
            )
            if driver:
                self._action_verifier = ActionVerifier(
                    state_provider=state_provider,
                    driver=driver,
                    latest_state_provider=latest_state,
                    expensive_state_capture=expensive_state_polling,
                )

        # Wire DeviceContextCapture for app-switch detection (Plan 02)
        if self._target_package and driver:
            from mobile_crawler.domain.adb_action_executor import ADBActionExecutor

            adb_executor = ADBActionExecutor(device_id=self.device_id)
            self._context_capture = DeviceContextCapture(
                target_package=self._target_package,
                adb_executor=adb_executor,
            )
            self._adb_executor = adb_executor

            # Wire app-switch recovery (Plan 03)
            self._app_switch_recovery = AppSwitchRecovery(
                target_package=self._target_package,
                adb_executor=adb_executor,
                context_capture=self._context_capture,
            )
            logger.info(
                f"DeviceContextCapture and AppSwitchRecovery wired with " f"target_package={self._target_package}"
            )

        # after_sleep_action is now a real delay driven by UIWaitPredicate
        # (wait_for_ui_settled) in the agents — no longer forced to 0.0

    def _start_sub_phase(self, phase_name: str) -> None:
        """Record the start timestamp for a diagnostic sub-phase."""
        self._sub_phase_starts[phase_name] = time.perf_counter()

    def _end_sub_phase(
        self,
        phase_name: str,
        *,
        metadata_key: str | None = None,
        parent_phase: StepPhase | str | None = None,
    ) -> float | None:
        """Finish a diagnostic sub-phase and store its elapsed milliseconds."""
        start = self._sub_phase_starts.pop(phase_name, None)
        if start is None:
            return None

        duration_ms = (time.perf_counter() - start) * 1000
        self._add_sub_phase_timing(
            metadata_key or f"{phase_name}_ms",
            duration_ms,
            parent_phase=parent_phase,
        )
        return duration_ms

    def _add_sub_phase_timing(
        self,
        key: str,
        duration_ms: float | None,
        *,
        parent_phase: StepPhase | str | None = None,
    ) -> None:
        """Add an elapsed sub-phase duration to phase transition metadata."""
        if duration_ms is None:
            return
        try:
            normalized_duration_ms = round(float(duration_ms), 3)
        except (TypeError, ValueError):
            return

        phase_key = self._metadata_phase_key(parent_phase)
        metadata = self._phase_metadata.setdefault(phase_key, {})
        sub_phases = metadata.setdefault("sub_phases", {})
        sub_phases[key] = normalized_duration_ms

    def _add_validation_retry(
        self,
        reason: str,
        *,
        parent_phase: StepPhase | str | None = StepPhase.DECIDE,
        timestamp: str | None = None,
        attempt: int | None = None,
    ) -> None:
        """Record a Manager validation retry with context."""
        phase_key = self._metadata_phase_key(parent_phase)
        metadata = self._phase_metadata.setdefault(phase_key, {})
        retries = metadata.setdefault("validation_retries", [])
        retry = {
            "reason": reason,
            "timestamp": timestamp or datetime.now().isoformat(),
        }
        if attempt is not None:
            retry["attempt"] = attempt
        retries.append(retry)

    def _metadata_phase_key(self, phase: StepPhase | str | None) -> str:
        if isinstance(phase, StepPhase):
            return phase.value
        if phase:
            return str(phase)
        if self._step_phase_machine:
            return self._step_phase_machine.current_phase.value
        return StepPhase.CAPTURE.value

    def _pop_phase_metadata(self, phase: StepPhase) -> dict[str, Any]:
        return self._phase_metadata.pop(phase.value, {})

    def _buffer_workflow_timing(self, event) -> None:
        """Buffer Manager/Executor timing until the following tool event creates a step."""
        from mobile_crawler.domain.crawler_agent.agent.executor.events import ExecutorResponseEvent
        from mobile_crawler.domain.crawler_agent.agent.manager.events import (
            ManagerContextEvent,
            ManagerResponseEvent,
        )

        if isinstance(event, ManagerContextEvent):
            app_card_load_ms = getattr(event, "app_card_load_ms", None)
            if app_card_load_ms is not None:
                self._pending_step_timing["app_card_load_ms"] = app_card_load_ms
        elif isinstance(event, ManagerResponseEvent):
            manager_llm_ms = getattr(event, "manager_llm_ms", None)
            if manager_llm_ms is not None:
                self._pending_step_timing["manager_llm_ms"] = manager_llm_ms
            retries = getattr(event, "validation_retries", None) or []
            if retries:
                self._pending_step_timing.setdefault("validation_retries", []).extend(retries)
        elif isinstance(event, ExecutorResponseEvent):
            executor_llm_ms = getattr(event, "executor_llm_ms", None)
            if executor_llm_ms is not None:
                self._pending_step_timing["executor_llm_ms"] = executor_llm_ms

    def _apply_pending_step_timing(self) -> None:
        """Attach buffered Manager/Executor timings to the current DECIDE phase."""
        pending = self._pending_step_timing
        if not pending:
            return

        for key in ("app_card_load_ms", "manager_llm_ms", "executor_llm_ms"):
            self._add_sub_phase_timing(key, pending.get(key), parent_phase=StepPhase.DECIDE)

        for retry in pending.get("validation_retries", []):
            self._add_validation_retry(
                str(retry.get("reason", "Validation retry")),
                timestamp=retry.get("timestamp"),
                attempt=retry.get("attempt"),
            )

        self._pending_step_timing = {}

    def _on_phase_transition(self, old_phase: StepPhase, new_phase: StepPhase) -> None:
        """Listener callback for state machine transitions.

        Persists the transition to the database and emits events to the UI.
        """
        if not self._current_run_id or not self._step_phase_repository:
            return

        duration_ms = None
        if self._step_phase_machine:
            duration_ms = self._step_phase_machine.get_phase_duration(old_phase)
            if duration_ms is not None:
                duration_ms = duration_ms * 1000  # Convert seconds to ms

        metadata = self._pop_phase_metadata(old_phase)

        transition = StepPhaseTransition(
            id=None,
            run_id=self._current_run_id,
            step_number=self._current_step_number,
            from_phase=old_phase.value,
            to_phase=new_phase.value,
            timestamp=datetime.now(),
            action_type=None,
            duration_ms=duration_ms,
            metadata_json=json.dumps(metadata) if metadata else None,
        )

        try:
            self._step_phase_repository.record_transition(transition)
            self._step_phase_repository.update_step_current_phase(
                self._current_run_id,
                self._current_step_number,
                new_phase.value,
            )

            # Record device context for normal steps
            if self._adb_executor:
                package = self._adb_executor.get_current_package()
                activity = self._adb_executor.get_current_activity()
                if package and activity:
                    try:
                        self._step_phase_repository.record_device_context(
                            self._current_run_id, self._current_step_number, package, activity
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record device context: {e}")

        except Exception as e:
            logger.warning(f"Failed to persist phase transition: {e}")

        # Emit event to CrawlerLoop listeners
        if self._emit_step_phase_event:
            try:
                self._emit_step_phase_event(
                    "on_step_phase_transition",
                    self._current_run_id,
                    self._current_step_number,
                    old_phase.value,
                    new_phase.value,
                    duration_ms or 0.0,
                )
            except Exception as e:
                logger.warning(f"Failed to emit step phase event: {e}")

    async def _handle_tool_execution_event(self, event) -> None:
        """Handle a ToolExecutionEvent from internal crawler_agent's event stream.

        Drives the step phase machine through transitions based on
        tool execution events. Before proceeding to DECIDE, validates:
        - Context pre-check (D-02): current package matches target app
        - UI dump validation (D-03): UI data is parseable and non-empty

        When either check fails, the step skips DECIDE/EXECUTE and
        transitions CAPTURE -> CHECKPOINT with skip reason metadata,
        preserving run stability per D-04.
        """
        if not self._step_phase_machine:
            return

        tool_name = getattr(event, "tool_name", "unknown")
        success = getattr(event, "success", False)

        # Increment step number on each tool execution
        self._current_step_number += 1
        self._apply_pending_step_timing()
        duration_ms = getattr(event, "duration_ms", None)
        self._add_sub_phase_timing(
            "tool_execution_ms",
            duration_ms,
            parent_phase=StepPhase.EXECUTE,
        )

        if self._emit_step_phase_event and duration_ms is not None:
            try:
                self._emit_step_phase_event(
                    "on_action_timing",
                    self._current_run_id,
                    self._current_step_number,
                    tool_name,
                    success,
                    duration_ms,
                )
            except Exception as e:
                logger.warning(f"Failed to emit action timing event: {e}")

        logger.debug(f"Step {self._current_step_number}: tool={tool_name} " f"success={success}")

        # --- Context pre-check (D-02): compare package against target ---
        skip_reason = None

        if self._context_capture:
            try:
                device_ctx = await self._context_capture.capture()
                self._current_device_context = device_ctx

                if not device_ctx.is_target_app:
                    # App switch detected — try recovery before skipping (Plan 03)
                    if self._app_switch_recovery:
                        logger.warning(
                            f"Step {self._current_step_number}: app switch detected "
                            f"(captured={device_ctx.package}, expected="
                            f"{self._target_package}). Attempting recovery."
                        )
                        recovered, attempts = await self._app_switch_recovery.detect_and_recover()

                        if recovered:
                            # Re-capture context after successful recovery
                            device_ctx = await self._context_capture.capture()
                            self._current_device_context = device_ctx
                            logger.info(
                                f"Step {self._current_step_number}: app switch recovery "
                                f"succeeded on attempt {attempts[-1].attempt_number}. "
                                f"Continuing with fresh context."
                            )
                            # Continue with the step normally — no skip
                        else:
                            # MAX_CONSECUTIVE_FAILURES reached — abort the run
                            logger.error(
                                f"Step {self._current_step_number}: app switch recovery "
                                f"failed after {len(attempts)} attempts. Aborting run."
                            )
                            # Record transition with abort metadata
                            self._step_phase_machine.transition_to(StepPhase.CHECKPOINT)
                            raise FatalError(
                                f"Aborting: {len(attempts)} consecutive app-switch " f"recovery failures",
                                context=ErrorContext(run_id=self._current_run_id),
                            )
                    else:
                        # No recovery handler available — fall back to skip behavior
                        logger.warning(
                            f"Step {self._current_step_number}: app mismatch detected "
                            f"(current={device_ctx.package}, target="
                            f"{self._target_package}). Skipping DECIDE/EXECUTE."
                        )
                        skip_reason = StepSkipReason.TARGET_APP_MISMATCH
            except Exception as e:
                logger.warning(f"Step {self._current_step_number}: context capture failed: {e}")

        # --- UI dump validation (D-03): check parseable and non-empty ---
        if skip_reason is None and self._ui_dump_validator:
            try:

                async def get_ui_data():
                    """Get UI data without triggering duplicate expensive parser work."""
                    # 1. Prefer shared_state.a11y_tree, where Manager/FastAgent stores
                    #    the latest already-parsed UIState.elements.
                    if self._crawler_agent:
                        shared_state = getattr(self._crawler_agent, "shared_state", None)
                        if shared_state:
                            a11y = getattr(shared_state, "a11y_tree", None)
                            if a11y:
                                return a11y

                    # 2. Fall back to a live read only when no parsed shared state exists.
                    #    Handle both UIState objects and dict-style raw states.
                    if self._crawler_agent and hasattr(self._crawler_agent, "state_provider"):
                        state_provider = self._crawler_agent.state_provider
                        if state_provider and hasattr(state_provider, "get_state"):
                            try:
                                live_started = time.perf_counter()
                                state = await state_provider.get_state()
                                self._add_sub_phase_timing(
                                    "ui_dump_live_state_capture_ms",
                                    (time.perf_counter() - live_started) * 1000,
                                    parent_phase=StepPhase.CAPTURE,
                                )
                                if state and hasattr(state, "elements"):
                                    elements = getattr(state, "elements", None)
                                    if elements:
                                        return elements
                                if state and isinstance(state, dict):
                                    a11y = state.get("a11y_tree")
                                    if a11y:
                                        return a11y
                            except Exception:
                                pass

                    return None

                # Use validate with retry for transient failures (per D-04)
                validation = await self._ui_dump_validator.validate_ui_dump_with_retry(get_ui_data, max_retries=1)

                if not validation.is_valid:
                    logger.warning(
                        f"Step {self._current_step_number}: UI dump invalid "
                        f"({validation.error}, elements={validation.element_count}). "
                        f"Skipping DECIDE/EXECUTE."
                    )
                    skip_reason = StepSkipReason.INVALID_UI_DUMP
                # If ui_data is None, proceed without validation —
                # The agent may not have state_provider in all execution paths

            except Exception as e:
                logger.warning(f"Step {self._current_step_number}: UI dump validation error: {e}")

        # --- Execute phase transitions ---
        try:
            if skip_reason is not None:
                # Skip DECIDE/EXECUTE — go CAPTURE -> CHECKPOINT with skip metadata
                metadata = json.dumps(
                    {
                        "skip_reason": skip_reason.value,
                        "package": getattr(self._current_device_context, "package", ""),
                        "activity": getattr(self._current_device_context, "activity", ""),
                    }
                )

                logger.info(f"Step {self._current_step_number}: skipping DECIDE/EXECUTE " f"due to {skip_reason.value}")

                # CAPTURE -> CHECKPOINT (skip DECIDE, EXECUTE, RECORD)
                self._step_phase_machine.transition_to(StepPhase.CHECKPOINT)

                # Record skip metadata on the transition
                transition = StepPhaseTransition(
                    id=None,
                    run_id=self._current_run_id,
                    step_number=self._current_step_number,
                    from_phase=StepPhase.CAPTURE.value,
                    to_phase=StepPhase.CHECKPOINT.value,
                    timestamp=datetime.now(),
                    action_type=None,
                    duration_ms=None,
                    metadata_json=metadata,
                )
                try:
                    self._step_phase_repository.record_transition(transition)
                except Exception as e:
                    logger.warning(f"Failed to persist skip transition: {e}")

                # CHECKPOINT -> CAPTURE (ready for next step)
                self._step_phase_machine.transition_to(StepPhase.CAPTURE)
            else:
                # Normal flow: CAPTURE -> DECIDE -> EXECUTE -> RECORD -> CHECKPOINT
                # CAPTURE -> DECIDE (AI has decided, now executing)
                self._step_phase_machine.transition_to(StepPhase.DECIDE)

                # DECIDE -> EXECUTE
                self._step_phase_machine.transition_to(StepPhase.EXECUTE)

                # Capture pre-state BEFORE waiting (for post-action verification)
                pre_state = {}
                if self._action_verifier:
                    try:
                        pre_state = await self._action_verifier.capture_pre_state()
                        logger.debug(
                            f"Step {self._current_step_number}: captured pre_state "
                            f"pkg={pre_state.get('package', '?')}"
                        )
                    except Exception as e:
                        logger.warning(f"Step {self._current_step_number}: pre_state capture failed: {e}")

                # Wait for UI to settle after action
                if self._ui_wait_predicate:
                    self._start_sub_phase("after_action_wait")
                    settled = await self._ui_wait_predicate.wait_for_ui_settled(tool_name)
                    self._end_sub_phase(
                        "after_action_wait",
                        metadata_key="after_action_wait_ms",
                        parent_phase=StepPhase.EXECUTE,
                    )
                    if not settled:
                        logger.debug(f"UI did not settle after {tool_name} " f"(step {self._current_step_number})")

                # EXECUTE -> RECORD
                self._step_phase_machine.transition_to(StepPhase.RECORD)

                # Verify post-action state in RECORD phase
                if self._action_verifier and pre_state:
                    try:
                        self._start_sub_phase("verification")
                        verification = await self._action_verifier.verify(pre_state, tool_name)
                        self._end_sub_phase(
                            "verification",
                            metadata_key="verification_ms",
                            parent_phase=StepPhase.RECORD,
                        )
                        logger.info(
                            f"Step {self._current_step_number}: verification "
                            f"result={verification} for action={tool_name}"
                        )
                    except Exception as e:
                        self._end_sub_phase(
                            "verification",
                            metadata_key="verification_ms",
                            parent_phase=StepPhase.RECORD,
                        )
                        logger.warning(f"Step {self._current_step_number}: verification failed: {e}")

                # RECORD -> CHECKPOINT
                self._step_phase_machine.transition_to(StepPhase.CHECKPOINT)

                # CHECKPOINT -> CAPTURE (ready for next step)
                self._step_phase_machine.transition_to(StepPhase.CAPTURE)

        except ValueError as e:
            logger.warning(f"Invalid phase transition at step {self._current_step_number}: {e}")
        except Exception as e:
            logger.warning(f"Phase transition error at step {self._current_step_number}: {e}")

    async def _handle_screenshot_timing_event(self, event) -> None:
        """Handle a ScreenshotEvent carrying capture duration for the Statistics dashboard."""
        duration_ms = getattr(event, "duration_ms", None)
        if duration_ms is None or not self._emit_step_phase_event:
            return
        try:
            self._emit_step_phase_event(
                "on_screenshot_timing", self._current_run_id, self._current_step_number, duration_ms
            )
        except Exception as e:
            logger.warning(f"Failed to emit screenshot timing event: {e}")

    async def _handle_ai_interaction_event(self, event) -> None:
        """Handle AI interaction events (Manager/Executor/FastAgent/AppOpener responses).

        Extracts prompt/response/screenshot from each event, writes screenshot to disk,
        emits AI Monitor signals, and persists to ai_interactions table with real step numbers.
        """
        if not isinstance(
            event, ManagerResponseEvent | ExecutorResponseEvent | FastAgentResponseEvent | AppOpenerResponseEvent
        ):
            return

        # Step number: advance the dedicated AI-call counter once per decide cycle
        # (Manager decision, AppOpener sub-decision, or FastAgent call). Mid-cycle
        # events (Executor response for the same step) reuse the current value so
        # the step's Manager and Executor stay grouped under one number.
        #
        # We deliberately do NOT derive from `self._current_step_number + 1`: that
        # counter only advances in _handle_tool_execution_event, which fires AFTER
        # these response events. If a cycle aborts between the Executor's response
        # and the tool actually running, no ToolExecutionEvent is emitted, the tool
        # counter never advances, and the next cycle would recompute the SAME number.
        # The dedicated counter is self-contained and immune to that (Fix 5).
        if isinstance(event, ManagerResponseEvent | AppOpenerResponseEvent | FastAgentResponseEvent):
            self._ai_call_step_number += 1
        step_number = self._ai_call_step_number

        # Extract common fields
        screenshot_bytes = None
        prompt_text = None
        raw_response = None
        usage = None
        latency_ms = None
        actions = []
        success = True  # Default for events without explicit success field
        error_message = None
        # AppOpener never captures a screenshot (pure text/package-matching call),
        # so vision is never applicable there regardless of any config flag.
        vision_enabled = False
        elements = None
        loop_detected = False
        retry_count = 0
        omniparser_ms = None

        if isinstance(event, ManagerResponseEvent):
            call_type = "manager"
            screenshot_bytes = getattr(event, "screenshot", None)
            system_prompt = getattr(event, "system_prompt", None) or ""
            user_prompt = getattr(event, "user_prompt_text", None) or ""
            prompt_text = f"System:\n{system_prompt}\n\nUser:\n{user_prompt}"
            raw_response = event.response
            usage = event.usage
            latency_ms = getattr(event, "manager_llm_ms", None)
            success = getattr(event, "success", True)
            error_message = getattr(event, "error", None)
            vision_enabled = getattr(event, "vision_enabled", True)
            elements = getattr(event, "elements", None)
            retry_count = len(getattr(event, "validation_retries", None) or [])
            loop_detected = getattr(event, "loop_detected", False)
            omniparser_ms = getattr(event, "omniparser_ms", None)
        elif isinstance(event, ExecutorResponseEvent):
            call_type = "executor"
            screenshot_bytes = getattr(event, "screenshot", None)
            prompt_text = getattr(event, "prompt_text", None)
            raw_response = event.response
            usage = event.usage
            latency_ms = getattr(event, "executor_llm_ms", None)
            success = getattr(event, "success", True)
            error_message = getattr(event, "error", None)
            vision_enabled = getattr(event, "vision_enabled", True)
            elements = getattr(event, "elements", None)
            # Use already-parsed result from event (Fix 8: single parse, not double)
            parsed = event.parsed_action
            if parsed:
                actions = [
                    {
                        "action": parsed.get("action", ""),
                        "reasoning": parsed.get("thought", ""),
                        "description": parsed.get("description", ""),
                    }
                ]
            else:
                actions = []
        elif isinstance(event, FastAgentResponseEvent):
            call_type = "fast_agent"
            screenshot_bytes = getattr(event, "screenshot", None)
            prompt_text = getattr(event, "prompt_text", None)
            raw_response = getattr(event, "raw_response", None) or event.thought
            usage = event.usage
            latency_ms = getattr(event, "fast_agent_llm_ms", None)
            success = getattr(event, "success", True)
            error_message = getattr(event, "error", None)
            vision_enabled = getattr(event, "vision_enabled", True)
            elements = getattr(event, "elements", None)
            retry_count = len(getattr(event, "validation_retries", None) or [])
            omniparser_ms = getattr(event, "omniparser_ms", None)
        elif isinstance(event, AppOpenerResponseEvent):
            call_type = "app_opener"
            prompt_text = event.prompt
            raw_response = event.response
            usage = None
            latency_ms = None
            success = event.success
            error_message = None if success else event.summary

        # Write screenshot to disk once per (run_id, step_number)
        screenshot_path = None
        if screenshot_bytes and self._screenshots_dir:
            screenshot_key = (self._current_run_id, step_number)
            if screenshot_key not in self._screenshot_written:
                os.makedirs(self._screenshots_dir, exist_ok=True)
                screenshot_path = os.path.join(self._screenshots_dir, f"step_{step_number:04d}.png")
                try:
                    with open(screenshot_path, "wb") as f:
                        f.write(screenshot_bytes)
                    self._screenshot_written.add(screenshot_key)
                except Exception as e:
                    logger.warning(f"Failed to write screenshot for step {step_number}: {e}")
                    screenshot_path = None

        # Build request_data matching ai_monitor_panel.py's expected shape
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8") if screenshot_bytes else ""
        config = self._crawler_agent_config
        request_data = {
            "user_prompt": json.dumps({"text": prompt_text or "", "screenshot": screenshot_b64}),
            "ui_elements": elements,
            "vision_enabled": vision_enabled,
            # The screenshot on disk (screenshot_path above) has already had
            # these cropped off at capture time (ADR-0002), but `elements[].bounds`
            # are absolute device coordinates (needed for tapping) — overlay
            # renderers need these to translate bounds back into the cropped
            # image's coordinate space before drawing. See CONTEXT.md.
            "status_bar_exclusion_px": config.status_bar_exclusion_px if config else 0,
            "bottom_bar_exclusion_px": config.bottom_bar_exclusion_px if config else 0,
        }

        # Build response_data
        tokens_input = usage.request_tokens if usage else None
        tokens_output = usage.response_tokens if usage else None
        response_data = {
            "response": raw_response or "",
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "latency_ms": latency_ms,
            "actions": actions,
            "success": success,
            "error_message": error_message,
            "vision_enabled": vision_enabled,
            "call_type": call_type,
            "retry_count": retry_count,
            "loop_detected": loop_detected,
        }

        # Emit signals to UI (on_ai_request_sent, on_ai_response_received, on_screenshot_captured)
        if self._emit_step_phase_event:
            try:
                self._emit_step_phase_event("on_ai_request_sent", self._current_run_id, step_number, request_data)
                # Also emit token counts directly in response_data for stats tracking fallback
                # (in case OTel span processor isn't active)
                response_data_with_tokens = {
                    **response_data,
                    "tokens_input": tokens_input,
                    "tokens_output": tokens_output,
                }
                self._emit_step_phase_event(
                    "on_ai_response_received", self._current_run_id, step_number, response_data_with_tokens
                )
                if screenshot_path:
                    self._emit_step_phase_event(
                        "on_screenshot_captured", self._current_run_id, step_number, screenshot_path
                    )
                if omniparser_ms is not None:
                    self._emit_step_phase_event(
                        "on_omniparser_timing",
                        self._current_run_id,
                        step_number,
                        omniparser_ms,
                        len(elements) if elements else 0,
                    )
            except Exception as e:
                logger.warning(f"Failed to emit AI interaction events: {e}")

        # Persist to ai_interactions table
        if self.ai_interaction_repository:
            try:
                interaction = AIInteraction(
                    id=None,
                    run_id=self._current_run_id,
                    step_number=step_number,
                    timestamp=datetime.now(),
                    request_json=json.dumps(request_data),
                    screenshot_path=screenshot_path,
                    response_raw=raw_response,
                    response_parsed_json=json.dumps({"actions": actions}) if actions else None,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    latency_ms=latency_ms,
                    success=success,
                    error_message=error_message,
                    retry_count=retry_count,
                )
                self.ai_interaction_repository.create_ai_interaction(interaction)
            except Exception as e:
                logger.warning(f"Failed to persist AI interaction for step {step_number}: {e}")

    def _build_auth_session(self, app_package: str) -> AuthenticationSession:
        from mobile_crawler.infrastructure.adb_client import ADBClient
        from mobile_crawler.infrastructure.app_account_store import AppAccountStore
        from mobile_crawler.infrastructure.sms_reader import SmsReader
        from mobile_crawler.infrastructure.verification_inbox import VerificationInboxReader, VerificationInboxStore

        user_store = self.config_manager.user_config_store
        inbox_config = VerificationInboxStore(user_store).get()
        inbox_reader = (
            VerificationInboxReader(inbox_config.address, inbox_config.app_password)
            if inbox_config and inbox_config.app_password
            else None
        )
        return AuthenticationSession(
            app_package=app_package,
            device_id=self.device_id,
            account_store=AppAccountStore(user_store),
            inbox_config=inbox_config,
            inbox_reader=inbox_reader,
            sms_reader=SmsReader(ADBClient()),
            human_fallback=HumanFallback(HumanFallbackConfig.from_store(user_store), self.human_prompter),
        )

    async def _detect_device_phone(self) -> None:
        """Best-effort: remember the device SIM's number for form fills when none is set manually."""
        self.config_manager.set("detected_phone", "")
        if self.config_manager.get("test_phone", "") or not self.device_id:
            return
        try:
            from mobile_crawler.infrastructure.adb_client import ADBClient
            from mobile_crawler.infrastructure.sms_reader import SmsReader

            number = await SmsReader(ADBClient()).read_own_number(self.device_id)
        except Exception as e:
            logger.debug("Could not detect device phone number: %s", e)
            return
        if number:
            logger.info("Detected device phone number for form fills")
            self.config_manager.set("detected_phone", number)

    def _build_auth_section(self, app_package: str) -> str:
        """Create this run's authentication session and return its goal text ('' if unavailable)."""
        try:
            self._auth_session = self._build_auth_session(app_package)
            return self._auth_session.goal_section()
        except Exception as e:
            self._auth_session = None
            logger.warning("Authentication scenario unavailable: %s", e)
            return ""

    def _create_exploration_goal(
        self, app_package: str, max_steps: int, exploration_objective: str | None = None
    ) -> CrawlerGoal:
        """Create a goal for app exploration.

        Args:
            app_package: Target app package name
            max_steps: Maximum steps to execute
            exploration_objective: Optional specific exploration objective

        Returns:
            CrawlerGoal for app exploration
        """
        guided = self.config_manager.get(guided_scenarios_config_key(app_package), [])
        auth_section = self._build_auth_section(app_package)
        if guided and isinstance(guided, list):
            description = (
                f"Explore the {app_package} app. "
                "You MUST follow these Guided Subgoals in order before starting general exploration:\n"
            )
            for i, step in enumerate(guided, 1):
                description += f"Subgoal {i}: {step}\n"

            if exploration_objective:
                description += f"\nAfter completing the guided subgoals, focus on the following objective: {exploration_objective}\n"
            else:
                description += (
                    "\nAfter completing the guided subgoals, continue exploring the app to discover other features.\n"
                )
        else:
            if exploration_objective:
                description = f"Explore the {app_package} app. {exploration_objective}"
            else:
                description = (
                    f"Explore the {app_package} app systematically. "
                    f"Navigate through different screens, interact with UI elements, "
                    f"and discover the app's functionality. Focus on user flows like "
                    f"registration, login, main features, and settings."
                )

        if auth_section:
            description += "\n\nFIRST GUIDED SCENARIO - " + auth_section

        description += "\n\nLOGIN AND FORM DATA:\n" + format_login_and_form_data(self.config_manager, app_package)

        # Force continuous exploration by disabling self-termination
        description += (
            "\n\nCRITICAL INSTRUCTION: You are running in continuous exploration mode. "
            "You MUST NEVER use the <request_accomplished> or <answer> tags to end the session early. "
            "Do not stop even if you think you have fully explored the app or completed the objective. "
            "Instead, keep exploring new screens, revisiting areas with different inputs, or checking edge cases. "
            "The system runtime will terminate you automatically when the configured time or step limit is reached."
        )

        # Proactively dismiss blocking dialogs (e.g. Google Play update prompts)
        # that would otherwise stall the crawl. The LLM must clear these before
        # continuing real exploration.
        description += (
            "\n\nBLOCKING DIALOG HANDLING: Many apps show a Google Play update prompt, "
            "'Update App' dialog, rate-the-app popup, onboarding splash, or a "
            "'What's new' modal on startup. If you encounter ANY of these blocking "
            "dialogs, IMMEDIATELY locate and click the dismiss affordance — the 'X' "
            "icon, 'Skip', 'Later', 'Not now', 'No thanks', or 'Close' button — to "
            "dismiss it and continue crawling. Never get stuck on an update/install "
            "screen; never accept an in-place update. Once dismissed, continue "
            "exploring the actual app."
        )

        return CrawlerGoal(
            description=description,
            max_steps=max_steps,
            reasoning=self.config_manager.get("crawler_reasoning_mode", True),
            app_package=app_package,
        )

    async def execute_exploration_task(
        self,
        run_id: int,
        app_package: str,
        max_steps: int = 15,
        exploration_objective: str | None = None,
        max_duration_seconds: int | None = None,
        step_by_step: bool = False,
    ) -> CrawlerRunResult:
        """Execute an app exploration task using internal Crawler agent.

        Args:
            run_id: Crawler run ID for logging
            app_package: Target app package name
            max_steps: Maximum steps to execute
            exploration_objective: Optional specific exploration objective
            max_duration_seconds: Optional maximum duration in seconds
            step_by_step: Whether to pause after each step and wait for advance_step()

        Returns:
            CrawlerRunResult with execution details
        """
        start_time = time.time()
        goal: CrawlerGoal | None = None

        # Store target package for context pre-check (Plan 02)
        self._target_package = app_package

        # Crash recovery settings
        max_crash_retries = 2
        crash_retry_delay = 3.0  # seconds to wait after relaunch

        # Transient UI-parser / network failure recovery settings.
        # Transient errors (e.g. Replicate "closed" connection drops) should
        # NOT relaunch the app — the device and screenshot are fine, only the
        # transport dropped. Give them their own retry budget so they don't
        # burn crash-retry slots. See PLAN-update-prompt-fix.
        max_transient_retries = int(self.config_manager.get("crawler_retry_count", 2) or 2)
        transient_retry_delay = 2.0  # seconds between transient retries

        crash_attempt = 0
        transient_attempt = 0

        while True:
            try:
                await self._ensure_device_awake_before_crawler()
                await self._ensure_target_app_active_before_crawler(app_package)

                # Initialize agent if needed
                await self._initialize_agent(max_steps, target_package=app_package, step_by_step=step_by_step)

                await self._detect_device_phone()

                # Create exploration goal
                goal = self._create_exploration_goal(app_package, max_steps, exploration_objective)

                # Log agent interaction
                self._log_agent_interaction(run_id, goal, None, None)

                # Execute the goal using internal Crawler agent
                logger.info(f"Executing Crawler agent goal: {goal.description[:100]}...")

                from mobile_crawler.domain.crawler_agent.agent.droid.crawler_agent import CrawlerAgent

                self._crawler_agent = CrawlerAgent(
                    goal=goal.description,
                    config=self._crawler_agent_config,
                    custom_tools=self._auth_session.tools() if self._auth_session else None,
                )

                # Instrument LlamaIndex and register stats collector (idempotent).
                # Runs after CrawlerAgent construction so it reuses whatever
                # TracerProvider setup_tracing() (Phoenix/Langfuse) already
                # registered, instead of racing it and winning with a bare,
                # exporter-less provider.
                self._setup_instrumentation()

                # Wire observers to the Crawler agent's state_provider and driver
                self._wire_observers_to_agent()

                result = self._crawler_agent.run()
                try:
                    from workflows.handler import WorkflowHandler
                except Exception:
                    WorkflowHandler = None

                is_timeout = False

                if WorkflowHandler and isinstance(result, WorkflowHandler):
                    self._current_handler = result
                    self._handler_loop = asyncio.get_running_loop()

                    # Consume workflow events for step phase timing and tracking
                    event_consumer_task = None
                    if self._step_phase_machine:
                        workflow_result = result

                        async def _consume_step_events(workflow_result=workflow_result):
                            """Background task: consume agent events and drive step phase metadata."""
                            try:
                                async for event in workflow_result.stream_events():
                                    if isinstance(event, StepPausedEvent):
                                        # Surface the pause to the UI / CrawlerLoop.
                                        # Use the CrawlState enum value string ("paused_step").
                                        if self._emit_state_change:
                                            self._emit_state_change("paused_step")
                                    elif isinstance(event, ToolExecutionEvent):
                                        await self._handle_tool_execution_event(event)
                                    elif isinstance(event, ScreenshotEvent):
                                        await self._handle_screenshot_timing_event(event)
                                    else:
                                        self._buffer_workflow_timing(event)
                                        await self._handle_ai_interaction_event(event)
                            except asyncio.CancelledError:
                                pass
                            except Exception as e:
                                logger.warning(f"Step event consumer error: {e}")

                        event_consumer_task = asyncio.create_task(_consume_step_events())

                    if max_duration_seconds is not None:
                        try:
                            result = await asyncio.wait_for(result, timeout=max_duration_seconds)
                        except TimeoutError:
                            is_timeout = True
                            logger.info(f"Max duration of {max_duration_seconds}s reached. Stopping Crawler agent.")
                            await self._shutdown_active_workflow()
                    else:
                        result = await result

                    # Cancel event consumer when main workflow finishes
                    if event_consumer_task is not None:
                        event_consumer_task.cancel()
                        try:
                            await event_consumer_task
                        except asyncio.CancelledError:
                            pass
                else:
                    if max_duration_seconds is not None:
                        task = asyncio.create_task(result)
                        try:
                            result = await asyncio.wait_for(task, timeout=max_duration_seconds)
                        except TimeoutError:
                            is_timeout = True
                            logger.info(f"Max duration of {max_duration_seconds}s reached. Stopping Crawler agent.")
                            if not task.done():
                                task.cancel()
                                try:
                                    await task
                                except asyncio.CancelledError:
                                    pass
                    else:
                        result = await result

                duration_ms = (time.time() - start_time) * 1000

                # Convert agent result to our format
                success = False
                steps_completed = 0
                error_message = None

                if is_timeout:
                    success = True
                elif hasattr(result, "success"):
                    raw_success = bool(result.success)
                    steps_completed = int(getattr(result, "steps", 0) or 0)
                    reason = str(getattr(result, "reason", ""))

                    # Agent returns success=False when max steps is reached, but this is normal completion.
                    if not raw_success and self._is_max_step_completion_reason(reason):
                        success = True  # Reached max steps is successful completion
                        error_message = None
                    else:
                        success = raw_success
                        error_message = None if success else reason
                elif isinstance(result, dict):
                    success = result.get("success", False)
                    steps_completed = result.get("steps_completed", 0)
                    error_message = result.get("error_message")
                elif isinstance(result, list):
                    success = True
                    steps_completed = len(result)

                # Extract action history from Crawler agent's internal state
                actions_taken = []
                action_outcomes = []
                if hasattr(self._crawler_agent, "shared_state"):
                    shared_state = self._crawler_agent.shared_state
                    if hasattr(shared_state, "action_history"):
                        actions_taken = shared_state.action_history or []
                    if hasattr(shared_state, "action_outcomes"):
                        action_outcomes = shared_state.action_outcomes or []

                if is_timeout and not steps_completed:
                    steps_completed = len(action_outcomes)

                # Count successful vs failed actions
                successful_count = sum(1 for outcome in action_outcomes if outcome is True)
                failed_count = sum(1 for outcome in action_outcomes if outcome is False)

                crawler_result = CrawlerRunResult(
                    success=success,
                    steps_completed=steps_completed,
                    actions_taken=actions_taken,
                    final_state={
                        "successful_actions": successful_count,
                        "failed_actions": failed_count,
                        "total_actions": len(action_outcomes),
                        "completion_reason": reason if "reason" in locals() and reason else None,
                        **self._run_outcome_details(
                            app_package,
                            is_timeout,
                            reason if "reason" in locals() and reason else "",
                        ),
                    },
                    error_message=error_message,
                    total_duration_ms=duration_ms,
                )

                # Log successful interaction (simulate result for timeout)
                log_result = {
                    "success": success,
                    "steps_completed": steps_completed,
                    "actions_taken": actions_taken,
                    "final_state": crawler_result.final_state,
                }
                self._log_agent_interaction(run_id, goal, log_result, None)

                if is_timeout:
                    # Clear error message and override reason
                    error_msg_log = "Duration limit reached"
                    logger.info(
                        f"Crawler agent timed out cleanly: {crawler_result.steps_completed} steps in {duration_ms:.1f}ms"
                    )
                else:
                    logger.info(
                        f"Crawler agent completed: {crawler_result.steps_completed} steps in {duration_ms:.1f}ms"
                    )
                return crawler_result

            except WorkflowCancelledByUser:
                # User pressed Stop. This is a normal, expected outcome (not a crash) -
                # CrawlerLoop already reports it as "Stopped by user" once _cancel_requested
                # is set, so surface it at INFO with whatever progress was made instead of
                # logging a scary traceback and discarding the run's steps/actions.
                duration_ms = (time.time() - start_time) * 1000
                actions_taken = []
                action_outcomes = []
                steps_completed = 0
                if hasattr(self._crawler_agent, "shared_state"):
                    shared_state = self._crawler_agent.shared_state
                    actions_taken = getattr(shared_state, "action_history", None) or []
                    action_outcomes = getattr(shared_state, "action_outcomes", None) or []
                    steps_completed = getattr(shared_state, "step_number", 0) or len(action_outcomes)

                successful_count = sum(1 for outcome in action_outcomes if outcome is True)
                failed_count = sum(1 for outcome in action_outcomes if outcome is False)

                logger.info(f"Crawler agent cancelled by user after {steps_completed} steps in {duration_ms:.1f}ms")
                return CrawlerRunResult(
                    success=True,
                    steps_completed=steps_completed,
                    actions_taken=actions_taken,
                    final_state={
                        "successful_actions": successful_count,
                        "failed_actions": failed_count,
                        "total_actions": len(action_outcomes),
                        "completion_reason": "Cancelled by user",
                        **self._run_outcome_details(app_package, False, ""),
                    },
                    error_message=None,
                    total_duration_ms=duration_ms,
                )
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = str(e)

                # Check if error is a transient UI-parser / network failure.
                # Transient errors are checked BEFORE app-crash detection so
                # that a "closed" / Replicate connection drop is never
                # misclassified as an app crash and never triggers a relaunch.
                is_transient = self._is_transient_network_error(error_msg)

                # Check if error indicates app crash
                is_app_crash = self._is_app_crash_error(error_msg)

                if is_transient and transient_attempt < max_transient_retries:
                    transient_attempt += 1
                    logger.warning(
                        f"Transient UI-parser/network error detected "
                        f"(retry {transient_attempt}/{max_transient_retries}): "
                        f"{error_msg}. Retrying without app relaunch in "
                        f"{transient_retry_delay}s."
                    )
                    await asyncio.sleep(transient_retry_delay)
                    # Reset start_time so duration reflects only the
                    # successful attempt, not the failed attempts.
                    start_time = time.time()
                    continue

                if is_app_crash and crash_attempt < max_crash_retries:
                    crash_attempt += 1
                    logger.warning(f"App crash detected (attempt {crash_attempt}/{max_crash_retries}): {error_msg}")

                    # Attempt to relaunch the app
                    try:
                        from mobile_crawler.domain.adb_action_executor import ADBActionExecutor

                        executor = ADBActionExecutor(device_id=self.device_id)
                        logger.info(f"Attempting to relaunch app: {app_package}")

                        launch_result = executor.launch_app(app_package)

                        if launch_result.success:
                            logger.info(f"App relaunched successfully, waiting {crash_retry_delay}s before retry...")
                            await asyncio.sleep(crash_retry_delay)

                            # Update start_time to exclude relaunch time from total duration
                            start_time = time.time()

                            # Retry the exploration
                            continue
                        else:
                            logger.error(f"Failed to relaunch app: {launch_result.error_message}")
                            # Fall through to error handling below
                    except Exception as relaunch_error:
                        logger.error(f"Error during app relaunch: {relaunch_error}")
                        # Fall through to error handling below

                # Log failed interaction
                if goal is not None:
                    self._log_agent_interaction(run_id, goal, None, error_msg)

                logger.error(f"Crawler agent execution failed: {error_msg}", exc_info=True)
                return CrawlerRunResult(
                    success=False,
                    steps_completed=0,
                    actions_taken=[],
                    final_state={},
                    error_message=error_msg,
                    total_duration_ms=duration_ms,
                )
            finally:
                self._current_handler = None
                self._handler_loop = None

    def _is_app_crash_error(self, error_message: str) -> bool:
        """Check if error message indicates an app crash.

        Args:
            error_message: Error message to check

        Returns:
            True if error appears to be caused by app crash
        """
        crash_indicators = [
            "No active window",
            "root filtered out",
            "Accessibility node info",
            "WindowManager",
            "android.view.WindowLeaked",
        ]

        error_lower = error_message.lower()

        # Bail out early for transient UI-parser / network failures. These
        # must NOT be classified as app crashes because relaunching the app
        # does nothing to fix a dropped Replicate connection — it just wastes
        # a crash-retry slot and masks the real problem. See PLAN-update-prompt-fix.
        if self._is_transient_network_error(error_message):
            return False

        return any(indicator.lower() in error_lower for indicator in crash_indicators)

    # Substrings that indicate a transient UI-parser/network failure rather
    # than an actual device/app crash. When present, the caller should retry
    # the crawl step WITHOUT relaunching the app.
    _TRANSIENT_ERROR_TOKENS = (
        "closed",
        "remoteprotocolerror",
        "server disconnected",
        "server disconnected)",
        "connection closed",
        "connection reset",
        "connection aborted",
        "connectionerror",
        "read timeout",
        "timed out",
        "timeout",
        "temporarily unavailable",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "overloaded",
        "capacity",
        "retry",
        "omniparser replicate error",
        "replicate api error",
        "omniparser",
    )

    def _is_transient_network_error(self, error_message: str) -> bool:
        """Check if an error message looks like a transient UI-parser/network failure.

        Transient failures include:
        - ``httpx.RemoteProtocolError`` raised by the Replicate streaming
          connection (often surfaced as the bare string ``"closed"`` after
          ~30-40s)
        - Replicate/OmniParser-wrapped variants ("OmniParser Replicate error: ...")
        - Generic timeouts and connection resets

        These should trigger a retry of the crawl step WITHOUT relaunching
        the target app, because the device is healthy and the screenshot
        payload is unchanged.

        Args:
            error_message: Error message to check

        Returns:
            True if the error appears transient and retryable.
        """
        if not error_message:
            return False
        error_lower = error_message.lower()
        return any(token in error_lower for token in self._TRANSIENT_ERROR_TOKENS)

    def _run_outcome_details(self, app_package: str, is_timeout: bool, reason: str) -> dict[str, Any]:
        """Stop kind and guided-scenario snapshot recorded on the run for the Run Report."""
        if is_timeout:
            stop_kind = "duration_limit"
        elif self._is_max_step_completion_reason(reason):
            stop_kind = "step_limit"
        else:
            stop_kind = None

        scenarios = self.config_manager.get(guided_scenarios_config_key(app_package), [])
        shared_state = getattr(self._crawler_agent, "shared_state", None)
        guided_progress = build_guided_progress(
            scenarios if isinstance(scenarios, list) else None,
            getattr(shared_state, "plan", None),
            getattr(shared_state, "current_subgoal", None),
        )
        auth_note = self._auth_session.skipped_reason if self._auth_session else None
        if auth_note:
            logger.warning("Run note: %s", auth_note)
        return {"stop_kind": stop_kind, "guided_progress": guided_progress, "auth_note": auth_note}

    @staticmethod
    def _is_max_step_completion_reason(reason: str) -> bool:
        """Return True when the agent ended normally at the configured step limit."""
        normalized = (reason or "").lower()
        return any(
            token in normalized
            for token in (
                "max step",
                "max steps",
                "maximum step",
                "maximum steps",
                "reached max step count",
            )
        )

    def _log_agent_interaction(
        self, run_id: int, goal: CrawlerGoal | None, result: Any | None, error_message: str | None
    ) -> None:
        """Log agent interaction to the database.

        Args:
            run_id: Crawler run ID
            goal: The goal that was executed
            result: Agent execution result (if successful)
            error_message: Error message (if failed)
        """
        if not self.ai_interaction_repository:
            return

        try:
            # Create request data
            request_data = None
            if goal is not None:
                request_data = {
                    "goal_description": goal.description,
                    "max_steps": goal.max_steps,
                    "reasoning_mode": goal.reasoning,
                    "app_package": goal.app_package,
                }

            # Create response data
            response_data = None
            if result:
                result = self._normalize_agent_result_for_logging(result)
                response_data = {
                    "success": result.get("success", False),
                    "steps_completed": result.get("steps_completed", 0),
                    "actions_taken": result.get("actions_taken", []),
                    "final_state": result.get("final_state", {}),
                }

            # Create AI interaction record
            interaction = AIInteraction(
                id=None,
                run_id=run_id,
                step_number=1,  # The agent handles multiple steps internally
                timestamp=datetime.now(),
                request_json=json.dumps(request_data) if request_data else None,
                screenshot_path=None,  # The agent handles screenshots internally
                response_raw=json.dumps(response_data) if response_data else None,
                response_parsed_json=json.dumps(response_data) if response_data else None,
                tokens_input=None,  # Token counting handled internally
                tokens_output=None,
                latency_ms=None,  # Will be calculated by calling code
                success=error_message is None,
                error_message=error_message,
                retry_count=0,
            )

            self.ai_interaction_repository.create_ai_interaction(interaction)

        except Exception as e:
            logger.warning(f"Failed to log agent interaction: {e}")

    @staticmethod
    def _normalize_agent_result_for_logging(result: Any) -> dict[str, Any]:
        """Return a dict-shaped result for database logging."""
        if isinstance(result, dict):
            return result

        if isinstance(result, list):
            return {
                "success": True,
                "steps_completed": len(result),
                "actions_taken": result,
                "final_state": {"raw_result_type": "list"},
            }

        if hasattr(result, "success"):
            return {
                "success": bool(getattr(result, "success", False)),
                "steps_completed": int(getattr(result, "steps", 0) or 0),
                "actions_taken": [],
                "final_state": {
                    "completion_reason": getattr(result, "reason", None),
                    "raw_result_type": type(result).__name__,
                },
            }

        return {
            "success": False,
            "steps_completed": 0,
            "actions_taken": [],
            "final_state": {
                "raw_result": str(result),
                "raw_result_type": type(result).__name__,
            },
        }

    def convert_agent_actions_to_crawler_format(self, agent_actions: list[dict[str, Any]]) -> list[AIAction]:
        """Convert agent actions to crawler AIAction format.

        Args:
            agent_actions: List of actions from the agent

        Returns:
            List of AIAction objects
        """
        converted_actions = []

        for action_data in agent_actions:
            try:
                # Extract action details
                action_type = action_data.get("action", "unknown")
                description = action_data.get("description", "")
                coordinates = action_data.get("coordinates")
                text = action_data.get("text")

                # Create bounding box if coordinates available
                bounding_box = None
                if coordinates and len(coordinates) >= 2:
                    x, y = coordinates[:2]
                    # Create a small bounding box around the point
                    bounding_box = BoundingBox(top_left=(max(0, x - 10), max(0, y - 10)), bottom_right=(x + 10, y + 10))

                # Map agent action types to crawler action types
                action_mapping = {
                    "click": "click",
                    "tap": "click",
                    "type": "input",
                    "swipe": "scroll_down",  # Simplified mapping
                    "scroll": "scroll_down",
                    "back": "back",
                }

                mapped_action = action_mapping.get(action_type, "click")

                # Create AIAction
                ai_action = AIAction(
                    action=mapped_action,
                    action_desc=description or f"Agent {action_type}",
                    target_bounding_box=bounding_box,
                    input_text=text,
                    reasoning=action_data.get("reasoning", ""),
                )

                converted_actions.append(ai_action)

            except Exception as e:
                logger.warning(f"Failed to convert agent action {action_data}: {e}")
                continue

        return converted_actions

    async def cleanup(self) -> None:
        """Cleanup agent resources."""
        await self._shutdown_active_workflow()
        if self._crawler_agent:
            try:
                # Close LLM clients to ensure AsyncClient.aclose() is called
                await self._close_llm_clients()
            except Exception as e:
                logger.warning(f"Error closing LLM clients: {e}")
            try:
                # Null out sub-agent references so GC can collect google.genai objects
                for attr in (
                    "manager_agent",
                    "executor_agent",
                    "action_ctx",
                    "state_provider",
                    "registry",
                    "mcp_manager",
                ):
                    if hasattr(self._crawler_agent, attr):
                        setattr(self._crawler_agent, attr, None)
            except Exception:
                pass
        self._crawler_agent = None
        self._is_initialized = False

    async def _close_llm_clients(self) -> None:
        """Explicitly close google.genai.Client instances to prevent pending tasks."""
        if not self._crawler_agent:
            return

        # Google GenAI clients are stored in the agent's LLM instances
        llm_attributes = ["manager_llm", "executor_llm", "fast_agent_llm", "app_opener_llm", "structured_output_llm"]

        closed_ids = set()  # Track by id() since some LLMs share the same object
        for attr in llm_attributes:
            llm = getattr(self._crawler_agent, attr, None)
            if llm is None or id(llm) in closed_ids:
                continue

            # Close the underlying google.genai client if it's a GoogleGenAI LLM
            if llm.__class__.__name__ == "GoogleGenAI":
                await self._close_google_genai_client(llm, attr)
                closed_ids.add(id(llm))

            # Null out LLM reference so GC can collect the google.genai.Client
            setattr(self._crawler_agent, attr, None)

    async def _close_google_genai_client(self, llm, attr_name: str) -> None:
        """Close a google.genai.Client instance from a llama-index GoogleGenAI LLM.

        The google.genai.Client has both sync and async cleanup:
        - client.close() is SYNCHRONOUS (returns None)
        - client.aio.aclose() is ASYNCHRONOUS (must be awaited)

        We must close the async client first, then the sync client.
        """
        try:
            # Access the internal google.genai.Client
            if hasattr(llm, "_client"):
                client = llm._client

                # First, close the async client (this is what has pending tasks)
                if hasattr(client, "aio"):
                    async_client = client.aio
                    if hasattr(async_client, "aclose"):
                        await async_client.aclose()
                        logger.debug(f"Closed google.genai.AsyncClient for {attr_name}")
                        return  # Skip calling the sync close method which creates orphaned coroutines

                # Then, close the sync client (this is synchronous, no await needed)
                if hasattr(client, "close"):
                    client.close()  # This is sync, do NOT await
                    logger.debug(f"Closed google.genai.Client for {attr_name}")

        except Exception as e:
            logger.warning(f"Failed to close client for {attr_name}: {e}")

    async def _shutdown_active_workflow(self) -> None:
        handler = self._current_handler
        if not handler:
            return

        try:
            if not handler.done():
                await handler.cancel_run()
                try:
                    await asyncio.wait_for(handler, timeout=5)
                except TimeoutError:
                    logger.warning("Timed out waiting for agent workflow to finish")
                except asyncio.CancelledError:
                    # Ignore cancellation error that is expected when waiting for a cancelled task
                    pass
            if handler.ctx and handler.ctx.is_running:
                await handler.ctx.shutdown()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"Error while shutting down agent workflow: {e}")
        finally:
            self._current_handler = None
            self._handler_loop = None

    def request_cancel(self) -> bool:
        """Request cancellation of the active agent workflow if available."""
        handler = self._current_handler
        loop = self._handler_loop
        if not handler or not loop:
            return False

        if loop.is_running():
            loop.call_soon_threadsafe(lambda: asyncio.create_task(handler.cancel_run()))
            return True

        return False

    def advance_step(self) -> bool:
        """Send a StepAdvanceEvent to the running agent workflow from a non-async caller (thread-safe).

        Returns True if the event was dispatched; False if no active handler exists.
        """
        handler = self._current_handler
        loop = self._handler_loop
        if not handler or not loop:
            return False

        def _send() -> None:
            try:
                handler.ctx.send_event(StepAdvanceEvent())
            except Exception as exc:
                logger.warning("Failed to send StepAdvanceEvent: %s", exc)

        if loop.is_running():
            loop.call_soon_threadsafe(_send)
            return True

        return False

    # ------------------------------------------------------------------

    async def analyze_ui_context(self, agent_tools, phone_state: dict[str, Any]) -> dict[str, Any]:
        """Analyze UI context using OmniParser fallback.

        This method can be called after agent execution to log
        OmniParser analysis for debugging/monitoring purposes.

        Args:
            agent_tools: Agent tools instance
            phone_state: Current phone state

        Returns:
            Dict with analysis results or empty dict if unavailable
        """
        if not self._ui_context_manager or not self._omni_parser_client:
            return {}

        try:
            context = await self._ui_context_manager.get_context(agent_tools, phone_state)
            logger.info(
                f"UI Context Analysis: source={context.get('source')}, "
                f"a11y_count={len(context.get('a11y', []))}, "
                f"omni_count={len(context.get('omni', []))}, "
                f"issues={context.get('issues', [])}"
            )
            return context
        except Exception as e:
            logger.warning(f"UI context analysis failed: {e}")
            return {}

    def get_omni_parser_stats(self) -> dict[str, Any]:
        """Get OmniParser usage statistics.

        Returns:
            Dict with backend, availability, etc.
        """
        if not self._omni_parser_client:
            return {"available": False}

        return {
            "available": True,
            "backend": self._omni_parser_client.backend.value,
            "local_available": self._omni_parser_client.check_local_available(),
        }
