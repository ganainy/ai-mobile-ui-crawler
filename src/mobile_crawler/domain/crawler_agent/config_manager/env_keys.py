"""Persistent API key storage using a .env file in the user config directory."""

from __future__ import annotations

import os
from pathlib import Path

import platformdirs
from dotenv import dotenv_values, set_key

ENV_FILE = Path(platformdirs.user_config_dir("droidrun")) / ".env"

API_KEY_ENV_VARS = {
    "google": "GOOGLE_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def load_env_keys() -> dict[str, str]:
    """Load API keys. The .env file takes precedence over shell env vars.

    Returns:
        Dict mapping slot name (e.g. "google") to key value.
    """
    result: dict[str, str] = {}
    for slot, env_var in API_KEY_ENV_VARS.items():
        result[slot] = os.environ.get(env_var, "")
    if ENV_FILE.exists():
        for slot, env_var in API_KEY_ENV_VARS.items():
            val = dotenv_values(ENV_FILE).get(env_var)
            if val:
                result[slot] = val
    return result


def save_env_keys(keys: dict[str, str]) -> None:
    """Persist API keys to the .env file and set them as env vars.

    Args:
        keys: Dict mapping slot name (e.g. "google") to key value.
    """
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ENV_FILE.exists():
        ENV_FILE.touch()
    for slot, env_var in API_KEY_ENV_VARS.items():
        val = keys.get(slot, "")
        if val:
            set_key(str(ENV_FILE), env_var, val)
            os.environ[env_var] = val
