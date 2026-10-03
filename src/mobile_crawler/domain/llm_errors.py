"""A failed AI model call, classified into a clear user-facing message.

The crawl cannot continue without its model, so any such failure stops the run and is shown to the user.
"""

from __future__ import annotations

from typing import Any

KIND_USAGE_LIMIT = "usage_limit"
KIND_CREDITS = "credits"
KIND_AUTH = "auth"
KIND_EMPTY = "empty_response"
KIND_TIMEOUT = "timeout"
KIND_OTHER = "other"

_CREDIT_MARKERS = ("insufficient", "out of credit", "credits", "quota", "billing", "balance", "usage limit")


class LLMCallError(RuntimeError):
    """The AI model could not give a usable answer. ``kind`` is one of the ``KIND_*`` values."""

    def __init__(self, message: str, kind: str = KIND_OTHER) -> None:
        super().__init__(message)
        self.kind = kind


def _status_code(exc: BaseException) -> int | None:
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    return status if isinstance(status, int) else None


def is_fatal_llm_error(exc: BaseException) -> bool:
    """True when retrying cannot help: bad/missing key, no credit, quota used up."""
    status = _status_code(exc)
    if status in (401, 402, 403):
        return True
    text = str(exc).lower()
    return status in (400, 429) and any(marker in text for marker in _CREDIT_MARKERS)


def classify_llm_error(exc: BaseException, model: str | None = None) -> LLMCallError:
    """Turn the last exception of a failed model call into an ``LLMCallError`` with a clear message."""
    if isinstance(exc, LLMCallError):
        return exc
    who = f"The AI model ({model})" if model else "The AI model"
    detail = str(exc) or type(exc).__name__
    status = _status_code(exc)
    text = detail.lower()
    if isinstance(exc, ValueError) and "empty" in text:
        return LLMCallError(
            f"{who} returned an empty response 3 times in a row, so the crawl was stopped. "
            "The model, its provider or your plan may be failing or out of usage; check your provider "
            "account, or pick another model and start again.",
            KIND_EMPTY,
        )
    if status in (401, 403):
        return LLMCallError(
            f"{who} rejected the API key (HTTP {status}). Check the key in Settings > API Keys.", KIND_AUTH
        )
    if status == 402 or (status in (400, 429) and any(m in text for m in _CREDIT_MARKERS)):
        return LLMCallError(
            f"{who} has no usage or credit left ({detail}). Add credit or wait for your limit to reset, "
            "then start again.",
            KIND_CREDITS,
        )
    if status == 429:
        return LLMCallError(
            f"{who} is rate limited (HTTP 429) and kept refusing requests. Wait a while or use another model.",
            KIND_USAGE_LIMIT,
        )
    if isinstance(exc, TimeoutError):
        return LLMCallError(f"{who} did not answer in time, 3 attempts in a row.", KIND_TIMEOUT)
    return LLMCallError(f"{who} could not be reached or failed 3 times in a row: {detail}", KIND_OTHER)


def find_llm_call_error(exc: BaseException | None) -> LLMCallError | None:
    """The ``LLMCallError`` in ``exc``'s cause chain (agents re-wrap it), if any."""
    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        if isinstance(exc, LLMCallError):
            return exc
        seen.add(id(exc))
        exc = exc.__cause__ or exc.__context__
    return None


def model_name(llm: Any) -> str | None:
    return getattr(llm, "model", None) or getattr(llm, "model_name", None)
