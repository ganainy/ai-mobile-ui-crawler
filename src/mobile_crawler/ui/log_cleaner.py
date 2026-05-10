"""Log message cleaning: strips ANSI codes, deduplicates, suppresses noise."""

import re
import time
from collections import deque
from typing import Optional

# ANSI escape sequence pattern (colors, cursor movements, etc.)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mGKHFABCDsuJh]")

# Prefixes that indicate a duplicate stdout/stderr mirror of an already-logged line.
_STDOUT_MIRROR_PREFIXES = (
    "[stdout]",
    "[stderr]",
)

# Logger name prefixes whose messages are duplicates of already-propagated records.
_DUPLICATE_LOGGER_PREFIXES = (
    "droidrun.",
    "droidrun:",
)

# Exact or prefix-matched substrings that identify pure library noise.
_NOISE_PATTERNS: list[re.Pattern] = [
    re.compile(r"PIL\.(PngImagePlugin|JpegImagePlugin|Image): STREAM"),
    re.compile(r"PIL\.(PngImagePlugin|JpegImagePlugin|Image): b'(IHDR|sRGB|sBIT|IDAT|PLTE)'"),
    re.compile(r"PIL\.Image: (Importing|failed to import)"),
    re.compile(r"Temp file: [A-Za-z]:\\.*\.jpg, size:"),
    re.compile(r"Converted to JPEG:"),
    re.compile(r"PIL detected format:"),
    re.compile(r"Image bytes: \d+ bytes, header:"),
    re.compile(r"Replicate output: \{"),
    re.compile(r"elements_raw type:"),
    re.compile(r"IndexedFormatter\.format:"),
    re.compile(r"_convert_omni_to_indexed:"),
    re.compile(r"Converting omni_tree"),
    re.compile(r"(Attempting to import|Attempting to get class|Successfully imported|Found class):"),
    re.compile(r"Initializing (OpenRouter|GoogleGenAI|Anthropic) with kwargs"),
    re.compile(r'HTTP Request: (POST|GET) https://.*"HTTP/1\.1 (200 OK|201 Created)"'),
    re.compile(r"openai\._base_client: (Sending HTTP|HTTP Response|request_id)"),
    re.compile(r"Request options: \{"),
    re.compile(r"idempotency_key"),
    re.compile(r"asyncio: Using proactor:"),
    re.compile(r"Could not get usage: Unsupported provider"),
]


class LogCleaner:
    """Stateful log message cleaner."""

    DEDUP_WINDOW_SECONDS = 2.0
    DEDUP_CACHE_SIZE = 200

    def __init__(self):
        self._recent: deque[tuple[float, str]] = deque(maxlen=self.DEDUP_CACHE_SIZE)

    def clean(self, logger_name: str, message: str) -> Optional[str]:
        """Clean and deduplicate a raw log message."""
        cleaned = _ANSI_RE.sub("", message)

        stripped = cleaned.strip()
        for prefix in _STDOUT_MIRROR_PREFIXES:
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix):].lstrip()
                break
        cleaned = stripped

        if not cleaned.strip():
            return None

        for pattern in _NOISE_PATTERNS:
            if pattern.search(cleaned):
                return None

        dedup_key = cleaned
        for prefix in _DUPLICATE_LOGGER_PREFIXES:
            if dedup_key.startswith(prefix):
                dedup_key = dedup_key[len(prefix):].lstrip()
                break
        if logger_name:
            logger_prefix = f"{logger_name}:"
            if dedup_key.startswith(logger_prefix):
                dedup_key = dedup_key[len(logger_prefix):].lstrip()

        now = time.monotonic()
        for ts, text in self._recent:
            if now - ts > self.DEDUP_WINDOW_SECONDS:
                continue
            if text == dedup_key:
                return None

        self._recent.append((now, dedup_key))
        return cleaned
