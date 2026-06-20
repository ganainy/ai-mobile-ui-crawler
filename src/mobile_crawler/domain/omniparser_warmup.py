"""Warm-up helper for the OmniParser backend."""

import io
from typing import Any


def create_mock_screenshot() -> bytes:
    """Create a small phone-like screenshot payload for OmniParser warm-up."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (360, 640), color=(246, 247, 249))
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, 360, 56), fill=(34, 43, 69))
    draw.text((20, 20), "Mobile Crawler Warmup", fill=(255, 255, 255))
    draw.rectangle((24, 96, 336, 156), fill=(255, 255, 255), outline=(210, 215, 224))
    draw.text((44, 118), "Search apps", fill=(72, 79, 96))
    draw.rectangle((24, 190, 156, 242), fill=(37, 99, 235))
    draw.text((58, 210), "Start", fill=(255, 255, 255))
    draw.rectangle((180, 190, 336, 242), fill=(255, 255, 255), outline=(37, 99, 235))
    draw.text((222, 210), "Settings", fill=(37, 99, 235))

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=90)
    return output.getvalue()


def warm_up_remote_omniparser(
    *,
    api_key: str,
    box_threshold: float = 0.05,
) -> list[dict[str, Any]]:
    """Send one mock screenshot to Replicate OmniParser to wake the backend."""
    from mobile_crawler.domain.crawler_agent.tools.omniparser_client import (
        OmniParserClient,
    )

    client = OmniParserClient(
        backend="replicate",
        api_key=api_key,
        box_threshold=box_threshold,
    )
    return client.parse(create_mock_screenshot())
