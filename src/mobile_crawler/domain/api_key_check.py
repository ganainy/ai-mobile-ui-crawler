"""Check whether an AI provider API key is accepted by the provider."""

import requests

from mobile_crawler.domain.opencode_go import OPENCODE_GO_BASE_URL, OPENCODE_GO_DEFAULT_MODEL, request_headers

_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_OPENROUTER_URL = "https://openrouter.ai/api/v1/auth/key"  # /models is public, this one validates the key
_TIMEOUT_SECONDS = 10


def check_api_key(provider: str, api_key: str) -> tuple[bool, str]:
    """Return (ok, message) for a "gemini", "openrouter" or "opencode_go" key."""
    api_key = api_key.strip()
    if not api_key:
        return False, "Enter a key first"
    try:
        if provider == "gemini":
            response = requests.get(
                _GEMINI_URL, params={"pageSize": 1}, headers={"x-goog-api-key": api_key}, timeout=_TIMEOUT_SECONDS
            )
        elif provider == "openrouter":
            response = requests.get(
                _OPENROUTER_URL, headers={"Authorization": f"Bearer {api_key}"}, timeout=_TIMEOUT_SECONDS
            )
        elif provider == "opencode_go":
            # /models is public and there is no key endpoint, so send a one-token chat call.
            response = requests.post(
                f"{OPENCODE_GO_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", **request_headers()},
                json={
                    "model": OPENCODE_GO_DEFAULT_MODEL,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 16,
                },
                timeout=_TIMEOUT_SECONDS,
            )
            if response.status_code == 429:
                return True, "Key works, but the usage limit is reached"
            if response.status_code == 400:
                # Auth passed (a bad key is 401/403); the tiny test call itself was refused.
                return True, "Key accepted (test call returned HTTP 400)"
        else:
            raise ValueError(f"Unknown provider: {provider}")
    except requests.RequestException as exc:
        return False, f"Couldn't reach the provider: {exc.__class__.__name__}"

    if response.ok:
        return True, "Key works"
    if response.status_code in (400, 401, 403):
        return False, "Key rejected"
    return False, f"Provider error (HTTP {response.status_code})"
