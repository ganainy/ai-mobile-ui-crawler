"""Jev shadow spike (Experimental Feature): log TypeSafe Jev's element pick beside the Executor's.

Jev answers typed questions about a text state in 70-500 ms. Here it is asked, alongside the
Executor's LLM call, which action and which element the Manager's subgoal calls for. Its answer
is only written to ``jev_shadow.jsonl``; it never acts on the device and never delays the step.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mobile_crawler.config.api_keys import resolve_api_key

logger = logging.getLogger("crawler_agent")

DEFAULT_MODEL = "~typesafe/jev-latest"
OPENROUTER_BASE_URL = "https://openrouter.ai/api"
REQUEST_TIMEOUT_S = 20.0
CLOSE_WAIT_S = 5.0  # how long the end of a run waits for the last lines

ACTION_CHOICES = {
    "click": "Tap an element",
    "long_press": "Press and hold an element",
    "swipe": "Scroll or swipe the screen",
    "type": "Type text into an input field",
    "back": "Press the system back button",
    "open_app": "Open an app by name",
    "other": "Any other action (wait, home, ...)",
}
DIRECTION_CHOICES = {"up": None, "down": None, "left": None, "right": None}

# Executor action names that mean the same as a Jev action label.
_ACTION_ALIASES = {
    "click_at": "click",
    "click_area": "click",
    "long_press_at": "long_press",
    "type_secret": "type",
    "input": "type",
    "input_text": "type",
}
_TARGET_ACTIONS = ("click", "long_press")


def sdk_available() -> bool:
    """True when ``typesafe-sdk`` can be imported."""
    try:
        import typesafe_sdk  # noqa: F401
    except ImportError:
        return False
    return True


def jev_shadow_enabled(config_manager) -> bool:
    """The saved ``jev_shadow_enabled`` setting (default off)."""
    return bool(config_manager.get("jev_shadow_enabled", False))


def jev_shadow_model(config_manager) -> str:
    """The saved ``jev_shadow_model`` setting, or the default when blank."""
    return str(config_manager.get("jev_shadow_model", DEFAULT_MODEL) or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def jev_shadow_openrouter_key(config_manager) -> str | None:
    return resolve_api_key(config_manager, "openrouter_api_key", ["OPENROUTER_API_KEY"])


def jev_shadow_problem(config_manager) -> str | None:
    """Why an enabled Jev shadow cannot run (missing OpenRouter key or SDK); None if fine or off."""
    if not jev_shadow_enabled(config_manager):
        return None
    if not jev_shadow_openrouter_key(config_manager):
        return "no OpenRouter API key is saved (Settings > API Keys & Parsing)"
    if not sdk_available():
        return "the typesafe-sdk package is not installed in this environment"
    return None


def normalize_action(action: dict[str, Any] | None) -> dict[str, Any] | None:
    """Reduce an Executor action dict to ``{action, index, direction}`` in Jev's vocabulary."""
    if not isinstance(action, dict) or "action" not in action:
        return None
    name = str(action["action"])
    name = _ACTION_ALIASES.get(name, name)
    if name == "system_button":
        name = "back" if action.get("button") == "back" else "other"
    elif name not in ACTION_CHOICES:
        name = "other"
    index = action.get("index")
    return {
        "action": name,
        "index": index if isinstance(index, int) and not isinstance(index, bool) else None,
        "direction": _swipe_direction(action) if name == "swipe" else None,
    }


def _swipe_direction(action: dict[str, Any]) -> str | None:
    """Direction the finger moves, from a swipe's two coordinates."""
    try:
        (x1, y1), (x2, y2) = action["coordinate"], action["coordinate2"]
        dx, dy = float(x2) - float(x1), float(y2) - float(y1)
    except (KeyError, TypeError, ValueError):
        return None
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


def element_label(element: dict[str, Any]) -> str:
    """One-line description of an element, as the Executor sees it."""
    parts = [str(element.get("className") or ""), str(element.get("text") or "")]
    resource_id = str(element.get("resourceId") or "")
    if resource_id and resource_id != element.get("text"):
        parts.append(resource_id)
    if element.get("checkedState"):
        parts.append(str(element["checkedState"]))
    return " | ".join(p for p in parts if p)


