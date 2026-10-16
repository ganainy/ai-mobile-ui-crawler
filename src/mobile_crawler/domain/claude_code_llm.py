"""Claude via the user's own, unmodified Claude Code program (``claude -p``).

The crawler never sees or stores Claude.ai login tokens: the user signs in to Claude Code themselves
(``claude auth login``) and each model call is one headless ``claude -p`` run with no tools. This is the only
route that uses a Claude subscription without extracting its credentials; Anthropic's terms (code.claude.com/docs/
en/legal-and-compliance) allow signing in to the unmodified Claude Code binary but not third-party apps handling
subscription tokens, and prefer API keys for programs that call Claude. Heavy automated use may hit plan limits.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import tempfile
from typing import Any, Sequence

from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    ChatResponseAsyncGen,
    ChatResponseGen,
    CompletionResponse,
    CompletionResponseAsyncGen,
    CompletionResponseGen,
    ImageBlock,
    LLMMetadata,
    MessageRole,
    TextBlock,
)
from llama_index.core.llms.callbacks import llm_chat_callback, llm_completion_callback
from llama_index.core.llms.custom import CustomLLM
from pydantic import Field

from mobile_crawler.domain.llm_errors import KIND_AUTH, KIND_OTHER, KIND_USAGE_LIMIT, LLMCallError

CLAUDE_CODE_DEFAULT_MODEL = "sonnet"
CLAUDE_CODE_MODELS = [
    {"id": "haiku", "name": "Claude Haiku (via Claude Code)", "provider": "claude_code", "supports_vision": True},
    {"id": "sonnet", "name": "Claude Sonnet (via Claude Code)", "provider": "claude_code", "supports_vision": True},
    {"id": "opus", "name": "Claude Opus (via Claude Code)", "provider": "claude_code", "supports_vision": True},
]

# Claude Code tells the model it has no tools, while the crawler's prompts talk about "tools" and "actions". Without
# this note the model sometimes concludes the tools are missing and refuses to act ("blocked: no device-control tool"),
# which wasted 16 of 27 steps in a Cut the Rope run.
FRAMING_NOTE = (
    "IMPORTANT CONTEXT: this is a plain text conversation inside an automation program. You have no callable tools "
    "and you do not need any. Any 'tools', 'actions' or 'functions' mentioned in the instructions below are NOT "
    "things you call: you request them by writing your answer in exactly the output format the instructions "
    "describe, and the program carries them out on the phone for you. Never answer that a tool is missing, "
    "unavailable, or that you are blocked; always produce the requested output format for the current screen."
)

_LIMIT_MARKERS = ("usage limit", "limit reached", "rate limit", "rate_limit", "overloaded", "5-hour", "weekly limit")
_AUTH_MARKERS = ("not logged in", "please run /login", "invalid api key", "authentication", "oauth", "401", "login")


def claude_executable() -> str | None:
    """Path to the ``claude`` program, or None when Claude Code is not installed."""
    return shutil.which("claude") or (
        os.path.expanduser("~/.local/bin/claude") if os.path.exists(os.path.expanduser("~/.local/bin/claude")) else None
    )


def build_args(model: str, system_prompt: str) -> list[str]:
    """Command line for one tool-less, single-turn, no-persistence Claude Code call."""
    args = [
        "-p",
        "--input-format", "stream-json",
        "--output-format", "stream-json",
        "--verbose",
        "--model", model,
        "--tools", "",
        "--max-turns", "1",
        "--no-session-persistence",
        "--disable-slash-commands",
        "--setting-sources", "",
    ]
    args += ["--system-prompt", f"{FRAMING_NOTE}\n\n{system_prompt}" if system_prompt else FRAMING_NOTE]
    return args


def _role_label(role: MessageRole) -> str:
    return {MessageRole.ASSISTANT: "assistant", MessageRole.USER: "user"}.get(role, str(role.value))


def split_messages(messages: Sequence[ChatMessage]) -> tuple[str, list[dict[str, Any]]]:
    """System text plus the content blocks of one user turn.

    Earlier turns are written out as labelled text so the model sees the whole conversation; images keep their
    position. The last message is sent as-is.
    """
    system_parts: list[str] = []
    content: list[dict[str, Any]] = []
    convo = [m for m in messages if m.role != MessageRole.SYSTEM]
    for m in messages:
        if m.role == MessageRole.SYSTEM:
            system_parts.append(m.content or "")
    for idx, m in enumerate(convo):
        last = idx == len(convo) - 1
        if len(convo) > 1 and not last:
            content.append({"type": "text", "text": f"[earlier {_role_label(m.role)} message]"})
        for block in m.blocks:
            if isinstance(block, TextBlock):
                if block.text:
                    content.append({"type": "text", "text": block.text})
            elif isinstance(block, ImageBlock):
                raw = block.resolve_image(as_base64=False).read()
                media = block.image_mimetype or "image/png"
                content.append(
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media, "data": base64.b64encode(raw).decode()},
                    }
                )
    return "\n\n".join(p for p in system_parts if p), content


def parse_stream(stdout: str) -> dict[str, Any]:
    """Final ``result`` event of the stream-json output (empty dict when none)."""
    result: dict[str, Any] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "result":
            result = event
    return result


def error_for(text: str) -> LLMCallError:
    low = (text or "").lower()
    if any(m in low for m in _LIMIT_MARKERS):
        return LLMCallError(
            "Your Claude plan's usage limit was reached (Claude Code via subscription). Wait for the limit to "
            f"reset or use another model. Details: {text[:200]}",
            KIND_USAGE_LIMIT,
        )
    if any(m in low for m in _AUTH_MARKERS):
        return LLMCallError(
            "Claude Code is not signed in. Run `claude auth login` on this machine and try again. "
            f"Details: {text[:200]}",
            KIND_AUTH,
        )
    return LLMCallError(f"Claude Code call failed: {text[:300]}", KIND_OTHER)


class ClaudeCode(CustomLLM):
    """llama-index LLM that answers through the local Claude Code program."""

    model: str = Field(default=CLAUDE_CODE_DEFAULT_MODEL)
    timeout_seconds: float = Field(default=180.0)
    executable: str | None = Field(default=None)

    @classmethod
    def class_name(cls) -> str:
        return "ClaudeCode"

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(context_window=200_000, num_output=8192, is_chat_model=True, model_name=self.model)

    async def _run(self, messages: Sequence[ChatMessage]) -> ChatResponse:
        exe = self.executable or claude_executable()
        if not exe:
            raise LLMCallError(
                "Claude Code is not installed. Install it with `curl -fsSL https://claude.ai/install.sh | bash` "
                "and sign in with `claude auth login`.",
                KIND_AUTH,
            )
        system_prompt, content = split_messages(messages)
        if not content:
            raise LLMCallError("Claude Code call had no content to send.", KIND_OTHER)
        payload = json.dumps({"type": "user", "message": {"role": "user", "content": content}}) + "\n"

        # Use the subscription login, never an API key that may be set in the environment (that would bill the API).
        env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
        with tempfile.TemporaryDirectory(prefix="claude-llm-") as workdir:  # empty cwd: no project context loaded
            proc = await asyncio.create_subprocess_exec(
                exe,
                *build_args(self.model, system_prompt),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
                env=env,
            )
            try:
                out, err = await asyncio.wait_for(proc.communicate(payload.encode()), timeout=self.timeout_seconds)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise TimeoutError(f"Claude Code did not answer within {self.timeout_seconds:.0f}s") from None

        result = parse_stream(out.decode(errors="replace"))
        if not result:
            raise error_for((err.decode(errors="replace") or out.decode(errors="replace")).strip() or "no output")
        if result.get("is_error") or result.get("subtype") not in (None, "success"):
            raise error_for(str(result.get("result") or result.get("subtype") or "unknown error"))
        text = str(result.get("result") or "")
        usage = result.get("usage") or {}
        raw = {
            "usage": {
                "input_tokens": int(usage.get("input_tokens", 0))
                + int(usage.get("cache_creation_input_tokens", 0))
                + int(usage.get("cache_read_input_tokens", 0)),
                "output_tokens": int(usage.get("output_tokens", 0)),
            },
            "total_cost_usd": result.get("total_cost_usd"),
            "duration_ms": result.get("duration_ms"),
        }
        return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content=text), raw=raw)

    @llm_chat_callback()
    async def achat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        return await self._run(messages)

    @llm_chat_callback()
    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        return asyncio.run(self._run(messages))

    @llm_completion_callback()
    def complete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponse:
        resp = asyncio.run(self._run([ChatMessage(role=MessageRole.USER, content=prompt)]))
        return CompletionResponse(text=resp.message.content or "", raw=resp.raw)

    @llm_completion_callback()
    async def acomplete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponse:
        resp = await self._run([ChatMessage(role=MessageRole.USER, content=prompt)])
        return CompletionResponse(text=resp.message.content or "", raw=resp.raw)

    def stream_complete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponseGen:
        def gen() -> CompletionResponseGen:
            full = self.complete(prompt)
            yield CompletionResponse(text=full.text, delta=full.text, raw=full.raw)

        return gen()

    def stream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponseGen:
        def gen() -> ChatResponseGen:
            full = self.chat(messages)
            yield ChatResponse(message=full.message, delta=full.message.content, raw=full.raw)

        return gen()

    async def astream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponseAsyncGen:
        async def gen() -> ChatResponseAsyncGen:
            full = await self._run(messages)
            yield ChatResponse(message=full.message, delta=full.message.content, raw=full.raw)

        return gen()

    async def astream_complete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponseAsyncGen:
        async def gen() -> CompletionResponseAsyncGen:
            full = await self.acomplete(prompt)
            yield CompletionResponse(text=full.text, delta=full.text, raw=full.raw)

        return gen()
