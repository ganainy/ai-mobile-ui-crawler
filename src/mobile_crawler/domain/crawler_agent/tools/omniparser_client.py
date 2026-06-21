"""OmniParser client for vision-based UI parsing in DroidRun."""

import base64
import logging
import os
import time
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_LOCAL_PARSE_TIMEOUT_SECONDS = 120

# Transient error substrings that justify a retry of the Replicate call.
# These come from httpx.RemoteProtocolError ("Server disconnected"),
# h11.ProtocolError ("Connection closed"), websockets, or Replicate SDK
# wrappers that re-raise with a bare "closed" message. None of these
# indicate a problem with the input image — only the transport.
_TRANSIENT_REPLICATE_ERROR_TOKENS = (
    "closed",
    "remote protocol error",
    "server disconnected",
    "connection reset",
    "connection aborted",
    "connectionerror",
    "read timeout",
    "timed out",
    "temporarily unavailable",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "503",
    "504",
    "502",
    "retry",
    "overloaded",
    "capacity",
)

DEFAULT_REPLICATE_MAX_RETRIES = 3
DEFAULT_REPLICATE_RETRY_INITIAL_DELAY = 1.0
DEFAULT_REPLICATE_RETRY_BACKOFF_FACTOR = 2.0
DEFAULT_REPLICATE_RETRY_MAX_DELAY = 15.0


def _is_transient_replicate_error(error: BaseException) -> bool:
    """Return True when an exception looks like a transient transport failure.

    The Replicate SDK hides httpx/h11 errors behind generic messages; the most
    common one we've seen in production is the bare string "closed" raised
    after ~30-40s when the upstream model server drops the streaming
    connection. We match case-insensitively against the exception message and
    the names of known network exception types.
    """
    message = (str(error) or "").lower()
    if any(token in message for token in _TRANSIENT_REPLICATE_ERROR_TOKENS):
        return True

    # Walk the cause chain — Replicate often wraps the real error.
    causes: list[BaseException] = []
    cause = error.__cause__ or error.__context__
    while cause and cause not in causes:
        causes.append(cause)
        cause = cause.__cause__ or cause.__context__

    type_names = " ".join(type(c).__name__.lower() for c in [error, *causes])
    if any(
        needle in type_names
        for needle in (
            "remoteprotocolerror",
            "protocolerror",
            "connectionerror",
            "connectionreset",
            "connectionaborted",
            "timeout",
            "readtimeout",
        )
    ):
        return True

    return False


class OmniParserBackend(Enum):
    REPLICATE = "replicate"
    LOCAL = "local"


