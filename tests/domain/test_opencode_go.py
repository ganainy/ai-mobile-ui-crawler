import asyncio
from unittest.mock import MagicMock, patch

import pytest

from mobile_crawler.domain.crawler_agent.agent.utils.inference import acall_with_retries
from mobile_crawler.domain.opencode_go import (
    LIMIT_MESSAGE,
    OPENCODE_GO_BASE_URL,
    OpenCodeGoLimitError,
    chat_models_from_ids,
    is_limit_error,
)
from mobile_crawler.domain.providers.registry import ProviderRegistry


def test_only_chat_completions_families_are_kept():
    ids = ["glm-5", "kimi-k3", "deepseek-v4-flash", "longcat-2", "hy3", "gpt-luna", "grok-5", "muse-spark",
           "minimax-m3", "qwen-4"]
    assert [m["id"] for m in chat_models_from_ids(ids)] == ["glm-5", "kimi-k3", "deepseek-v4-flash", "longcat-2", "hy3"]


def test_only_the_vision_model_is_flagged_vision():
    models = {m["id"]: m for m in chat_models_from_ids(["kimi-k3", "deepseek-v4-flash-vision-exp"])}
    assert models["deepseek-v4-flash-vision-exp"]["supports_vision"] is True
    assert models["kimi-k3"]["supports_vision"] is False
    assert models["kimi-k3"]["provider"] == "opencode_go"


def test_limit_error_detected_by_status_code():
    exc = Exception("boom")
    exc.status_code = 429
    assert is_limit_error(exc)
    response_exc = Exception("boom")
    response_exc.response = MagicMock(status_code=429)
    assert is_limit_error(response_exc)
    assert not is_limit_error(ValueError("x"))


def test_limit_message_names_provider_and_balance():
    assert "OpenCode Go" in LIMIT_MESSAGE
    assert "Use balance" in LIMIT_MESSAGE


def test_registry_lists_models_without_a_key_and_filters():
    registry = ProviderRegistry()
    response = MagicMock()
    response.json.return_value = {"data": [{"id": "kimi-k3"}, {"id": "gpt-luna"}]}
    with patch("mobile_crawler.domain.providers.registry.requests.get", return_value=response) as get:
        models = registry.fetch_opencode_go_models()
    assert get.call_args.args[0] == f"{OPENCODE_GO_BASE_URL}/models"
    assert [m["id"] for m in models] == ["kimi-k3"]


def test_registry_propagates_fetch_failure():
    registry = ProviderRegistry()
    with patch("mobile_crawler.domain.providers.registry.requests.get", side_effect=OSError("down")):
        with pytest.raises(RuntimeError):
            registry.fetch_opencode_go_models()


def test_call_with_retries_does_not_retry_an_opencode_go_limit():
    error = Exception("429")
    error.status_code = 429
    llm = MagicMock(api_base=OPENCODE_GO_BASE_URL)
    calls = []

    async def achat(messages):
        calls.append(1)
        raise error

    llm.achat = achat
    with pytest.raises(OpenCodeGoLimitError) as info:
        asyncio.run(acall_with_retries(llm, [], delay=0))
    assert len(calls) == 1
    assert str(info.value) == LIMIT_MESSAGE


def test_call_with_retries_still_retries_429_from_other_providers():
    error = Exception("429")
    error.status_code = 429
    llm = MagicMock(api_base="https://openrouter.ai/api/v1")
    calls = []

    async def achat(messages):
        calls.append(1)
        raise error

    llm.achat = achat
    with pytest.raises(Exception, match="429"):
        asyncio.run(acall_with_retries(llm, [], delay=0))
    assert len(calls) == 3
