"""Config snapshot captured at run start, so runs can be compared across crawler changes."""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from mobile_crawler.domain.guided_scenarios_generator import guided_scenarios_config_key

logger = logging.getLogger(__name__)

SNAPSHOT_RELATIVE_PATH = Path("data") / "config_snapshot.json"

# Explicit allowlist: keys are copied one by one so API keys and other secrets can never leak in.
_PLAIN_KEYS = (
    "ai_provider",
    "ai_model",
    "limit_type",
    "ui_parser_mode",
    "omniparser_backend",
    "enable_tracing",
    "tracing_provider",
    "enable_traffic_capture",
    "enable_video_recording",
    "restart_app_before_run",
)


def current_git_commit() -> str | None:
    """Short commit hash of the crawler checkout, or None if git is unavailable."""
    try:
        repo_root = Path(__file__).resolve().parents[3]
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        commit = result.stdout.strip()
        return commit if result.returncode == 0 and commit else None
    except Exception:
        return None


def build_config_snapshot(config_manager: Any, app_package: str, git_commit: str | None) -> dict[str, Any]:
    """Collect the settings that shape a run into a JSON-safe dict."""
    snapshot: dict[str, Any] = {key: config_manager.get(key, None) for key in _PLAIN_KEYS}
    snapshot["max_steps"] = config_manager.get("max_steps", config_manager.get("max_crawl_steps", None))
    snapshot["max_duration_seconds"] = config_manager.get(
        "max_duration_seconds", config_manager.get("max_crawl_duration_seconds", None)
    )
    snapshot["status_bar_exclusion_px"] = config_manager.get("top_bar_height", None)
    snapshot["bottom_bar_exclusion_px"] = config_manager.get("bottom_bar_height", None)
    snapshot["guided_scenarios"] = config_manager.get(guided_scenarios_config_key(app_package), [])
    snapshot["git_commit"] = git_commit
    return snapshot


def write_config_snapshot(session_path: str, snapshot: dict[str, Any]) -> Path:
    """Write the snapshot to <session>/data/config_snapshot.json and return its path."""
    path = Path(session_path) / SNAPSHOT_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def read_config_snapshot(session_path: str | None) -> dict[str, Any] | None:
    """Read a run's snapshot, or None when absent (older runs) or unreadable."""
    if not session_path:
        return None
    path = Path(session_path) / SNAPSHOT_RELATIVE_PATH
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
