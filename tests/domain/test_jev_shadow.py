import asyncio
import json
from types import SimpleNamespace

import pytest

from mobile_crawler.domain.jev_shadow import (
    JevPick,
    JevShadow,
    build_request,
    compare,
    normalize_action,
)

ELEMENTS = [
    {"index": 1, "className": "Button", "text": "Sign in", "resourceId": "btn_sign_in", "checkedState": ""},
    {"index": 2, "className": "EditText", "text": "Email", "resourceId": "", "checkedState": ""},
]


def answer(choice, confidence=0.9):
    return SimpleNamespace(choice=choice, confidence=confidence)


class FakeClient:
    def __init__(self, choices=None, error=None, delay=0.0):
        self.choices = choices
        self.error = error
        self.delay = delay
        self.calls = []

    async def system_one(self, state, questions, model=None):
        self.calls.append((state, questions, model))
        await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return SimpleNamespace(choices=self.choices, model="jev-1.2")


def test_build_request_lists_current_element_indexes():
    state, questions = build_request("Tap Sign in", ELEMENTS)

    assert state["subgoal"] == "Tap Sign in"
    assert [e["index"] for e in state["elements"]] == [1, 2]
    assert set(questions) == {"action", "direction", "index"}
    assert list(questions["index"].criteria) == ["1", "2"]
    assert "click" in questions["action"].criteria


def test_build_request_without_elements_skips_index_question():
    _, questions = build_request("Go back", [])

    assert "index" not in questions


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ({"action": "click", "index": 3}, {"action": "click", "index": 3, "direction": None}),
        ({"action": "click_at", "x": 1, "y": 2}, {"action": "click", "index": None, "direction": None}),
        ({"action": "type_secret", "index": 4}, {"action": "type", "index": 4, "direction": None}),
        ({"action": "system_button", "button": "back"}, {"action": "back", "index": None, "direction": None}),
        ({"action": "system_button", "button": "home"}, {"action": "other", "index": None, "direction": None}),
        ({"action": "wait", "duration": 1}, {"action": "other", "index": None, "direction": None}),
        (
            {"action": "swipe", "coordinate": [500, 1500], "coordinate2": [500, 500]},
            {"action": "swipe", "index": None, "direction": "up"},
        ),
        (
            {"action": "swipe", "coordinate": [900, 500], "coordinate2": [100, 500]},
            {"action": "swipe", "index": None, "direction": "left"},
        ),
    ],
)
def test_normalize_action(action, expected):
    assert normalize_action(action) == expected


def test_normalize_action_rejects_garbage():
    assert normalize_action({"nope": 1}) is None
    assert normalize_action(None) is None


def test_compare_click_needs_same_index():
    jev = JevPick(action="click", index=1, action_confidence=0.9, index_confidence=0.9)

    assert compare(jev, {"action": "click", "index": 1, "direction": None}) == (True, None)
    assert compare(jev, {"action": "click", "index": 2, "direction": None}) == (False, None)
    assert compare(jev, {"action": "back", "index": None, "direction": None}) == (False, None)


def test_compare_click_by_coordinates_has_no_element_to_compare():
    jev = JevPick(action="click", index=1)

    assert compare(jev, {"action": "click", "index": None, "direction": None}) == (None, "no_executor_index")


def test_compare_excludes_typing_and_missing_answers():
    jev = JevPick(action="type", index=2)

    assert compare(jev, {"action": "type", "index": 2, "direction": None}) == (None, "type")
    assert compare(JevPick(error="boom"), {"action": "click", "index": 1, "direction": None}) == (
        None,
        "no_jev_answer",
    )
    assert compare(jev, None) == (None, "no_executor_action")


def test_confidence_is_weakest_relevant_answer():
    click = JevPick(action="click", action_confidence=0.95, index_confidence=0.6)
    back = JevPick(action="back", action_confidence=0.95, index_confidence=0.1)

    assert click.confidence == 0.6
    assert back.confidence == 0.95


def run_step(shadow, actions, subgoal="Tap Sign in"):
    async def go():
        task = shadow.start(subgoal, ELEMENTS)
        shadow.finish(task, subgoal, actions, executor_ms=1800.0)
        await shadow.aclose()

    asyncio.run(go())


def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_step_writes_one_line_with_both_picks(tmp_path):
    client = FakeClient({"action": answer("click", 0.97), "index": answer("1", 0.91), "direction": answer("up")})
    shadow = JevShadow(api_key="k", jsonl_path=tmp_path / "reports" / "jev_shadow.jsonl", client=client)
    shadow.step_provider = lambda: 7

    run_step(shadow, [{"action": "click", "index": 1}, {"action": "click", "index": 2}])

    (line,) = read_lines(tmp_path / "reports" / "jev_shadow.jsonl")
    assert line["step"] == 7
    assert line["subgoal"] == "Tap Sign in"
    assert line["jev"]["action"] == "click"
    assert line["jev"]["index"] == 1
    assert line["jev"]["confidence"] == 0.91
    assert line["jev"]["model"] == "jev-1.2"
    assert line["jev"]["latency_ms"] >= 0
    assert line["executor"] == {"first_action": {"action": "click", "index": 1, "direction": None}, "latency_ms": 1800.0}
    assert line["agree"] is True
    assert client.calls[0][2] == "~typesafe/jev-latest"


def test_disagreement_is_logged(tmp_path):
    client = FakeClient({"action": answer("click"), "index": answer("2"), "direction": answer("up")})
    shadow = JevShadow(api_key="k", jsonl_path=tmp_path / "j.jsonl", client=client, model="~typesafe/jev-x")

    run_step(shadow, [{"action": "click", "index": 1}])

    (line,) = read_lines(tmp_path / "j.jsonl")
    assert line["agree"] is False
    assert client.calls[0][2] == "~typesafe/jev-x"


def test_typing_step_is_logged_but_excluded(tmp_path):
    client = FakeClient({"action": answer("type"), "index": answer("2"), "direction": answer("up")})
    shadow = JevShadow(api_key="k", jsonl_path=tmp_path / "j.jsonl", client=client)

    run_step(shadow, [{"action": "type", "index": 2, "text": "a@b.c"}])

    (line,) = read_lines(tmp_path / "j.jsonl")
    assert line["agree"] is None
    assert line["excluded"] == "type"


def test_jev_error_is_swallowed_and_logged(tmp_path):
    client = FakeClient(error=RuntimeError("503"))
    shadow = JevShadow(api_key="k", jsonl_path=tmp_path / "j.jsonl", client=client)

    run_step(shadow, [{"action": "click", "index": 1}])

    (line,) = read_lines(tmp_path / "j.jsonl")
    assert "503" in line["jev"]["error"]
    assert line["agree"] is None


def test_start_never_waits_for_jev(tmp_path):
    client = FakeClient({"action": answer("click"), "index": answer("1"), "direction": answer("up")}, delay=0.3)
    shadow = JevShadow(api_key="k", jsonl_path=tmp_path / "j.jsonl", client=client)

    async def go():
        loop = asyncio.get_running_loop()
        began = loop.time()
        task = shadow.start("Tap", ELEMENTS)
        shadow.finish(task, "Tap", [{"action": "click", "index": 1}], executor_ms=None)
        elapsed = loop.time() - began
        await shadow.aclose()
        return elapsed

    assert asyncio.run(go()) < 0.1
    assert len(read_lines(tmp_path / "j.jsonl")) == 1
