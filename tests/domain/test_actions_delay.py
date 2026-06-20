"""Tests for type_text and type_secret focus delay behavior."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mobile_crawler.domain.crawler_agent.agent.utils.actions import type_text, type_secret


def _make_ctx(index: int = 0, secret_value: str | None = None):
    """Build a minimal ActionContext mock for action tests."""
    ctx = MagicMock()
    ctx.driver = AsyncMock()
    ctx.driver.tap = AsyncMock()
    ctx.driver.input_text = AsyncMock(return_value=True)
    ctx.ui = MagicMock()
    ctx.ui.get_element_coords = MagicMock(return_value=(100, 200))

    if secret_value is not None:
        ctx.credential_manager = AsyncMock()
        ctx.credential_manager.resolve_key = AsyncMock(return_value=secret_value)
        ctx.credential_manager.get_keys = AsyncMock(return_value=["MY_PASS"])
    else:
        ctx.credential_manager = None

    return ctx


@pytest.mark.asyncio
async def test_type_text_with_index_includes_delay():
    """type_text(index!= -1) must sleep 0.5s between tap and input_text."""
    ctx = _make_ctx()

    with patch("mobile_crawler.domain.crawler_agent.agent.utils.actions.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await type_text("hello", index=0, ctx=ctx)

    assert result.success
    ctx.driver.tap.assert_called_once_with(100, 200)
    ctx.driver.input_text.assert_called_once_with("hello", False)
    # Verify sleep(0.5) was called
    mock_sleep.assert_called_once_with(0.5)


@pytest.mark.asyncio
async def test_type_text_with_negative_index_skips_tap_and_delay():
    """type_text(index=-1) must not tap or sleep."""
    ctx = _make_ctx()

    with patch("mobile_crawler.domain.crawler_agent.agent.utils.actions.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await type_text("hello", index=-1, ctx=ctx)

    assert result.success
    ctx.driver.tap.assert_not_called()
    mock_sleep.assert_not_called()
    ctx.driver.input_text.assert_called_once_with("hello", False)


@pytest.mark.asyncio
async def test_type_secret_with_index_includes_delay():
    """type_secret(index!=-1) must sleep 0.5s between tap and input_text."""
    ctx = _make_ctx(secret_value="s3cret!")

    with patch("mobile_crawler.domain.crawler_agent.agent.utils.actions.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await type_secret("MY_PASS", index=5, ctx=ctx)

    assert result.success
    ctx.driver.tap.assert_called_once_with(100, 200)
    ctx.driver.input_text.assert_called_once_with("s3cret!")
    mock_sleep.assert_called_once_with(0.5)


@pytest.mark.asyncio
async def test_type_secret_no_credential_manager_returns_error():
    """type_secret without credential_manager should return failure."""
    ctx = _make_ctx()
    ctx.credential_manager = None

    result = await type_secret("MY_PASS", index=0, ctx=ctx)
    assert not result.success
    assert "Credential manager" in result.summary