class OmniParserClient:
    """Client for OmniParser vision-based UI parsing.

    Supports two backends:
    - Replicate API (default): Pay-per-call, no GPU needed
    - Local server: Faster, requires GPU setup

    Example element from parse result:
    {
        "type": "text",  # or "icon"
        "bbox": [0.05, 0.85, 0.95, 0.92],  # [x1, y1, x2, y2] in ratios
        "interactivity": True,
        "content": "In den Warenkorb"
    }
    """

    def __init__(
        self,
        backend: str = "replicate",
        api_key: str | None = None,
        local_url: str = "http://localhost:8000",
        local_parse_timeout_seconds: int | float = DEFAULT_LOCAL_PARSE_TIMEOUT_SECONDS,
        box_threshold: float = 0.05,
    ):
        """Initialize OmniParser client.

        Args:
            backend: "replicate" or "local"
            api_key: API key for Replicate (or set REPLICATE_API_KEY env var)
            local_url: URL for local OmniParser server
            local_parse_timeout_seconds: Local server parse request timeout
            box_threshold: Minimum confidence threshold for element detection
        """
        self.backend = OmniParserBackend(backend)
        # Check both env var names for backward compatibility:
        # REPLICATE_API_KEY (our canonical name) and
        # REPLICATE_API_TOKEN (Replicate SDK's native name)
        self._api_key = api_key or os.environ.get("REPLICATE_API_KEY") or os.environ.get("REPLICATE_API_TOKEN")
        self.local_url = local_url
        self.local_parse_timeout_seconds = max(1, float(local_parse_timeout_seconds))
        self.box_threshold = box_threshold
        logger.debug(f"OmniParser initialized: backend={backend}, has_api_key={bool(self._api_key)}")

    def parse(self, image_bytes: bytes) -> list[dict[str, Any]]:
        """Parse screenshot using OmniParser.

        Args:
            image_bytes: Screenshot image data

        Returns:
            List of UI elements with bounding boxes and descriptions
        """
        if self.backend == OmniParserBackend.LOCAL:
            return self._parse_local(image_bytes)
        else:
            return self._parse_replicate(image_bytes)

    def _parse_replicate(self, image_bytes: bytes) -> list[dict[str, Any]]:
        """Parse using Replicate API.

        Args:
            image_bytes: Screenshot image data

        Returns:
            List of UI elements
        """
        import os
        import tempfile

        try:
            import replicate
        except ImportError as e:
            logger.error("replicate package not installed: pip install replicate")
            raise ImportError("replicate package required: pip install replicate") from e

        if not self._api_key:
            raise ValueError(
                "Replicate API key not configured. Set REPLICATE_API_KEY " "(or REPLICATE_API_TOKEN) env var."
            )

        # Debug: check image format
        logger.debug(f"Image bytes: {len(image_bytes)} bytes, header: {image_bytes[:20]}")

        # Set BOTH env var names so any Replicate SDK consumer finds the token
        os.environ["REPLICATE_API_TOKEN"] = self._api_key
        os.environ["REPLICATE_API_KEY"] = self._api_key

        try:
            # Validate image with Pillow first
            try:
                import io

                from PIL import Image

                img = Image.open(io.BytesIO(image_bytes))
                logger.debug(f"PIL detected format: {img.format}, mode: {img.mode}, size: {img.size}")
                # Convert to RGB JPEG
                if img.mode != "RGB":
                    img = img.convert("RGB")
                output = io.BytesIO()
                img.save(output, format="JPEG", quality=95)
                image_bytes = output.getvalue()
                logger.debug(f"Converted to JPEG: {len(image_bytes)} bytes")
            except Exception as img_err:
                logger.warning(f"Image validation/conversion failed: {img_err}")

            # Write to a proper temp file with correct extension
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name

            logger.debug(f"Temp file: {tmp_path}, size: {os.path.getsize(tmp_path)}")

            try:
                # Use new Replicate client API with file path
                client = replicate.Client()

                # Open the temp file once and reuse the handle across retries.
                # Seeking back to 0 between attempts lets the SDK re-upload the
                # same bytes without re-opening (and leaking) file descriptors.
                with open(tmp_path, "rb") as image_handle:
                    output = self._run_replicate_with_retry(client, image_handle)

                logger.debug(f"client.run() succeeded, output type: {type(output)}")

                # Parse output - depends on model output format
                logger.debug(f"Replicate output type: {type(output)}")
                logger.debug(f"Replicate output: {str(output)[:500]}")

                if output is None:
                    logger.warning("Replicate returned None")
                    return []

                # Handle the dict response format from OmniParser
                if isinstance(output, dict):
                    # OmniParser v2 returns {"elements": "...", "img": "..."}
                    try:
                        elements_raw = output.get("elements")
                    except Exception as e:
                        logger.error(f"Error getting elements from output: {e}")
                        return []

                    logger.debug(
                        f"elements_raw type: {type(elements_raw)}, value: {str(elements_raw)[:200] if elements_raw else 'empty'}"
                    )

                    valid_elements = []

                    if elements_raw is None:
                        logger.warning("OmniParser returned None for elements")
                        return []

                    if not elements_raw:
                        logger.warning("OmniParser returned empty elements string")
                        return []

                    if isinstance(elements_raw, str) and elements_raw:
                        import ast
                        import re

                        # Split on record boundaries: "icon N: {" starts each record.
                        # Using a lookahead so the delimiter is not consumed.
                        record_pattern = re.compile(r"(?=icon \d+: \{)")
                        records = record_pattern.split(elements_raw)

                        if not any(record.strip() for record in records):
                            logger.warning(f"No icon matches found in: {elements_raw[:300]}")
                            return []

                        for record in records:
                            record = record.strip()
                            if not record:
                                continue
                            # Extract the dict portion after "icon N: "
                            brace_start = record.find("{")
                            if brace_start == -1:
                                continue
                            dict_str = record[brace_start:]
                            # Ensure the string is complete (ends with '}')
                            # Drop truncated last records from Replicate response
                            if not dict_str.rstrip().endswith("}"):
                                logger.debug(
                                    "Dropping truncated OmniParser element: %s",
                                    dict_str[:80],
                                )
                                continue
                            try:
                                el = ast.literal_eval(dict_str)
                                if isinstance(el, dict) and "bbox" in el:
                                    valid_elements.append(el)
                            except (ValueError, SyntaxError) as e:
                                logger.debug("Failed to parse element: %s", e)
                                continue

                    logger.debug(f"Valid elements parsed: {len(valid_elements)}")
                    if valid_elements:
                        logger.debug(f"First valid element: {valid_elements[0]}")

                    return valid_elements if valid_elements else []
                elif isinstance(output, list):
                    return output
                elif isinstance(output, str):
                    # JSON string - try to parse it
                    try:
                        import json

                        parsed = json.loads(output)
                        if isinstance(parsed, dict):
                            return parsed.get("elements", parsed.get("parsed_content", []))
                        elif isinstance(parsed, list):
                            return parsed
                    except Exception:
                        pass
                    return []
                else:
                    logger.warning(f"Unexpected Replicate output type: {type(output)}")
                    return []
            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Replicate API error: {e}")
            raise RuntimeError(f"OmniParser Replicate error: {e}") from e

    def _run_replicate_with_retry(self, client: Any, image_handle: Any) -> Any:
        """Call ``client.run`` with retry/backoff for transient transport errors.

        Replicate streams OmniParser predictions over a long-lived HTTP
        connection. When the upstream model server drops the stream (e.g. the
        bare ``closed`` error from ``httpx.RemoteProtocolError`` /
        ``h11.ProtocolError``), the request can be safely retried because the
        OmniParser model is stateless with respect to individual screenshots.

        Non-transient errors (auth failures, 4xx, malformed input) propagate
        immediately so the caller can surface them.

        Args:
            client: A ``replicate.Client`` instance (or test double).
            image_handle: An already-open binary file handle for the screenshot
                JPEG. The handle is rewound to position 0 before each attempt
                so retries can re-read the same bytes. The caller owns the
                handle's lifecycle (i.e. is responsible for closing it).
        """
        model = "microsoft/omniparser-v2:" "49cf3d41b8d3aca1360514e83be4c97131ce8f0d99abfc365526d8384caa88df"

        max_retries = DEFAULT_REPLICATE_MAX_RETRIES
        delay = DEFAULT_REPLICATE_RETRY_INITIAL_DELAY
        max_delay = DEFAULT_REPLICATE_RETRY_MAX_DELAY
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(
                    "Calling Replicate client.run() (attempt %s/%s)",
                    attempt,
                    max_retries,
                )
                # Rewind so retries upload the full image again, not a
                # truncated tail from wherever the previous attempt left the
                # read cursor.
                try:
                    image_handle.seek(0)
                except Exception:
                    pass

                return client.run(
                    model,
                    input={
                        "image": image_handle,
                        "box_threshold": self.box_threshold,
                    },
                )
            except Exception as run_err:
                last_error = run_err
                if not _is_transient_replicate_error(run_err):
                    logger.error("client.run() failed (non-transient): %s", run_err)
                    raise

                if attempt >= max_retries:
                    logger.error(
                        "client.run() failed after %s attempts: %s",
                        attempt,
                        run_err,
                    )
                    raise

                sleep_for = min(delay, max_delay)
                logger.warning(
                    "Replicate transient error on attempt %s/%s: %s. " "Retrying in %.1fs.",
                    attempt,
                    max_retries,
                    run_err,
                    sleep_for,
                )
                time.sleep(sleep_for)
                delay *= DEFAULT_REPLICATE_RETRY_BACKOFF_FACTOR

        # Defensive: should be unreachable because the loop either returns or
        # re-raises, but keeps the type checker happy.
        assert last_error is not None
        raise last_error

    def _parse_local(self, image_bytes: bytes) -> list[dict[str, Any]]:
        """Parse using local OmniParser server.

        Args:
            image_bytes: Screenshot image data

        Returns:
            List of UI elements
        """
        import requests

        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        try:
            payload = {
                "base64_image": b64_image,
                "box_threshold": self.box_threshold,
            }

            # Try /parse/ first (Microsoft format), fallback to /parse only
            # when the endpoint is missing. Do not retry timed-out parses.
            parse_url = f"{self.local_url}/parse/"
            response = requests.post(
                parse_url,
                json=payload,
                timeout=self.local_parse_timeout_seconds,
            )
            if response.status_code == 404:
                parse_url = f"{self.local_url}/parse"
                response = requests.post(
                    parse_url,
                    json=payload,
                    timeout=self.local_parse_timeout_seconds,
                )

            if response.status_code != 200:
                raise RuntimeError(f"Local OmniParser error: {response.status_code}")

            result = response.json()
            return result.get("parsed_content_list", result.get("elements", []))

        except requests.exceptions.Timeout:
            logger.error(
                "Local OmniParser parse timed out after %.0fs. "
                "Increase omniparser_local_parse_timeout_seconds or use GPU acceleration.",
                self.local_parse_timeout_seconds,
            )
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Local OmniParser connection error: {e}")
            raise

    def is_available(self) -> bool:
        """Check if OmniParser is available (local server or API key configured).

        Returns:
            True if backend is ready to use
        """
        if self.backend == OmniParserBackend.REPLICATE:
            has_key = bool(self._api_key)
            logger.debug(f"OmniParser Replicate check: has_api_key={has_key}")
            return has_key
        else:
            return self._check_local_server()

    def _check_local_server(self) -> bool:
        """Check if local server is available."""
        import requests

        try:
            response = requests.get(f"{self.local_url}/probe/", timeout=2)
            if response.status_code == 200:
                return True
            response = requests.get(f"{self.local_url}/health", timeout=2)
            return response.status_code == 200
        except Exception:
            return False


def create_omni_parser_client(
    backend: str = "replicate",
    api_key: str | None = None,
    local_url: str = "http://localhost:8000",
    local_parse_timeout_seconds: int | float = DEFAULT_LOCAL_PARSE_TIMEOUT_SECONDS,
    box_threshold: float = 0.05,
) -> OmniParserClient | None:
    """Factory function to create OmniParser client with error handling.

    Args:
        backend: "replicate" or "local"
        api_key: API key for Replicate
        local_url: URL for local server
        local_parse_timeout_seconds: Local server parse request timeout
        box_threshold: Detection threshold

    Returns:
        OmniParserClient instance or None if not available
    """
    try:
        client = OmniParserClient(
            backend=backend,
            api_key=api_key,
            local_url=local_url,
            local_parse_timeout_seconds=local_parse_timeout_seconds,
            box_threshold=box_threshold,
        )
        if client.is_available():
            logger.info(f"OmniParser client initialized (backend: {backend})")
            return client
        else:
            logger.warning(f"OmniParser backend '{backend}' not available")
            return None
    except Exception as e:
        logger.warning(f"Failed to initialize OmniParser client: {e}")
        return None
