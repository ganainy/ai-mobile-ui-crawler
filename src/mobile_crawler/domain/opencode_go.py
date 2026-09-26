"""OpenCode Go (opencode.ai/go): a subscription AI Provider served through an OpenAI-style chat endpoint."""

from typing import Any

OPENCODE_GO_BASE_URL = "https://opencode.ai/zen/go/v1"
OPENCODE_GO_DEFAULT_MODEL = "kimi-k3"
OPENCODE_GO_VISION_MODEL = "deepseek-v4-flash-vision-exp"

# `/models` lists ids only. These prefixes are the models served through `chat/completions`; the
# `responses` (GPT, Grok, Muse) and Anthropic `messages` (MiniMax, Qwen) families are hidden.
_CHAT_COMPLETIONS_PREFIXES = ("glm-", "kimi-", "deepseek-", "longcat-", "hy")

# OpenAILike defaults to a 3900-token context window; these are large-context models.
OPENCODE_GO_LLM_KWARGS = {"api_base": OPENCODE_GO_BASE_URL, "context_window": 128_000}

LIMIT_MESSAGE = (
    "OpenCode Go usage limit reached (capped per 5 hours, week and month). Wait for the limit to reset, "
    "or turn on \"Use balance\" in your OpenCode account to keep going."
)


class OpenCodeGoLimitError(RuntimeError):
    """OpenCode Go refused a request because the subscription's usage limit is used up."""

    def __init__(self) -> None:
        super().__init__(LIMIT_MESSAGE)


def chat_models_from_ids(model_ids: list[str]) -> list[dict[str, Any]]:
    """Model entries for the ids OpenCode Go serves through `chat/completions`."""
    return [
        {
            "id": model_id,
            "name": model_id,
            "provider": "opencode_go",
            "supports_vision": model_id == OPENCODE_GO_VISION_MODEL,
        }
        for model_id in model_ids
        if model_id.startswith(_CHAT_COMPLETIONS_PREFIXES)
    ]


def is_limit_error(exc: BaseException) -> bool:
    """True if ``exc`` carries HTTP 429 (the error body format is undocumented, so only the status counts)."""
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    return status == 429


def is_opencode_go_llm(llm: Any) -> bool:
    return str(getattr(llm, "api_base", "") or "").startswith(OPENCODE_GO_BASE_URL)
