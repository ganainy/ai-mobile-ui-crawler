"""Pre-run warnings: problems that do not stop a crawl but make it worse than the settings promise.

Shared by the GUI (shown in a dialog before the run starts) and the CLI (printed to stderr).
Each check is best-effort: if it cannot be carried out, it stays silent rather than guessing.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_A11Y_PARSER_MODES = ("accessibility", "boost")


@dataclass(frozen=True)
class PreRunWarning:
    """One problem found before the run.

    ``portal_fix`` says how ``core.portal_actions`` can fix a Portal problem: ``"enable"``
    (a few seconds over adb) or ``"install"`` (a download; minutes). None for other problems.
    """

    message: str
    portal_fix: str | None = None


def collect_pre_run_warnings(config_manager, device_id: str | None) -> list[PreRunWarning]:
    """Return one human-readable message per problem found, in the order they matter.

    The checks run in parallel (each waits on the network or adb for up to ~2 s).
    """
    checks = (_portal_warning, _phoenix_warning)
    with ThreadPoolExecutor(max_workers=len(checks)) as pool:
        futures = [(check, pool.submit(check, config_manager, device_id)) for check in checks]
    warnings = []
    for check, future in futures:
        try:
            message = future.result()
        except Exception as e:
            logger.debug("Pre-run check %s failed: %s", check.__name__, e)
            continue
        if message:
            warnings.append(message)
    return warnings


def _portal_warning(config_manager, device_id: str | None) -> PreRunWarning | None:
    """Portal must be installed with its accessibility service on for the a11y tree parser modes."""
    mode = str(config_manager.get("ui_parser_mode", "boost") or "boost").lower()
    if mode not in _A11Y_PARSER_MODES or not device_id:
        return None

    from async_adbutils import adb

    from mobile_crawler.domain.crawler_agent.portal import get_portal_status

    async def status():
        return await get_portal_status(await adb.device(serial=device_id))

    portal = asyncio.run(status())
    if portal.ready:
        return None
    if mode == "accessibility":
        effect = "the crawler will see no UI elements"
    else:
        effect = "every step will fall back to OmniParser (slower, and it costs money on Replicate)"
    return PreRunWarning(
        f"{portal.describe()}, so the phone cannot supply an accessibility tree and {effect} "
        f"(UI parser mode '{mode}').",
        portal_fix="enable" if portal.installed else "install",
    )


def _phoenix_warning(config_manager, device_id: str | None) -> PreRunWarning | None:
    """Phoenix tracing is enabled but no Phoenix answers: remote and down, port taken, or start failed."""
    from mobile_crawler.infrastructure.phoenix_docker import (
        PhoenixDockerService,
        is_local_phoenix_url,
        last_start_error,
        phoenix_tracing_url,
    )

    endpoint = phoenix_tracing_url(config_manager)
    if endpoint is None:
        return None
    no_trace = "so this run will have no trace"
    if not is_local_phoenix_url(endpoint):
        from mobile_crawler.domain.crawler_agent.agent.utils.tracing_setup import check_phoenix_reachable

        if check_phoenix_reachable(endpoint, timeout=1.0):
            return None
        return PreRunWarning(
            f"Phoenix tracing is enabled but no Phoenix server answers at {endpoint}, {no_trace}. "
            "It is not on this machine, so the crawler does not start it. "
            "Fix: start that Phoenix server or turn tracing off in Settings."
        )

    service = PhoenixDockerService(endpoint)
    if service.is_phoenix_reachable():
        return None
    if service.port_in_use():
        if service.is_running():
            return PreRunWarning(
                f"Phoenix tracing is enabled but the {service.container_name} container on port {service.port} "
                f"does not answer yet (still starting, or stuck), {no_trace}. "
                f"Fix: wait a moment, check `docker logs {service.container_name}`, or turn tracing off in Settings."
            )
        return PreRunWarning(
            f"Phoenix tracing is enabled but port {service.port} is in use by something that is not Phoenix, "
            f"{no_trace}. Fix: free the port, change the Phoenix URL, or turn tracing off in Settings."
        )
    reason = last_start_error(endpoint)
    fix = "fix the error above" if reason else "check that Docker Desktop is running"
    return PreRunWarning(
        f"Phoenix tracing is enabled but Phoenix could not be started in Docker at {endpoint}"
        f"{f' ({reason})' if reason else ''}, {no_trace}. "
        f"Fix: {fix}, or turn tracing off in Settings."
    )