def build_request(subgoal: str, elements: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(state, questions)`` for one Executor step.

    ``questions`` maps names to SDK ``Choice`` objects. ``index`` lists the current element
    indexes; it is left out when the screen has no elements.
    """
    from typesafe_sdk import Choice

    indexed = [e for e in elements if isinstance(e, dict) and isinstance(e.get("index"), int)]
    state = {
        "subgoal": subgoal,
        "elements": [{"index": e["index"], "element": element_label(e)} for e in indexed],
    }
    questions: dict[str, Any] = {
        "action": Choice(
            instructions="Which single action does the subgoal call for first?",
            criteria=dict(ACTION_CHOICES),
        ),
        "direction": Choice(
            instructions="If the action is a swipe, in which direction does the finger move?",
            criteria=dict(DIRECTION_CHOICES),
        ),
    }
    if indexed:
        questions["index"] = Choice(
            instructions="Which element (by index) does the first action target?",
            criteria={str(e["index"]): element_label(e) or None for e in indexed},
        )
    return state, questions


@dataclass
class JevPick:
    """Jev's answer for one step (or why there is none)."""

    action: str | None = None
    action_confidence: float | None = None
    index: int | None = None
    index_confidence: float | None = None
    direction: str | None = None
    direction_confidence: float | None = None
    latency_ms: float | None = None
    model: str | None = None
    error: str | None = None

    @property
    def confidence(self) -> float | None:
        """The weakest confidence among the answers that matter for this pick."""
        values = [self.action_confidence]
        if self.action in _TARGET_ACTIONS:
            values.append(self.index_confidence)
        elif self.action == "swipe":
            values.append(self.direction_confidence)
        known = [v for v in values if v is not None]
        return min(known) if known and len(known) == len(values) else None


def parse_response(response: Any) -> JevPick:
    """Turn an SDK ``SystemOneResponse`` into a ``JevPick``."""
    choices = response.choices
    pick = JevPick(model=getattr(response, "model", None))
    if "action" in choices:
        pick.action = choices["action"].choice
        pick.action_confidence = choices["action"].confidence
    if "index" in choices:
        chosen = choices["index"].choice
        pick.index = int(chosen) if chosen.lstrip("-").isdigit() else None
        pick.index_confidence = choices["index"].confidence
    if pick.action == "swipe" and "direction" in choices:
        pick.direction = choices["direction"].choice
        pick.direction_confidence = choices["direction"].confidence
    return pick


def compare(jev: JevPick, executor: dict[str, Any] | None) -> tuple[bool | None, str | None]:
    """Whether Jev agrees with the Executor's first action; ``(None, reason)`` when not comparable."""
    if executor is None:
        return None, "no_executor_action"
    if executor["action"] == "type":
        return None, "type"
    if jev.error or jev.action is None:
        return None, "no_jev_answer"
    if jev.action != executor["action"]:
        return False, None
    if jev.action in _TARGET_ACTIONS:
        if executor["index"] is None:
            return None, "no_executor_index"  # e.g. click_at by coordinates: no element to compare
        return jev.index == executor["index"], None
    if jev.action == "swipe" and executor["direction"] is not None:
        return jev.direction == executor["direction"], None
    return True, None


@dataclass
class JevShadow:
    """Asks Jev about each Executor step and appends the comparison to a JSONL file."""

    api_key: str
    jsonl_path: Path
    model: str = DEFAULT_MODEL
    step_provider: Any = None  # () -> int, the crawl's current step number
    client: Any = None  # SDK async client; built on first use unless a test supplies one
    _tasks: set = field(default_factory=set, init=False, repr=False)
    _lines_written: int = field(default=0, init=False, repr=False)

    def start(self, subgoal: str, elements: list[dict[str, Any]] | None) -> asyncio.Task:
        """Begin asking Jev; the task resolves to a ``JevPick`` and never raises."""
        return asyncio.ensure_future(self._ask(subgoal, list(elements or [])))

    def finish(
        self,
        task: asyncio.Task,
        subgoal: str,
        actions: list[dict[str, Any]] | None,
        executor_ms: float | None,
    ) -> None:
        """Write the step's line once Jev has answered, without making the caller wait."""
        step = self.step_provider() if callable(self.step_provider) else None
        recorder = asyncio.ensure_future(self._record(task, step, subgoal, actions, executor_ms))
        self._tasks.add(recorder)
        recorder.add_done_callback(self._tasks.discard)

    async def aclose(self) -> None:
        """Give pending lines a few seconds to finish, drop the rest, then close the client."""
        if self._tasks:
            _, pending = await asyncio.wait(list(self._tasks), timeout=CLOSE_WAIT_S)
            for recorder in pending:
                recorder.cancel()
        client, self.client = self.client, None
        if client is not None and hasattr(client, "aclose"):
            try:
                await client.aclose()
            except Exception as e:
                logger.debug(f"Jev shadow client close failed: {e}")

    async def _ask(self, subgoal: str, elements: list[dict[str, Any]]) -> JevPick:
        started = time.perf_counter()
        try:
            state, questions = build_request(subgoal, elements)
            if self.client is None:
                from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy

                self.client = AsyncTypeSafeClient(
                    api_key=self.api_key,
                    base_url=OPENROUTER_BASE_URL,
                    retry=RetryPolicy(max_retries=0),
                    timeout=REQUEST_TIMEOUT_S,
                )
            response = await self.client.system_one(state=state, questions=questions, model=self.model)
            pick = parse_response(response)
        except Exception as e:
            logger.warning(f"Jev shadow call failed: {e}")
            pick = JevPick(error=f"{type(e).__name__}: {e}")
        pick.latency_ms = (time.perf_counter() - started) * 1000
        return pick

    async def _record(
        self,
        task: asyncio.Task,
        step: int | None,
        subgoal: str,
        actions: list[dict[str, Any]] | None,
        executor_ms: float | None,
    ) -> None:
        try:
            pick = await task
            first = normalize_action(actions[0]) if actions else None
            agree, excluded = compare(pick, first)
            line = {
                "step": step,
                "subgoal": subgoal,
                "jev": {
                    "action": pick.action,
                    "index": pick.index,
                    "direction": pick.direction,
                    "confidence": pick.confidence,
                    "action_confidence": pick.action_confidence,
                    "index_confidence": pick.index_confidence,
                    "latency_ms": pick.latency_ms,
                    "model": pick.model,
                    "error": pick.error,
                },
                "executor": {"first_action": first, "latency_ms": executor_ms},
                "agree": agree,
                "excluded": excluded,
            }
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            with self.jsonl_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
            self._lines_written += 1
        except Exception as e:
            logger.warning(f"Jev shadow could not record step {step}: {e}")
