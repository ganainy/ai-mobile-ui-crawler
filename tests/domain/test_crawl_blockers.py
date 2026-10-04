import io

import pytest
from PIL import Image

from mobile_crawler.domain.crawl_blockers import (
    KIND_SCREENSHOT_BLOCKED,
    CrawlBlockedError,
    find_crawl_blocked_error,
    is_blank_screenshot,
    screenshot_blocked_error,
)
from mobile_crawler.domain.crawler_agent.tools.ui.provider import AndroidStateProvider


def _jpeg(color):
    out = io.BytesIO()
    Image.new("RGB", (64, 128), color).save(out, format="JPEG", quality=95)
    return out.getvalue()


def test_black_image_is_blank_and_others_are_not():
    assert is_blank_screenshot(_jpeg((0, 0, 0)))
    assert not is_blank_screenshot(_jpeg((30, 30, 30)))
    assert not is_blank_screenshot(b"not an image")
    assert not is_blank_screenshot(None)


def test_black_screen_with_a_small_overlay_handle_is_still_blank():
    img = Image.new("RGB", (1080, 2180), (0, 0, 0))
    img.paste((70, 70, 70), (1070, 260, 1080, 570))  # edge-panel handle
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=95)
    assert is_blank_screenshot(out.getvalue())


def test_find_crawl_blocked_error_walks_the_cause_chain():
    inner = screenshot_blocked_error("app.vera.prod")
    try:
        raise RuntimeError("wrapped") from inner
    except RuntimeError as outer:
        assert find_crawl_blocked_error(outer) is inner
    assert find_crawl_blocked_error(ValueError("x")) is None
    assert inner.kind == KIND_SCREENSHOT_BLOCKED


class _Driver:
    def __init__(self, frames):
        self.frames = list(frames)

    async def screenshot(self):
        return self.frames.pop(0) if len(self.frames) > 1 else self.frames[0]


def _provider(frames):
    provider = AndroidStateProvider.__new__(AndroidStateProvider)
    provider.driver = _Driver(frames)
    provider.target_package = "app.vera.prod"
    provider._captures_done = 0
    provider._blank_streak = 0
    return provider


@pytest.mark.asyncio
async def test_black_first_capture_raises(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", lambda *_: _noop())
    black = _jpeg((0, 0, 0))
    provider = _provider([black])
    with pytest.raises(CrawlBlockedError) as excinfo:
        await provider._check_blank_screenshot(black)
    assert excinfo.value.kind == KIND_SCREENSHOT_BLOCKED


@pytest.mark.asyncio
async def test_black_first_capture_that_recovers_is_fine(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", lambda *_: _noop())
    provider = _provider([_jpeg((90, 90, 90))])
    assert await provider._check_blank_screenshot(_jpeg((0, 0, 0))) is False


@pytest.mark.asyncio
async def test_black_frame_mid_run_skips_until_third_in_a_row():
    provider = _provider([_jpeg((90, 90, 90))])
    black = _jpeg((0, 0, 0))
    assert await provider._check_blank_screenshot(_jpeg((90, 90, 90))) is False
    assert await provider._check_blank_screenshot(black) is True
    assert await provider._check_blank_screenshot(black) is True
    with pytest.raises(CrawlBlockedError):
        await provider._check_blank_screenshot(black)


async def _noop():
    return None
