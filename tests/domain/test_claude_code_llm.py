import asyncio
import io
import json

import pytest
from llama_index.core.base.llms.types import ChatMessage, ImageBlock, MessageRole, TextBlock
from PIL import Image

from mobile_crawler.domain import claude_code_llm as cc
from mobile_crawler.domain.llm_errors import KIND_AUTH, KIND_USAGE_LIMIT, LLMCallError


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, format="PNG")
    return buf.getvalue()


def test_args_are_toolless_single_turn_and_carry_the_system_prompt():
    args = cc.build_args("haiku", "be brief")
    assert args[args.index("--tools") + 1] == ""
    assert args[args.index("--max-turns") + 1] == "1"
    assert "--no-session-persistence" in args
    prompt = args[args.index("--system-prompt") + 1]
    assert prompt.endswith("be brief") and "no callable tools" in prompt
    assert cc.build_args("haiku", "")[cc.build_args("haiku", "").index("--system-prompt") + 1] == cc.FRAMING_NOTE


def test_split_messages_keeps_text_and_images_in_order():
    img = png_bytes()
    system, content = cc.split_messages(
        [
            ChatMessage(role=MessageRole.SYSTEM, content="rules"),
            ChatMessage(role=MessageRole.USER, content="first"),
            ChatMessage(role=MessageRole.ASSISTANT, content="answer"),
            ChatMessage(role=MessageRole.USER, blocks=[TextBlock(text="look"), ImageBlock(image=img)]),
        ]
    )
    assert system == "rules"
    assert content[-1]["type"] == "image" and content[-1]["source"]["media_type"] == "image/png"
    assert any("earlier assistant message" in c.get("text", "") for c in content)


def test_parse_stream_takes_the_result_event():
    out = "\n".join([json.dumps({"type": "system"}), "noise", json.dumps({"type": "result", "result": "hi"})])
    assert cc.parse_stream(out)["result"] == "hi"
    assert cc.parse_stream("nothing") == {}


def test_errors_are_classified():
    assert cc.error_for("Claude AI usage limit reached|123").kind == KIND_USAGE_LIMIT
    assert cc.error_for("Not logged in · Please run /login").kind == KIND_AUTH
    assert isinstance(cc.error_for("boom"), LLMCallError)


class FakeProc:
    def __init__(self, out, err=b"", code=0):
        self._out, self._err, self.returncode = out, err, code
        self.stdin_seen = None

    async def communicate(self, data=None):
        self.stdin_seen = data
        return self._out, self._err


def run_with(monkeypatch, proc, messages, env=None):
    seen = {}

    async def fake_exec(*args, **kwargs):
        seen["args"], seen["env"] = args, kwargs["env"]
        return proc

    monkeypatch.setattr(cc.asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(cc, "claude_executable", lambda: "/bin/claude")
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    llm = cc.ClaudeCode(model="haiku")
    return asyncio.run(llm.achat(messages)), seen


def test_achat_returns_text_and_usage_and_hides_the_api_key(monkeypatch):
    result = {"type": "result", "subtype": "success", "is_error": False, "result": "pong",
              "usage": {"input_tokens": 2, "cache_creation_input_tokens": 10, "cache_read_input_tokens": 3, "output_tokens": 5}}
    proc = FakeProc(json.dumps(result).encode())
    resp, seen = run_with(monkeypatch, proc, [ChatMessage(role=MessageRole.USER, content="ping")], {"ANTHROPIC_API_KEY": "sk-x"})
    assert resp.message.content == "pong"
    assert resp.raw["usage"] == {"input_tokens": 15, "output_tokens": 5}
    assert "ANTHROPIC_API_KEY" not in seen["env"]
    assert json.loads(proc.stdin_seen)["message"]["content"][0] == {"type": "text", "text": "ping"}


def test_error_result_raises_a_clear_error(monkeypatch):
    result = {"type": "result", "subtype": "success", "is_error": True, "result": "Claude AI usage limit reached"}
    with pytest.raises(LLMCallError) as exc:
        run_with(monkeypatch, FakeProc(json.dumps(result).encode()), [ChatMessage(role=MessageRole.USER, content="x")])
    assert exc.value.kind == KIND_USAGE_LIMIT


def test_missing_program_is_reported(monkeypatch):
    monkeypatch.setattr(cc, "claude_executable", lambda: None)
    with pytest.raises(LLMCallError, match="not installed"):
        asyncio.run(cc.ClaudeCode().achat([ChatMessage(role=MessageRole.USER, content="x")]))


def test_load_llm_builds_it_without_an_api_key():
    from mobile_crawler.domain.crawler_agent.agent.utils.llm_picker import load_llm

    llm = load_llm("ClaudeCode", model="haiku", api_key="ignored", temperature=0.0)
    assert llm.class_name() == "ClaudeCode" and llm.model == "haiku"


def test_registry_lists_the_claude_code_models(monkeypatch):
    from mobile_crawler.domain.providers.registry import ProviderRegistry

    monkeypatch.setattr(cc, "claude_executable", lambda: "/bin/claude")
    ids = [m["id"] for m in ProviderRegistry().fetch_claude_code_models()]
    assert ids == ["haiku", "sonnet", "opus"]
    monkeypatch.setattr(cc, "claude_executable", lambda: None)
    with pytest.raises(RuntimeError, match="not installed"):
        ProviderRegistry().fetch_claude_code_models()
