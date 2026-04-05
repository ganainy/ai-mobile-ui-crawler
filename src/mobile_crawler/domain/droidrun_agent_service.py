"""DroidRun agent service integration for mobile crawler."""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.domain.models import ActionResult, AIResponse, AIAction, BoundingBox
from mobile_crawler.infrastructure.ai_interaction_repository import AIInteraction, AIInteractionRepository

logger = logging.getLogger(__name__)


class DroidRunLogHandler(logging.Handler):
    """Forward DroidRun logs to UI and JSONL file per run."""

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
                self.emit_debug(self.run_id, 0, message)
        except Exception:
            # Avoid log recursion on failures
            pass


@dataclass
class DroidRunGoal:
    """Goal representation for DroidRun agent."""
    description: str
    max_steps: int = 15
    reasoning: bool = True
    app_package: Optional[str] = None


@dataclass
class DroidRunResult:
    """Result from DroidRun agent execution."""
    success: bool
    steps_completed: int
    actions_taken: List[Dict[str, Any]]
    final_state: Dict[str, Any]
    error_message: Optional[str] = None
    total_duration_ms: float = 0.0


class DroidRunAgentService:
    """Service for integrating DroidRun AI agents with the mobile crawler."""

    def __init__(
        self,
        config_manager: ConfigManager,
        ai_interaction_repository: Optional[AIInteractionRepository],
        device_id: str
    ):
        """Initialize DroidRun agent service.

        Args:
            config_manager: Configuration manager for crawler settings
            ai_interaction_repository: Repository for logging AI interactions
            device_id: ADB device identifier
        """
        self.config_manager = config_manager
        self.ai_interaction_repository = ai_interaction_repository
        self.device_id = device_id
        self._droid_agent = None
        self._droidrun_config = None
        self._current_handler = None
        self._handler_loop = None
        self._log_handler = None
        self._is_initialized = False

    def _get_droidrun_config(self) -> Dict[str, Any]:
        """Convert crawler configuration to DroidRun format.

        Returns:
            DroidRun configuration dictionary
        """
        # Get LLM configuration from crawler config
        ai_provider = self.config_manager.get('ai_provider', 'gemini')
        ai_model = self.config_manager.get('ai_model', 'gemini-1.5-flash')

        # Map crawler providers to DroidRun format
        provider_mapping = {
            'gemini': 'GoogleGenAI',
            'openai': 'OpenAI',
            'anthropic': 'AnthropicAI',
            'ollama': 'Ollama'
        }

        droid_provider = provider_mapping.get(ai_provider, 'GoogleGenAI')

        def resolve_api_key(primary_key: str, env_keys: List[str]) -> Optional[str]:
            key_value = self.config_manager.get(primary_key)
            if not key_value:
                try:
                    key_value = self.config_manager.user_config_store.get_secret_plaintext(primary_key)
                except Exception:
                    key_value = None
            if not key_value:
                for env_key in env_keys:
                    key_value = os.environ.get(env_key)
                    if key_value:
                        break
            return key_value

        config = {
            'agent': {
                'max_steps': self.config_manager.get('max_crawl_steps', 15),
                'reasoning': self.config_manager.get('droidrun_reasoning_mode', True),
                'streaming': self.config_manager.get('droidrun_streaming', False),
            },
            'device': {
                'platform': 'android',
                'serial': self.device_id,
                'auto_setup': False  # We handle device setup separately
            },
            'llm_profiles': {
                'manager': {
                    'provider': droid_provider,
                    'model': ai_model,
                    'temperature': 0.1,
                    'kwargs': {}
                },
                'executor': {
                    'provider': droid_provider,
                    'model': ai_model,
                    'temperature': 0.0,
                    'kwargs': {}
                },
                'fast_agent': {
                    'provider': droid_provider,
                    'model': ai_model,
                    'temperature': 0.0,
                    'kwargs': {}
                },
                'app_opener': {
                    'provider': droid_provider,
                    'model': ai_model,
                    'temperature': 0.0,
                    'kwargs': {}
                },
                'structured_output': {
                    'provider': droid_provider,
                    'model': ai_model,
                    'temperature': 0.0,
                    'kwargs': {}
                }
            },
            'telemetry': {
                'enabled': self.config_manager.get('droidrun_telemetry_enabled', False)
            }
        }

        # Add API keys based on provider
        if ai_provider == 'gemini':
            api_key = resolve_api_key('gemini_api_key', ['GEMINI_API_KEY', 'GOOGLE_API_KEY'])
            if api_key:
                config['llm_profiles']['manager']['kwargs']['api_key'] = api_key
                config['llm_profiles']['executor']['kwargs']['api_key'] = api_key
                config['llm_profiles']['fast_agent']['kwargs']['api_key'] = api_key
                config['llm_profiles']['app_opener']['kwargs']['api_key'] = api_key
                config['llm_profiles']['structured_output']['kwargs']['api_key'] = api_key
                os.environ['GEMINI_API_KEY'] = api_key
                os.environ['GOOGLE_API_KEY'] = api_key
        elif ai_provider == 'openai':
            api_key = resolve_api_key('openai_api_key', ['OPENAI_API_KEY'])
            if api_key:
                config['llm_profiles']['manager']['kwargs']['api_key'] = api_key
                config['llm_profiles']['executor']['kwargs']['api_key'] = api_key
                config['llm_profiles']['fast_agent']['kwargs']['api_key'] = api_key
                config['llm_profiles']['app_opener']['kwargs']['api_key'] = api_key
                config['llm_profiles']['structured_output']['kwargs']['api_key'] = api_key
                os.environ['OPENAI_API_KEY'] = api_key
        elif ai_provider == 'anthropic':
            api_key = resolve_api_key('anthropic_api_key', ['ANTHROPIC_API_KEY'])
            if api_key:
                config['llm_profiles']['manager']['kwargs']['api_key'] = api_key
                config['llm_profiles']['executor']['kwargs']['api_key'] = api_key
                config['llm_profiles']['fast_agent']['kwargs']['api_key'] = api_key
                config['llm_profiles']['app_opener']['kwargs']['api_key'] = api_key
                config['llm_profiles']['structured_output']['kwargs']['api_key'] = api_key
                os.environ['ANTHROPIC_API_KEY'] = api_key

        return config

    def configure_run_logging(self, run_id: int, log_dir: str, emit_debug, enable_ui: bool) -> None:
        """Attach a DroidRun log handler for UI/debug and JSONL output.

        Always enables UI forwarding so logs reach both the JSONL file
        and the root QLogHandler bridge in MainWindow.
        """
        log_path = os.path.join(log_dir, "droidrun_trace.jsonl")
        handler = DroidRunLogHandler(run_id, log_path, emit_debug, True)
        handler.setLevel(logging.DEBUG)

        # Patch the droidrun logger and known children to ensure propagation
        for name in ["droidrun", "droidrun.agent", "droidrun.tools", "droidrun.config_manager"]:
            lg = logging.getLogger(name)
            lg.propagate = True
            lg.setLevel(logging.DEBUG)

        droid_logger = logging.getLogger("droidrun")
        droid_logger.addHandler(handler)
        self._log_handler = handler

    def clear_run_logging(self) -> None:
        """Detach DroidRun log handler if attached."""
        if self._log_handler:
            droid_logger = logging.getLogger("droidrun")
            droid_logger.removeHandler(self._log_handler)
            self._log_handler = None

    async def _initialize_agent(self) -> None:
        """Initialize DroidRun agent with current configuration."""
        if self._is_initialized:
            return

        try:
            self._ensure_droidrun_import()
            # Import DroidRun components
            from droidrun.config_manager.config_manager import DroidConfig

            # Create DroidRun configuration
            config_dict = self._get_droidrun_config()
            self._droidrun_config = DroidConfig.from_dict(config_dict)

            self._is_initialized = True
            logger.info("DroidRun agent initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize DroidRun agent: {e}")
            raise

    def _create_exploration_goal(
        self,
        app_package: str,
        max_steps: int,
        exploration_objective: Optional[str] = None
    ) -> DroidRunGoal:
        """Create a goal for app exploration.

        Args:
            app_package: Target app package name
            max_steps: Maximum steps to execute
            exploration_objective: Optional specific exploration objective

        Returns:
            DroidRunGoal for app exploration
        """
        if exploration_objective:
            description = f"Explore the {app_package} app. {exploration_objective}"
        else:
            description = (
                f"Explore the {app_package} app systematically. "
                f"Navigate through different screens, interact with UI elements, "
                f"and discover the app's functionality. Focus on user flows like "
                f"registration, login, main features, and settings."
            )

        return DroidRunGoal(
            description=description,
            max_steps=max_steps,
            reasoning=self.config_manager.get('droidrun_reasoning_mode', True),
            app_package=app_package
        )

    async def execute_exploration_task(
        self,
        run_id: int,
        app_package: str,
        max_steps: int = 15,
        exploration_objective: Optional[str] = None
    ) -> DroidRunResult:
        """Execute an app exploration task using DroidRun agent.

        Args:
            run_id: Crawler run ID for logging
            app_package: Target app package name
            max_steps: Maximum steps to execute
            exploration_objective: Optional specific exploration objective

        Returns:
            DroidRunResult with execution details
        """
        start_time = time.time()
        goal: Optional[DroidRunGoal] = None

        # Crash recovery settings
        max_crash_retries = 2
        crash_retry_delay = 3.0  # seconds to wait after relaunch

        for attempt in range(max_crash_retries + 1):
            try:
                # Initialize agent if needed
                await self._initialize_agent()

                # Create exploration goal
                goal = self._create_exploration_goal(app_package, max_steps, exploration_objective)

                # Log agent request
                self._log_agent_interaction(run_id, goal, None, None)

                # Execute the goal using DroidRun agent
                logger.info(f"Executing DroidRun agent goal: {goal.description[:100]}...")

                from droidrun.agent.droid.droid_agent import DroidAgent

                self._droid_agent = DroidAgent(
                    goal=goal.description,
                    config=self._droidrun_config
                )

                result = self._droid_agent.run()
                try:
                    from workflows.handler import WorkflowHandler
                except Exception:
                    WorkflowHandler = None

                if WorkflowHandler and isinstance(result, WorkflowHandler):
                    self._current_handler = result
                    self._handler_loop = asyncio.get_running_loop()
                    result = await result
                else:
                    result = await result

                duration_ms = (time.time() - start_time) * 1000

                # Convert DroidRun result to our format
                success = False
                steps_completed = 0
                error_message = None
                if hasattr(result, "success"):
                    raw_success = bool(getattr(result, "success"))
                    steps_completed = int(getattr(result, "steps", 0) or 0)
                    reason = str(getattr(result, "reason", ""))

                    # DroidRun returns success=False when max steps is reached, but this is normal completion
                    # Treat "reached max steps" as successful completion, not an error
                    if not raw_success and reason and "maximum" in reason.lower():
                        success = True  # Reached max steps is successful completion
                        error_message = None
                    else:
                        success = raw_success
                        error_message = None if success else reason
                elif isinstance(result, dict):
                    success = result.get("success", False)
                    steps_completed = result.get("steps_completed", 0)
                    error_message = result.get("error_message")

                # Extract action history from DroidRun agent's internal state
                actions_taken = []
                action_outcomes = []
                if hasattr(self._droid_agent, 'shared_state'):
                    shared_state = self._droid_agent.shared_state
                    if hasattr(shared_state, 'action_history'):
                        actions_taken = shared_state.action_history or []
                    if hasattr(shared_state, 'action_outcomes'):
                        action_outcomes = shared_state.action_outcomes or []

                # Count successful vs failed actions
                successful_count = sum(1 for outcome in action_outcomes if outcome is True)
                failed_count = sum(1 for outcome in action_outcomes if outcome is False)

                droid_result = DroidRunResult(
                    success=success,
                    steps_completed=steps_completed,
                    actions_taken=actions_taken,
                    final_state={
                        'successful_actions': successful_count,
                        'failed_actions': failed_count,
                        'total_actions': len(action_outcomes)
                    },
                    error_message=error_message,
                    total_duration_ms=duration_ms
                )

                # Log successful interaction
                self._log_agent_interaction(run_id, goal, result, None)

                logger.info(f"DroidRun agent completed: {droid_result.steps_completed} steps in {duration_ms:.1f}ms")
                return droid_result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = str(e)

                # Check if error indicates app crash
                is_app_crash = self._is_app_crash_error(error_msg)

                if is_app_crash and attempt < max_crash_retries:
                    logger.warning(
                        f"App crash detected (attempt {attempt + 1}/{max_crash_retries}): {error_msg}"
                    )

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

                logger.error(f"DroidRun agent execution failed: {error_msg}")
                return DroidRunResult(
                    success=False,
                    steps_completed=0,
                    actions_taken=[],
                    final_state={},
                    error_message=error_msg,
                    total_duration_ms=duration_ms
                )
            finally:
                self._current_handler = None
                self._handler_loop = None

        # Should not reach here, but handle the case
        return DroidRunResult(
            success=False,
            steps_completed=0,
            actions_taken=[],
            final_state={},
            error_message="Max crash retries exceeded",
            total_duration_ms=(time.time() - start_time) * 1000
        )

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
            "android.view.WindowLeaked"
        ]

        error_lower = error_message.lower()
        return any(indicator.lower() in error_lower for indicator in crash_indicators)

    def _log_agent_interaction(
        self,
        run_id: int,
        goal: Optional[DroidRunGoal],
        result: Optional[Dict[str, Any]],
        error_message: Optional[str]
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
                    "app_package": goal.app_package
                }

            # Create response data
            response_data = None
            if result:
                response_data = {
                    "success": result.get('success', False),
                    "steps_completed": result.get('steps_completed', 0),
                    "actions_taken": result.get('actions_taken', []),
                    "final_state": result.get('final_state', {})
                }

            # Create AI interaction record
            interaction = AIInteraction(
                id=None,
                run_id=run_id,
                step_number=1,  # DroidRun handles multiple steps internally
                timestamp=datetime.now(),
                request_json=json.dumps(request_data) if request_data else None,
                screenshot_path=None,  # DroidRun handles screenshots internally
                response_raw=json.dumps(response_data) if response_data else None,
                response_parsed_json=json.dumps(response_data) if response_data else None,
                tokens_input=None,  # Token counting handled by DroidRun
                tokens_output=None,
                latency_ms=None,  # Will be calculated by calling code
                success=error_message is None,
                error_message=error_message,
                retry_count=0
            )

            self.ai_interaction_repository.create_ai_interaction(interaction)

        except Exception as e:
            logger.warning(f"Failed to log agent interaction: {e}")

    def _ensure_droidrun_import(self) -> None:
        """Ensure the DroidRun submodule is importable without pip install."""
        repo_root = Path(__file__).resolve().parents[3]
        droidrun_root = repo_root / "external" / "droidrun"
        if droidrun_root.exists() and str(droidrun_root) not in sys.path:
            sys.path.insert(0, str(droidrun_root))

    def convert_droidrun_actions_to_crawler_format(
        self,
        droidrun_actions: List[Dict[str, Any]]
    ) -> List[AIAction]:
        """Convert DroidRun actions to crawler AIAction format.

        Args:
            droidrun_actions: List of actions from DroidRun

        Returns:
            List of AIAction objects
        """
        converted_actions = []

        for action_data in droidrun_actions:
            try:
                # Extract action details
                action_type = action_data.get('action', 'unknown')
                description = action_data.get('description', '')
                coordinates = action_data.get('coordinates')
                text = action_data.get('text')

                # Create bounding box if coordinates available
                bounding_box = None
                if coordinates and len(coordinates) >= 2:
                    x, y = coordinates[:2]
                    # Create a small bounding box around the point
                    bounding_box = BoundingBox(
                        top_left=(max(0, x-10), max(0, y-10)),
                        bottom_right=(x+10, y+10)
                    )

                # Map DroidRun action types to crawler action types
                action_mapping = {
                    'click': 'click',
                    'tap': 'click',
                    'type': 'input',
                    'swipe': 'scroll_down',  # Simplified mapping
                    'scroll': 'scroll_down',
                    'back': 'back'
                }

                mapped_action = action_mapping.get(action_type, 'click')

                # Create AIAction
                ai_action = AIAction(
                    action=mapped_action,
                    action_desc=description or f"DroidRun {action_type}",
                    target_bounding_box=bounding_box,
                    input_text=text,
                    reasoning=action_data.get('reasoning', '')
                )

                converted_actions.append(ai_action)

            except Exception as e:
                logger.warning(f"Failed to convert DroidRun action {action_data}: {e}")
                continue

        return converted_actions

    async def cleanup(self) -> None:
        """Cleanup DroidRun agent resources."""
        await self._shutdown_active_workflow()
        if self._droid_agent:
            try:
                # Close LLM clients to ensure AsyncClient.aclose() is called
                await self._close_llm_clients()
            except Exception as e:
                logger.warning(f"Error closing LLM clients: {e}")
            try:
                # Null out sub-agent references so GC can collect google.genai objects
                for attr in ('manager_agent', 'executor_agent', 'action_ctx',
                             'state_provider', 'registry', 'mcp_manager'):
                    if hasattr(self._droid_agent, attr):
                        setattr(self._droid_agent, attr, None)
            except Exception:
                pass
        self._droid_agent = None
        self._is_initialized = False

    async def _close_llm_clients(self) -> None:
        """Explicitly close google.genai.Client instances to prevent pending tasks."""
        if not self._droid_agent:
            return

        # Google GenAI clients are stored in the agent's LLM instances
        llm_attributes = [
            'manager_llm', 'executor_llm', 'fast_agent_llm',
            'app_opener_llm', 'structured_output_llm'
        ]

        closed_ids = set()  # Track by id() since some LLMs share the same object
        for attr in llm_attributes:
            llm = getattr(self._droid_agent, attr, None)
            if llm is None or id(llm) in closed_ids:
                continue

            # Close the underlying google.genai client if it's a GoogleGenAI LLM
            if llm.__class__.__name__ == 'GoogleGenAI':
                await self._close_google_genai_client(llm, attr)
                closed_ids.add(id(llm))

            # Null out LLM reference so GC can collect the google.genai.Client
            setattr(self._droid_agent, attr, None)

    async def _close_google_genai_client(self, llm, attr_name: str) -> None:
        """Close a google.genai.Client instance from a llama-index GoogleGenAI LLM.

        The google.genai.Client has both sync and async cleanup:
        - client.close() is SYNCHRONOUS (returns None)
        - client.aio.aclose() is ASYNCHRONOUS (must be awaited)

        We must close the async client first, then the sync client.
        """
        try:
            # Access the internal google.genai.Client
            if hasattr(llm, '_client'):
                client = llm._client

                # First, close the async client (this is what has pending tasks)
                if hasattr(client, 'aio'):
                    async_client = client.aio
                    if hasattr(async_client, 'aclose'):
                        await async_client.aclose()
                        logger.debug(f"Closed google.genai.AsyncClient for {attr_name}")

                # Then, close the sync client (this is synchronous, no await needed)
                if hasattr(client, 'close'):
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
                except asyncio.TimeoutError:
                    logger.warning("Timed out waiting for DroidRun workflow to finish")
            if handler.ctx and handler.ctx.is_running:
                await handler.ctx.shutdown()
        except Exception as e:
            logger.warning(f"Error while shutting down DroidRun workflow: {e}")
        finally:
            self._current_handler = None
            self._handler_loop = None

    def request_cancel(self) -> bool:
        """Request cancellation of the active DroidRun workflow if available."""
        handler = self._current_handler
        loop = self._handler_loop
        if not handler or not loop:
            return False

        if loop.is_running():
            loop.call_soon_threadsafe(lambda: asyncio.create_task(handler.cancel_run()))
            return True

        return False