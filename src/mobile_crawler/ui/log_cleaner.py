"""Log message cleaning: strips ANSI codes, deduplicates, suppresses noise."""

import ast
import re
import time
from collections import deque

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

_OMNIPARSER_HINTS = (
    "omniparser",
    "replicate output type",
    "valid elements parsed",
    "first valid element",
    "using omniparser only",
    "icon ",
)

_OMNIPARSER_DICT_LINE_RE = re.compile(r"^(icon\s+\d+:\s*|First valid element:\s*)(\{.*\})$")

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

    def clean(self, logger_name: str, message: str) -> str | None:
        """Clean and deduplicate a raw log message."""
        cleaned = _ANSI_RE.sub("", message)

        stripped = cleaned.strip()
        for prefix in _STDOUT_MIRROR_PREFIXES:
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix):].lstrip()
                break
        cleaned = stripped
        cleaned = self._normalize_omniparser_message(logger_name, cleaned)

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
        dedup_key = re.sub(r"\s+", " ", dedup_key).strip()

        now = time.monotonic()
        for ts, text in self._recent:
            if now - ts > self.DEDUP_WINDOW_SECONDS:
                continue
            if text == dedup_key:
                return None

        self._recent.append((now, dedup_key))
        return cleaned

    def _normalize_omniparser_message(self, logger_name: str, message: str) -> str:
        lower_logger = (logger_name or "").lower()
        lower_message = message.lower()
        is_omniparser_related = "omni" in lower_logger or any(hint in lower_message for hint in _OMNIPARSER_HINTS)
        if not is_omniparser_related:
            return message

        normalized = (
            message.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace("\\'", "'")
            .replace('\\"', '"')
        )

        formatted_lines: list[str] = []
        for line in normalized.splitlines() or [normalized]:
            match = _OMNIPARSER_DICT_LINE_RE.match(line.strip())
            if not match:
                formatted_lines.append(line)
                continue

            prefix, payload = match.groups()
            pretty_payload = self._format_omniparser_payload(payload)
            if pretty_payload is None:
                formatted_lines.append(line)
                continue

            formatted_lines.append(prefix.strip())
            formatted_lines.extend(f"  {payload_line}" for payload_line in pretty_payload.splitlines())

        return "\n".join(formatted_lines)

    def _format_omniparser_payload(self, payload: str) -> str | None:
        try:
            parsed = ast.literal_eval(payload)
        except (SyntaxError, ValueError):
            return None

        if not isinstance(parsed, dict):
            return None

        lines: list[str] = []
        if "type" in parsed:
            lines.append(f"type: {parsed['type']}")
        if "interactivity" in parsed:
            lines.append(f"interactivity: {parsed['interactivity']}")
        if "content" in parsed:
            lines.append(f"content: {parsed['content']}")
        if "bbox" in parsed:
            lines.append(f"bbox: {parsed['bbox']}")

        for key, value in parsed.items():
            if key in {"type", "interactivity", "content", "bbox"}:
                continue
            lines.append(f"{key}: {value}")

        return "\n".join(lines)
