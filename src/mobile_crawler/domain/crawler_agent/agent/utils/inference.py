import asyncio
import logging
from typing import TypeVar

from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    CompletionResponse,
)
from llama_index.core.prompts import PromptTemplate
from pydantic import BaseModel

from mobile_crawler.domain.llm_errors import classify_llm_error, is_fatal_llm_error, model_name
from mobile_crawler.domain.opencode_go import OpenCodeGoLimitError, is_limit_error, is_opencode_go_llm

logger = logging.getLogger("crawler_agent")

T = TypeVar("T", bound=BaseModel)


def describe_empty_response(response) -> str:
    """What an HTTP-200 reply with no text did carry: finish reason, token usage, reasoning/tool-call blocks."""
    if response is None:
        return "no response object"
    parts: list[str] = []
    raw = getattr(response, "raw", None)
    try:
        choice = (raw.choices[0] if getattr(raw, "choices", None) else None) if not isinstance(raw, dict) else None
        if choice is not None:
            parts.append(f"finish_reason={getattr(choice, 'finish_reason', None)}")
            msg = getattr(choice, "message", None)
            for field in ("reasoning_content", "reasoning", "refusal", "tool_calls"):
                value = getattr(msg, field, None)
                if value:
                    parts.append(f"{field}={str(value)[:200]!r}")
        usage = getattr(raw, "usage", None)
        if usage is not None:
            parts.append(f"usage=in:{getattr(usage, 'prompt_tokens', None)}/out:{getattr(usage, 'completion_tokens', None)}")
    except Exception as e:  # diagnostics must never break the retry loop
        parts.append(f"raw unreadable: {e!r}")
    message = getattr(response, "message", None)
    blocks = [type(b).__name__ for b in getattr(message, "blocks", None) or []]
    parts.append(f"blocks={blocks}")
    parts.append(f"additional_kwargs={str(getattr(message, 'additional_kwargs', None))[:200]}")
    return ", ".join(parts)


async def acall_with_retries(
    llm,
    messages: list,
    retries: int = 3,
    timeout: float = 500,
    delay: float = 1.0,
    stream: bool = False,
) -> ChatResponse:
    """
    Call LLM with retries and timeout handling.

    Args:
        llm: The LLM client instance
        messages: List of messages to send
        retries: Number of retry attempts
        timeout: Timeout in seconds for each attempt
        delay: Base delay between retries (multiplied by attempt number)
        stream: If True, stream response chunks to console in real-time

    Returns:
        The LLM ChatResponse object
    """
    last_exception: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            if stream:
                response = await _stream_response(llm, messages, timeout)
            else:
                response = await asyncio.wait_for(
                    llm.achat(messages=messages),
                    timeout=timeout,
                )

            # Validate response
            if (
                response is not None
                and getattr(response, "message", None) is not None
                and getattr(response.message, "content", None)
            ):
                if not stream:
                    logger.debug(f"{response.message.content}")
                return response
            else:
                logger.warning(f"Attempt {attempt} returned empty content ({describe_empty_response(response)})")
                last_exception = ValueError("Empty response content")

        except TimeoutError:
            logger.warning(f"Attempt {attempt} timed out after {timeout} seconds")
            last_exception = TimeoutError("Timed out")

        except Exception as e:
            if is_opencode_go_llm(llm) and is_limit_error(e):
                raise OpenCodeGoLimitError() from e
            if is_fatal_llm_error(e):
                raise classify_llm_error(e, model_name(llm)) from e
            logger.warning(f"Attempt {attempt} failed with error: {e!r}")
            last_exception = e

        if attempt < retries:
            await asyncio.sleep(delay * attempt)

    raise classify_llm_error(last_exception or ValueError("Empty response content"), model_name(llm)) from last_exception


async def _stream_response(llm, messages: list, timeout: float) -> ChatResponse:
    """
    Stream LLM response chunks to console and return accumulated response.

    Args:
        llm: The LLM client instance
        messages: List of messages to send
        timeout: Timeout in seconds for the entire stream

    Returns:
        ChatResponse with accumulated content
    """
    content = ""
    last_chunk: ChatResponse | None = None

    async def stream_chunks():
        nonlocal content, last_chunk
        async for chunk in await llm.astream_chat(messages=messages):
            delta = chunk.delta or ""
            if delta:
                logger.debug(delta, extra={"stream": True})
            content += delta
            last_chunk = chunk
        logger.debug("", extra={"stream_end": True})

    await asyncio.wait_for(stream_chunks(), timeout=timeout)

    # Build response matching non-streaming format
    # Use last_chunk.message to preserve all blocks (ThinkingBlock, etc.)
    # that providers accumulate during streaming
    response = ChatResponse(
        message=(last_chunk.message if last_chunk else ChatMessage(role="assistant", content=content)),
        raw=last_chunk.raw if last_chunk else None,
        additional_kwargs=last_chunk.additional_kwargs if last_chunk else {},
    )

    return response


