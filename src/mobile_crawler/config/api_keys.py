"""Where an API key comes from: the setting, then the saved secret, then the environment."""

import os


def resolve_api_key(config_manager, primary_key: str, env_keys: list[str] | tuple[str, ...] = ()) -> str | None:
    """Return the key saved as ``primary_key``, else the first of ``env_keys`` set in the environment."""
    key_value = config_manager.get(primary_key)
    if not key_value:
        try:
            key_value = config_manager.user_config_store.get_secret_plaintext(primary_key)
        except (KeyError, AttributeError):
            key_value = None
    if not key_value:
        for env_key in env_keys:
            key_value = os.environ.get(env_key)
            if key_value:
                break
    return key_value or None
