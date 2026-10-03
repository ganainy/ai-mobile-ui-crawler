import asyncio
from unittest.mock import MagicMock

import pytest

from mobile_crawler.domain.crawler_agent.agent.utils.inference import acall_with_retries
from mobile_crawler.domain.llm_errors import (
    KIND_AUTH,
    KIND_CREDITS,
    KIND_EMPTY,
    LLMCallError,
    find_llm_call_error,
)


def _llm(achat, model="m1"):
    llm = MagicMock(api_base="https://openrouter.ai/api/v1", model=model)
    llm.achat = achat
    return llm


def _http_error(status, text="x"):
    error = Exception(text)
    error.status_code = status
    return error


def test_empty_response_after_retries_is_a_clear_llm_error():
    async def achat(messages):
        return MagicMock(message=MagicMock(content=""))

    with pytest.raises(LLMCallError) as info:
        asyncio.run(acall_with_retries(_llm(achat), [], delay=0))
    assert info.value.kind == KIND_EMPTY
    assert "empty response" in str(info.value) and "m1" in str(info.value)


@pytest.mark.parametrize("status,kind", [(401, KIND_AUTH), (402, KIND_CREDITS)])
def test_auth_and_credit_errors_stop_at_once(status, kind):
    calls = []

    async def achat(messages):
        calls.append(1)
        raise _http_error(status)

    with pytest.raises(LLMCallError) as info:
        asyncio.run(acall_with_retries(_llm(achat), [], delay=0))
    assert info.value.kind == kind
    assert len(calls) == 1


def test_quota_text_on_429_is_not_retried():
    calls = []

    async def achat(messages):
        calls.append(1)
        raise _http_error(429, "You exceeded your current quota")

    with pytest.raises(LLMCallError) as info:
        asyncio.run(acall_with_retries(_llm(achat), [], delay=0))
    assert info.value.kind == KIND_CREDITS
    assert len(calls) == 1


def test_find_llm_call_error_walks_the_cause_chain():
    inner = LLMCallError("boom")
    outer = RuntimeError("wrapped")
    outer.__cause__ = inner
    assert find_llm_call_error(outer) is inner
    assert find_llm_call_error(ValueError("x")) is None