async def acomplete_with_retries(
    llm,
    prompt: str,
    retries: int = 3,
    timeout: float = 500,
    delay: float = 1.0,
    stream: bool = False,
) -> CompletionResponse:
    """
    Call LLM completion with retries and timeout handling.

    Args:
        llm: The LLM client instance
        prompt: The prompt string to send
        retries: Number of retry attempts
        timeout: Timeout in seconds for each attempt
        delay: Base delay between retries (multiplied by attempt number)
        stream: If True, stream response chunks to console in real-time

    Returns:
        The LLM CompletionResponse object
    """
    last_exception: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            if stream:
                response = await _stream_complete_response(llm, prompt, timeout)
            else:
                response = await asyncio.wait_for(
                    llm.acomplete(prompt),
                    timeout=timeout,
                )

            # Validate response
            if response is not None and getattr(response, "text", None):
                if not stream:
                    logger.debug(f"{response.text}")
                return response
            else:
                logger.warning(f"Attempt {attempt} returned empty content")
                last_exception = ValueError("Empty response content")

        except TimeoutError:
            logger.warning(f"Attempt {attempt} timed out after {timeout} seconds")
            last_exception = TimeoutError("Timed out")

        except Exception as e:
            if is_fatal_llm_error(e):
                raise classify_llm_error(e, model_name(llm)) from e
            logger.warning(f"Attempt {attempt} failed with error: {e!r}")
            last_exception = e

        if attempt < retries:
            await asyncio.sleep(delay * attempt)

    raise classify_llm_error(last_exception or ValueError("Empty response content"), model_name(llm)) from last_exception


async def _stream_complete_response(llm, prompt: str, timeout: float) -> CompletionResponse:
    """
    Stream LLM completion response chunks to console and return accumulated response.

    Args:
        llm: The LLM client instance
        prompt: The prompt string to send
        timeout: Timeout in seconds for the entire stream

    Returns:
        CompletionResponse with accumulated content
    """
    content = ""
    last_chunk: CompletionResponse | None = None

    async def stream_chunks():
        nonlocal content, last_chunk
        async for chunk in await llm.astream_complete(prompt):
            delta = chunk.delta or ""
            if delta:
                logger.debug(delta, extra={"stream": True})
            content += delta
            last_chunk = chunk
        logger.debug("", extra={"stream_end": True})

    await asyncio.wait_for(stream_chunks(), timeout=timeout)

    # Build response matching non-streaming format
    response = CompletionResponse(
        text=content,
        raw=last_chunk.raw if last_chunk else None,
        additional_kwargs=last_chunk.additional_kwargs if last_chunk else {},
    )

    return response


async def astructured_predict_with_retries(
    llm,
    output_cls: type[T],
    prompt: PromptTemplate,
    retries: int = 3,
    timeout: float = 500,
    delay: float = 1.0,
    **prompt_args,
) -> T:
    """
    Call LLM structured predict with retries and timeout handling.

    Args:
        llm: The LLM client instance
        output_cls: The Pydantic model class for structured output
        prompt: PromptTemplate with {variables}
        retries: Number of retry attempts
        timeout: Timeout in seconds for each attempt
        delay: Base delay between retries (multiplied by attempt number)
        **prompt_args: Values for template variables

    Returns:
        Instance of the output_cls Pydantic model
    """
    last_exception: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            result = await asyncio.wait_for(
                llm.astructured_predict(output_cls, prompt, **prompt_args),
                timeout=timeout,
            )

            # Validate response
            if result is not None:
                logger.debug(f"{result}")
                return result
            else:
                logger.warning(f"Attempt {attempt} returned None")
                last_exception = ValueError("Empty response")

        except TimeoutError:
            logger.warning(f"Attempt {attempt} timed out after {timeout} seconds")
            last_exception = TimeoutError("Timed out")

        except Exception as e:
            if is_fatal_llm_error(e):
                raise classify_llm_error(e, model_name(llm)) from e
            logger.warning(f"Attempt {attempt} failed with error: {e!r}")
            last_exception = e

        if attempt < retries:
            await asyncio.sleep(delay * attempt)

    raise classify_llm_error(last_exception or ValueError("Empty response content"), model_name(llm)) from last_exception
