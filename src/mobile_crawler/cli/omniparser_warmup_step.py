"""Warm up the Replicate OmniParser backend before a CLI crawl (the GUI does this with its keep-alive checkbox)."""

from __future__ import annotations

import time
from typing import Any, Callable

KEEPALIVE_ENABLED_KEY = "omniparser_keepalive_enabled"  # same setting as the GUI's "Keep Replicate OmniParser warm" box


def warm_up_omniparser_if_needed(config_manager: Any, warm_up: Callable[..., Any] | None = None) -> str | None:
    """Send one mock screenshot to Replicate OmniParser so its first real parse is not a cold start.

    Runs before the crawl starts, so a cold start (observed: 139 s) does not eat the crawl's time limit.
    Returns a one-line message to show the user, or None when nothing was done. Never raises.
    """
    parser_mode = str(config_manager.get("ui_parser_mode", "boost") or "boost")
    if parser_mode not in ("boost", "omniparser"):
        return None
    if str(config_manager.get("omniparser_backend", "replicate") or "replicate") != "replicate":
        return None
    if not config_manager.get(KEEPALIVE_ENABLED_KEY, True):
        return None

    from mobile_crawler.config.api_keys import resolve_api_key

    api_key = resolve_api_key(config_manager, "replicate_api_key", ["REPLICATE_API_KEY", "REPLICATE_API_TOKEN"])
    if not api_key:
        return "OmniParser warm-up skipped: no Replicate API key"

    if warm_up is None:
        from mobile_crawler.domain.omniparser_warmup import warm_up_remote_omniparser as warm_up

    started = time.perf_counter()
    try:
        warm_up(api_key=api_key, box_threshold=float(config_manager.get("omniparser_box_threshold", 0.05) or 0.05))
    except Exception as exc:  # a failed warm-up must never stop the crawl
        return f"OmniParser warm-up failed ({exc}); the first parse may be slow"
    return f"OmniParser warm-up ok ({time.perf_counter() - started:.1f}s)"
