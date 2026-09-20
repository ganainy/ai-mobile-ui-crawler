"""
ExecutorAgent - Action execution workflow.

This agent is responsible for:
- Taking a specific subgoal from the Manager
- Analyzing the current UI state
- Selecting and executing appropriate actions
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from llama_index.core.base.llms.types import ChatMessage, ImageBlock, TextBlock
from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import Context, StartEvent, StopEvent, Workflow, step

from mobile_crawler.domain.crawler_agent.agent.executor.events import (
    ExecutorActionEvent,
    ExecutorActionResultEvent,
    ExecutorContextEvent,
    ExecutorResponseEvent,
)
from mobile_crawler.domain.crawler_agent.agent.executor.prompts import parse_executor_response
from mobile_crawler.domain.crawler_agent.agent.usage import get_usage_from_response
from mobile_crawler.domain.crawler_agent.agent.utils.inference import acall_with_retries
from mobile_crawler.domain.crawler_agent.agent.utils.prompt_resolver import PromptResolver
from mobile_crawler.domain.crawler_agent.config_manager.config_manager import AgentConfig
from mobile_crawler.domain.crawler_agent.config_manager.prompt_loader import PromptLoader
from mobile_crawler.domain.ui_wait_predicate import wait_for_ui_settled_after_action

if TYPE_CHECKING:
    from mobile_crawler.domain.crawler_agent.agent.action_context import ActionContext
    from mobile_crawler.domain.crawler_agent.agent.droid import CrawlerAgentState
    from mobile_crawler.domain.crawler_agent.agent.tool_registry import ToolRegistry

logger = logging.getLogger("crawler_agent")


class ExecutorAgent(Workflow):
    """
    Action execution agent that performs specific actions.

    Single-turn agent: receives subgoal, selects action, executes it.
    Uses ChatMessage objects directly for LLM calls.
    """

    # Flow-control tools hidden from executor's LLM prompt
    _EXCLUDE_TOOLS = {"remember", "complete"}

    # Actions that leave the screen as it was, so an Action Batch may continue
    # after them. Anything else navigates and ends the batch.
    _BATCHABLE_ACTIONS = {"type", "type_secret", "input", "input_text"}

    def __init__(
        self,
        llm: LLM,
        registry: ToolRegistry | None,
        action_ctx: ActionContext | None,
        shared_state: CrawlerAgentState,
        agent_config: AgentConfig,
        prompt_resolver: PromptResolver | None = None,
        max_actions_per_batch: int = 1,
        foreground_package: Callable[[], Awaitable[str | None]] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.max_actions_per_batch = max(1, max_actions_per_batch)
        self.foreground_package = foreground_package
        self.llm = llm
        self.agent_config = agent_config
        self.config = agent_config.executor
        self.vision = agent_config.executor.vision
        self.registry = registry
        self.action_ctx = action_ctx
        self.shared_state = shared_state
        self.prompt_resolver = prompt_resolver or PromptResolver()

        logger.debug("ExecutorAgent initialized.")

    @step
    async def prepare_context(self, ctx: Context, ev: StartEvent) -> ExecutorContextEvent:
        """Prepare executor context and prompt."""
        subgoal = ev.get("subgoal", "")
        logger.debug(f"🧠 Executor thinking about action for: {subgoal}")

        # Build action history (last 5)
        action_history = []
        if self.shared_state.action_history:
            n = min(5, len(self.shared_state.action_history))
            action_history = [
                {"action": act, "summary": summ, "outcome": outcome, "error": err}
                for act, summ, outcome, err in zip(
                    self.shared_state.action_history[-n:],
                    self.shared_state.summary_history[-n:],
                    self.shared_state.action_outcomes[-n:],
                    self.shared_state.error_descriptions[-n:],
                    strict=True,
                )
            ]

        # Get available secrets (only if type_secret is actually in the registry)
        available_secrets = []
        if (
            self.registry
            and "type_secret" in self.registry.tools
            and self.action_ctx
            and self.action_ctx.credential_manager
        ):
            available_secrets = await self.action_ctx.credential_manager.get_keys()

        # Build prompt variables
        variables = {
            "instruction": self.shared_state.instruction,
            "app_card": "",
            "device_state": self.shared_state.formatted_device_state,
            "plan": self.shared_state.plan,
            "subgoal": subgoal,
            "progress_status": self.shared_state.progress_summary,
            "atomic_actions": self.registry.get_signatures(exclude=self._EXCLUDE_TOOLS),
            "action_history": action_history,
            "available_secrets": available_secrets,
            "variables": self.shared_state.custom_variables,
            "platform": self.shared_state.platform,
            "max_actions_per_batch": self.max_actions_per_batch,
        }

        custom_prompt = self.prompt_resolver.get_prompt("executor_system")
        if custom_prompt:
            prompt_text = PromptLoader.render_template(custom_prompt, variables)
        else:
            prompt_text = await PromptLoader.load_prompt(
                self.agent_config.get_executor_system_prompt_path(),
                variables,
            )

        # Build message
        messages = [ChatMessage(role="user", blocks=[TextBlock(text=prompt_text)])]

        # Add screenshot if vision enabled
        if self.vision:
            screenshot = self.shared_state.screenshot
            if screenshot is not None:
                messages[0].blocks.append(ImageBlock(image=screenshot))
                logger.debug("📸 Using screenshot for Executor")
            else:
                logger.warning("⚠️ Vision enabled but no screenshot available")
        await ctx.store.set("executor_messages", messages)
        event = ExecutorContextEvent(subgoal=subgoal)
        ctx.write_event_to_stream(event)
        return event

    @step
    async def get_response(self, ctx: Context, ev: ExecutorContextEvent) -> ExecutorResponseEvent:
        """Get LLM response."""
        logger.debug("Executor getting LLM response...")

        # Get messages from context
        messages = await ctx.store.get("executor_messages")

        # Prompt text + screenshot for AI Monitor (collected once, used on all paths)
        prompt_text = messages[0].content if messages else None
        screenshot = self.shared_state.screenshot

        try:
            logger.info("Executor response:", extra={"color": "green"})
            llm_start = time.perf_counter()
            response = await acall_with_retries(self.llm, messages, stream=self.agent_config.streaming)
            executor_llm_ms = (time.perf_counter() - llm_start) * 1000
            response_text = str(response)
        except ValueError as e:
            logger.warning(f"Executor LLM returned empty response: {e}")
            error_response = (
                "### Thought\nExecutor failed to respond, try again\n"
                '### Action\n{"action": "invalid"}\n'
                "### Description\nExecutor failed to respond, try again"
            )
            event = ExecutorResponseEvent(
                response=error_response,
                usage=None,
                executor_llm_ms=None,
                prompt_text=prompt_text,
                screenshot=screenshot,
                success=False,
                error=str(e),
                vision_enabled=self.vision,
                elements=self.shared_state.a11y_tree,
            )
            ctx.write_event_to_stream(event)
            return event
        except Exception as e:
            raise RuntimeError(f"Error calling LLM in executor: {e}") from e

        # Extract usage
        usage = None
        try:
            usage = get_usage_from_response(self.llm.class_name(), response)
        except Exception as e:
            logger.warning(f"Could not get usage: {e}")

        # Parse response once here (Fix 8) so consumers read parsed_action instead
        # of re-parsing the raw text. Keep it best-effort: parse failure doesn't
        # block the event from emitting; process_response will handle the error.
        parsed_action = None
        try:
            parsed_action = parse_executor_response(response_text)
        except Exception as e:
            logger.warning(f"Failed to parse executor response in get_response: {e}")

        event = ExecutorResponseEvent(
            response=response_text,
            usage=usage,
            executor_llm_ms=executor_llm_ms,
            prompt_text=prompt_text,
            screenshot=screenshot,
            parsed_action=parsed_action,
            vision_enabled=self.vision,
            elements=self.shared_state.a11y_tree,
        )
        ctx.write_event_to_stream(event)
        return event

    @step
    async def process_response(self, ctx: Context, ev: ExecutorResponseEvent) -> ExecutorActionEvent:
        """Parse LLM response and extract action."""
        logger.debug("⚙️ Processing executor response...")

        response_text = ev.response

        try:
            # Prefer the result already parsed at get_response (single-parse,
            # Fix 8); fall back to parsing here when it's absent (failure path).
            parsed = ev.parsed_action if ev.parsed_action is not None else parse_executor_response(response_text)
        except Exception as e:
            logger.error(f"❌ Failed to parse executor response: {e}")
            return ExecutorActionEvent(
                action_json=json.dumps({"action": "invalid"}),
                thought=f"Failed to parse response: {str(e)}",
                description="Invalid response format from LLM",
                full_response=response_text,
            )

        # Update unified state
        self.shared_state.last_thought = parsed["thought"]

        event = ExecutorActionEvent(
            action_json=parsed["action"],
            thought=parsed["thought"],
            description=parsed["description"],
            full_response=response_text,
            actions=parsed.get("actions", []),
        )

        ctx.write_event_to_stream(event)
        return event

    async def _foreground(self) -> str | None:
        if self.foreground_package is None:
            return None
        try:
            return await self.foreground_package()
        except Exception as e:
            logger.debug(f"Foreground package check failed: {e}")
            return None

    @step
    async def execute(self, ctx: Context, ev: ExecutorActionEvent) -> ExecutorActionResultEvent:
        """Execute the action."""
        logger.debug(f"⚡ Executing action: {ev.description}")

        if ev.actions:
            planned = ev.actions
        else:
            try:
                planned = [json.loads(ev.action_json)]
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse action JSON: {e}")
                event = ExecutorActionResultEvent(
                    action={"action": "invalid"},
                    success=False,
                    error=f"Invalid action JSON: {str(e)}",
                    summary="Failed to parse action",
                    thought=ev.thought,
                    full_response=ev.full_response,
                )
                ctx.write_event_to_stream(event)
                return event
        planned = planned[: self.max_actions_per_batch]

        baseline = await self._foreground() if len(planned) > 1 else None
        results: list[dict] = []
        for position, action_dict in enumerate(planned):
            action_type = action_dict.get("action", "unknown")
            action_args = {k: v for k, v in action_dict.items() if k != "action"}

            result = await self.registry.execute(action_type, action_args, self.action_ctx, workflow_ctx=ctx)
            results.append(
                {
                    "action": action_dict,
                    "outcome": result.success,
                    "error": "" if result.success else result.summary,
                    "summary": result.summary,
                }
            )
            logger.debug(f"{'✅' if result.success else '❌'} Execution complete: {result.summary}")

            if not result.success or position == len(planned) - 1:
                break
            if action_type not in self._BATCHABLE_ACTIONS:
                break
            if baseline is not None and await self._foreground() != baseline:
                logger.info("Action Batch aborted: foreground package changed")
                break

        await wait_for_ui_settled_after_action(
            self.action_ctx.state_provider,
            results[-1]["action"].get("action", "unknown"),
            self.agent_config.wait_for_stable_ui,
        )

        last = results[-1]
        failed = next((r for r in results if not r["outcome"]), None)
        event = ExecutorActionResultEvent(
            action=last["action"],
            success=failed is None,
            error=failed["error"] if failed else "",
            summary=last["summary"],
            thought=ev.thought,
            full_response=ev.full_response,
            results=results,
        )
        ctx.write_event_to_stream(event)
        return event

    @step
    async def finalize(self, ctx: Context, ev: ExecutorActionResultEvent) -> StopEvent:
        """Return executor results to parent workflow."""
        logger.debug("✅ Executor execution complete")

        return StopEvent(
            result={
                "action": ev.action,
                "outcome": ev.success,
                "error": ev.error,
                "summary": ev.summary,
                "thought": ev.thought,
                "results": ev.results,
            }
        )
