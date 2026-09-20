"""Action Batch: the Executor response can carry several ordered actions."""

from mobile_crawler.domain.crawler_agent.agent.executor.prompts import parse_executor_response


def _response(action_block: str) -> str:
    return (
        "### Thought ###\nFill the form.\n"
        f"### Action ###\n{action_block}\n"
        "### Description ###\nFill the form then submit."
    )


def test_single_action_response_yields_one_action():
    parsed = parse_executor_response(_response('{"action": "click", "index": 6}'))

    assert parsed["actions"] == [{"action": "click", "index": 6}]


def test_json_array_response_yields_actions_in_order():
    block = (
        '[{"action": "type", "index": 5, "text": "a@b.c"},'
        ' {"action": "type", "index": 3, "text": "pw"},'
        ' {"action": "click", "index": 4}]'
    )

    parsed = parse_executor_response(_response(block))

    assert [a["action"] for a in parsed["actions"]] == ["type", "type", "click"]
    assert [a["index"] for a in parsed["actions"]] == [5, 3, 4]


def test_multiline_array_response_is_parsed():
    block = '[\n  {"action": "type", "index": 5, "text": "x"},\n  {"action": "click", "index": 6}\n]'

    parsed = parse_executor_response(_response(block))

    assert len(parsed["actions"]) == 2


def test_single_action_string_key_is_kept_for_existing_consumers():
    parsed = parse_executor_response(_response('{"action": "click", "index": 6}'))

    assert parsed["action"] == '{"action": "click", "index": 6}'


def test_malformed_action_json_yields_no_actions():
    parsed = parse_executor_response(_response("not json at all"))

    assert parsed["actions"] == []


# --- ExecutorAgent runs an Action Batch -------------------------------------

import asyncio  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from llama_index.core.base.llms.types import ChatMessage, ChatResponse  # noqa: E402

from mobile_crawler.domain.crawler_agent.agent.executor import executor_agent as executor_module  # noqa: E402
from mobile_crawler.domain.crawler_agent.agent.executor.executor_agent import ExecutorAgent  # noqa: E402
from mobile_crawler.domain.crawler_agent.config_manager.config_manager import AgentConfig  # noqa: E402


class FakeLLM:
    def __init__(self, text):
        self._text = text

    def class_name(self):
        return "FakeLLM"

    async def achat(self, messages):
        return ChatResponse(message=ChatMessage(role="assistant", content=self._text))


class FakeRegistry:
    """Records executed actions; actions named in `failing` report failure."""

    def __init__(self, failing=()):
        self.executed = []
        self.failing = set(failing)
        self.tools = {}

    def get_signatures(self, exclude=None):
        return {}

    async def execute(self, name, args, ctx, workflow_ctx=None):
        self.executed.append({"action": name, **args})
        ok = args.get("index") not in self.failing
        return SimpleNamespace(success=ok, summary=f"{name} {'ok' if ok else 'failed'}")


def _shared_state():
    return SimpleNamespace(
        instruction="",
        formatted_device_state="",
        plan="",
        progress_summary="",
        custom_variables={},
        platform="android",
        action_history=[],
        summary_history=[],
        action_outcomes=[],
        error_descriptions=[],
        screenshot=None,
        a11y_tree=[],
        last_thought="",
    )


def _run_batch(actions_json, registry=None, max_actions=5, foreground_packages=None, monkeypatch=None):
    registry = registry or FakeRegistry()
    settles = []

    async def fake_settle(state_provider, action_type, grace):
        settles.append(action_type)
        return True

    monkeypatch.setattr(executor_module, "wait_for_ui_settled_after_action", fake_settle)

    packages = iter(foreground_packages or [])

    async def foreground():
        return next(packages, "com.app")

    async def go():
        agent = ExecutorAgent(
            llm=FakeLLM(_response(actions_json)),
            registry=registry,
            action_ctx=SimpleNamespace(state_provider=object(), credential_manager=None),
            shared_state=_shared_state(),
            agent_config=AgentConfig(streaming=False),
            max_actions_per_batch=max_actions,
            foreground_package=foreground,
            timeout=30,
        )
        return await agent.run(subgoal="fill and submit")

    return asyncio.run(go()), registry, settles


FORM = (
    '[{"action": "type", "index": 5, "text": "a@b.c"},'
    ' {"action": "type", "index": 3, "text": "pw"},'
    ' {"action": "click", "index": 4}]'
)


def test_batch_runs_all_actions_in_order(monkeypatch):
    result, registry, _ = _run_batch(FORM, monkeypatch=monkeypatch)

    assert [a["index"] for a in registry.executed] == [5, 3, 4]
    assert [r["outcome"] for r in result["results"]] == [True, True, True]
    assert result["outcome"] is True


def test_batch_stops_at_first_failure(monkeypatch):
    result, registry, _ = _run_batch(FORM, registry=FakeRegistry(failing={3}), monkeypatch=monkeypatch)

    assert [a["index"] for a in registry.executed] == [5, 3]
    assert result["outcome"] is False
    assert len(result["results"]) == 2


def test_batch_ends_after_a_navigating_action(monkeypatch):
    block = '[{"action": "click", "index": 4}, {"action": "type", "index": 5, "text": "late"}]'

    result, registry, _ = _run_batch(block, monkeypatch=monkeypatch)

    assert [a["action"] for a in registry.executed] == ["click"]
    assert len(result["results"]) == 1


def test_batch_aborts_when_foreground_package_changes(monkeypatch):
    # first value = package before the batch, second = after the first action
    result, registry, _ = _run_batch(
        FORM, foreground_packages=["com.app", "com.brave.browser"], monkeypatch=monkeypatch
    )

    assert [a["index"] for a in registry.executed] == [5]
    assert len(result["results"]) == 1


def test_batch_is_capped(monkeypatch):
    block = "[" + ",".join(f'{{"action": "type", "index": {i}, "text": "x"}}' for i in range(1, 6)) + "]"

    _, registry, _ = _run_batch(block, max_actions=2, monkeypatch=monkeypatch)

    assert [a["index"] for a in registry.executed] == [1, 2]


def test_cap_of_one_keeps_single_action_behaviour(monkeypatch):
    _, registry, _ = _run_batch(FORM, max_actions=1, monkeypatch=monkeypatch)

    assert [a["index"] for a in registry.executed] == [5]


def test_ui_settle_wait_runs_once_after_the_whole_batch(monkeypatch):
    _, _, settles = _run_batch(FORM, monkeypatch=monkeypatch)

    assert settles == ["click"]
